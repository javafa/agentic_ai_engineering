from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
load_dotenv()

# 1) 상태 정의
class TopState(TypedDict):
    messages: Annotated[list, add_messages]
    research_result: str    # 리서치 팀의 산출물
    dev_result: str         # 개발 팀의 산출물
    round_count: int        # 무한 루프 방지

class TeamState(TypedDict):
    messages: Annotated[list, add_messages]
    team_result: str        # 팀 내부에서 최상위로 올릴 결과

# 개발 팀 전용 상태: 수정 루프(coder ⇄ reviewer)를 돌리기 위한 채널 추가
class DevTeamState(TeamState):
    code: str               # 최신 코드(coder 산출물)
    feedback: str           # 리뷰어 피드백(총평 또는 수정 요청)
    approved: bool          # 리뷰 통과 여부
    pending_review: bool    # 이번 코드가 아직 리뷰 안 됨
    revision_count: int     # 수정 반복 횟수

# 라우팅 스키마 정의
class OrchestratorDecision(BaseModel):
    reasoning: str
    next_team: Literal["research_team", "dev_team", "FINISH"]

class ResearchRouteDecision(BaseModel):
    reasoning: str
    next_worker: Literal["searcher", "analyzer"]

# 리뷰 판단을 위한 스키마
class ReviewResultDecision(BaseModel):
    approved: bool = Field(description="코드가 충분히 좋아 더 수정이 필요 없으면 True")
    feedback: str = Field(description="수정이 필요하면 구체적 지적, 승인이면 간단한 총평")

# 2) 유틸리티 정의
# 2-1) 로그 헬퍼 — 형식: {들여쓰기}[노드명(12)] EVENT(8) 메시지
def log(name: str, event: str, message: str = "", depth: int = 0):
    if message:
        message = message.replace("\n", " ").strip()
        if len(message) > 120:
            message = message[:117] + "..."
    indent = "  " * depth
    print(f"{indent}[{name:<12}] {event:<8} {message}")

# 2-2) prefill 가드 — state에 저장하지 않으며, 마지막이 human/tool 턴이면 그대로 반환
def ensure_user_last(messages: list) -> list:
    if messages and getattr(messages[-1], "type", None) == "ai":
        return [*messages, {"role": "user",
                            "content": "위 진행 상황을 바탕으로 당신의 역할에 맞게 다음 단계를 수행하세요."}]
    return messages

# 3) Tool 정의
@tool
def web_search(query: str) -> str:
    """웹에서 정보를 검색합니다."""
    results = {
        "AI 에이전트 트렌드": "2026년에는 Agentic RAG와 멀티 에이전트 시스템이 주류입니다.",
        "Python 3.14 변경점": "JIT 컴파일러 개선, 새로운 타입 힌트 문법 등이 포함.",
    }
    for key, val in results.items():
        if any(word in query for word in key.split()):
            return val
    return f"'{query}'에 대한 검색 결과입니다: 관련 정보를 찾았습니다."

@tool
def write_code(description: str, language: str = "python") -> str:
    """요구사항에 따라 코드를 작성합니다."""
    return f"{language}\n# {description}에 대한 코드\nprint('Hello from generated code')\n"

# 4) 모델과 상수 - 빠른 응답 확인을 위해 더 작은 모델로 변경
llm = ChatAnthropic(model="claude-haiku-4-5")
MAX_ROUNDS = 8
MAX_REVISIONS = 2   # 개발 팀 수정 루프 횟수 상한

# 5) 리서치 팀 구현 — 본질적으로 선형(검색 → 분석)
def build_research_team():
    def research_supervisor(state: TeamState) -> Command:
        """리서치 팀 슈퍼바이저: 다음 워커 결정"""
        decision_llm = llm.with_structured_output(ResearchRouteDecision)
        try:
            decision = decision_llm.invoke([
                {"role": "system", "content": """당신은 리서치 팀의 슈퍼바이저입니다.
가용 워커:
- searcher: 웹 검색으로 정보 수집. 메시지에 검색 결과(tool 응답)가 없을 때 선택.
- analyzer: 수집된 정보를 분석. 메시지에 검색 결과가 이미 있을 때만 선택.

원칙: 검색 결과가 없으면 무조건 searcher를 선택하세요."""},
                *ensure_user_last(state["messages"])
            ])
            log("supervisor", "ROUTE", f"→ {decision.next_worker} | {decision.reasoning}", depth=1)
            return Command(goto=decision.next_worker)
        except Exception:
            # 팀 진입 시점에는 항상 searcher 부터 시작
            log("supervisor", "FALLBACK", "→ searcher (구조화 출력 예외)", depth=1)
            return Command(goto="searcher")

    def searcher(state: TeamState) -> Command:
        """검색 워커: web_search Tool 활용"""
        search_llm = llm.bind_tools([web_search])
        response = search_llm.invoke([
            {"role": "system", "content":
             "당신은 검색 전문가입니다. web_search 도구를 활용해 정보를 찾으세요."},
            *ensure_user_last(state["messages"])
        ])
        if response.tool_calls:
            new_messages = [response]
            for tc in response.tool_calls:
                log("searcher", "TOOL", f'{tc["name"]}({tc["args"]})', depth=1)
                result = web_search.invoke(tc["args"])
                new_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result)
                })
            log("searcher", "ROUTE", "→ analyzer (검색 완료)", depth=1)
            return Command(goto="analyzer", update={"messages": new_messages})
        log("searcher", "ROUTE", "→ analyzer (도구 호출 없음)", depth=1)
        return Command(goto="analyzer", update={"messages": [response]})

    def analyzer(state: TeamState) -> Command:
        """분석 워커: 검색 결과를 종합하고 팀 결과 확정"""
        response = llm.invoke([
            {"role": "system", "content":
             "당신은 분석가입니다. 검색 결과를 종합해 핵심 인사이트를 도출하세요."},
            *ensure_user_last(state["messages"])
        ])
        log("analyzer", "RESULT", response.content, depth=1)
        return Command(
            goto=END,
            update={
                "messages": [response],
                "team_result": response.content
            }
        )

    team_work_flow = StateGraph(TeamState)
    team_work_flow.add_node("research_supervisor", research_supervisor)
    team_work_flow.add_node("searcher", searcher)
    team_work_flow.add_node("analyzer", analyzer)
    team_work_flow.add_edge(START, "research_supervisor")
    return team_work_flow.compile()

# 6) 개발 팀 구현 — 반복(coder ⇄ reviewer 수정 루프)
def build_dev_team():
    def _merge_dev_result(state: DevTeamState) -> str:
        """코드와 리뷰를 명시적으로 합쳐 상위(team_result)로 올린다."""
        code = state.get("code", "")
        feedback = state.get("feedback", "")
        parts = []
        if code:
            parts.append(f"## 작성된 코드\n{code}")
        if feedback:
            parts.append(f"## 코드 리뷰\n{feedback}")
        return "\n\n".join(parts) if parts else "(개발 산출물 없음)"

    def dev_supervisor(state: DevTeamState) -> Command:
        """개발 팀 슈퍼바이저: 수정 루프의 흐름을 제어하는 결정적 컨트롤러.
        판단(승인/수정)은 reviewer가 하고, 여기서는 상태에 따라 다음 노드만 정한다."""
        has_code = bool(state.get("code"))
        pending = state.get("pending_review", False)
        approved = state.get("approved", False)
        revisions = state.get("revision_count", 0)

        # 종료 조건
        if approved:
            log("supervisor", "DONE", "리뷰 통과 — 종료", depth=1)
            return Command(goto=END, update={"team_result": _merge_dev_result(state)})
        if revisions >= MAX_REVISIONS:
            log("supervisor", "LIMIT", f"최대 수정({MAX_REVISIONS}) 도달 — 종료", depth=1)
            return Command(goto=END, update={"team_result": _merge_dev_result(state)})

        # 루프 라우팅
        if not has_code:
            log("supervisor", "ROUTE", "→ coder (최초 구현)", depth=1)
            return Command(goto="coder")
        if pending:
            log("supervisor", "ROUTE", "→ reviewer (리뷰 대기)", depth=1)
            return Command(goto="reviewer")
        # 코드는 있으나 리뷰에서 수정 요청됨
        log("supervisor", "ROUTE", f"→ coder (수정 {revisions + 1}회차)", depth=1)
        return Command(goto="coder")

    def coder(state: DevTeamState) -> Command:
        """코드 작성 워커: write_code 툴 활용, 피드백이 있으면 반영해 재작성"""
        feedback = state.get("feedback", "")
        sys = "당신은 코드 작성 전문가입니다. write_code 도구로 요구사항에 맞는 파이썬 코드를 작성하세요."
        if feedback:
            sys += f"\n\n[직전 리뷰 피드백 — 반드시 반영]: {feedback}"

        code_llm = llm.bind_tools([write_code])
        response = code_llm.invoke([
            {"role": "system", "content": sys},
            *ensure_user_last(state["messages"])
        ])

        new_messages = [response]
        code_text = response.content if isinstance(response.content, str) else ""
        if response.tool_calls:
            produced = []
            for tc in response.tool_calls:
                log("coder", "TOOL", f'{tc["name"]}({tc["args"]})', depth=1)
                result = write_code.invoke(tc["args"])
                produced.append(str(result))
                new_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result)
                })
            code_text = "\n\n".join(produced)

        log("coder", "CODE", code_text, depth=1)
        log("coder", "ROUTE", "→ dev_supervisor", depth=1)
        return Command(goto="dev_supervisor", update={
            "messages": new_messages,
            "code": code_text,
            "pending_review": True,   # 새 코드가 리뷰를 기다림
        })

    def reviewer(state: DevTeamState) -> Command:
        """코드 리뷰 워커: 승인/수정 여부를 구조화 출력으로 판단"""
        review_llm = llm.with_structured_output(ReviewResultDecision)
        try:
            decision: ReviewResultDecision = review_llm.invoke([
                {"role": "system", "content":
                 "당신은 코드 리뷰어입니다. 코드를 검토해 승인 여부를 판단하세요. "
                 "수정이 필요하면 approved=False와 함께 구체적 개선 지적을, "
                 "충분하면 approved=True와 간단한 총평을 작성하세요."},
                *ensure_user_last(state["messages"])
            ])
            approved, feedback = decision.approved, decision.feedback
        except Exception:
            # 파싱 실패 시 보수적으로 승인 처리(무한 루프 방지)
            approved, feedback = True, "리뷰 파싱 실패 — 자동 승인 처리"

        revisions = state.get("revision_count", 0)
        log("reviewer", "REVIEW", f"승인={approved} | {feedback}", depth=1)
        log("reviewer", "ROUTE", "→ dev_supervisor", depth=1)
        return Command(goto="dev_supervisor", update={
            "approved": approved,
            "feedback": feedback,
            "pending_review": False,
            "revision_count": revisions + (0 if approved else 1),
        })

    team_work_flow = StateGraph(DevTeamState)
    team_work_flow.add_node("dev_supervisor", dev_supervisor)
    team_work_flow.add_node("coder", coder)
    team_work_flow.add_node("reviewer", reviewer)
    team_work_flow.add_edge(START, "dev_supervisor")
    return team_work_flow.compile()

# 7) 오케스트레이터
def orchestrator(state: TopState) -> Command:
    """최상위 오케스트레이터: 어느 팀에 작업을 맡길지 결정"""
    count = state.get("round_count", 0) + 1
    log("orchestrator", "START", f"round {count}/{MAX_ROUNDS} "
        f"(리서치={'O' if state.get('research_result') else 'X'}, "
        f"개발={'O' if state.get('dev_result') else 'X'})")

    # 핑퐁 루프 방지
    if count >= MAX_ROUNDS:
        log("orchestrator", "LIMIT", "최대 라운드 도달 — 작업 종료")
        return Command(goto=END, update={
            "messages": [{"role": "assistant",
                          "content": "최대 라운드에 도달, 작업을 종료합니다."}],
            "round_count": count
        })

    decision_llm = llm.with_structured_output(OrchestratorDecision)
    try:
        decision = decision_llm.invoke([
            {"role": "system", "content": f"""당신은 멀티팀 프로젝트의 오케스트레이터입니다.
가용 팀:
- research_team: 정보 검색과 분석 담당
- dev_team: 코드 작성과 리뷰 담당
- FINISH: 모든 작업이 완료되었을 때

현재 진행 상태:
- 리서치 결과: {state.get('research_result') or '없음'}
- 개발 결과: {state.get('dev_result') or '없음'}

다음 규칙대로 결정하세요:
1. 사용자 요청에 정보 조사가 필요하고 '리서치 결과'가 '없음'이면 → research_team
2. 사용자 요청에 코드 작성이 필요하고 '개발 결과'가 '없음'이면 → dev_team
3. 필요한 작업이 모두 끝났으면 → FINISH

이미 결과가 채워진 단계는 다시 호출하지 마세요."""},
            *ensure_user_last(state["messages"])
        ])
        next_team = decision.next_team
        log("orchestrator", "DECIDE", f"{next_team} | {decision.reasoning}")
    except Exception:
        # 구조화 출력 파싱 실패 시 진행 상태 기반 폴백
        if not state.get("research_result"):
            next_team = "research_team"
        elif not state.get("dev_result"):
            next_team = "dev_team"
        else:
            next_team = "FINISH"
        log("orchestrator", "FALLBACK", f"구조화 출력 실패 → {next_team}")

    if next_team == "FINISH":
        log("orchestrator", "FINISH", "모든 작업 완료")
        return Command(goto=END, update={"round_count": count})
    log("orchestrator", "ROUTE", f"→ {next_team}")
    return Command(
        goto=next_team,
        update={"round_count": count}
    )

# 8) 팀 노드: 서브그래프를 최상위에서 호출하는 래퍼
research_team = build_research_team()
def research_team_node(state: TopState):
    log("research_team", "ENTER", "리서치 팀 시작")
    result = research_team.invoke({
        "messages": state["messages"],
        "team_result": ""
    })
    log("research_team", "RESULT", result.get("team_result", ""))
    return {
        "messages": result["messages"],
        "research_result": result.get("team_result", "")
    }

dev_team = build_dev_team()
def dev_team_node(state: TopState):
    log("dev_team", "ENTER", "개발 팀 시작")
    result = dev_team.invoke({
        "messages": state["messages"],
        "team_result": "",
        "code": "",
        "feedback": "",
        "approved": False,
        "pending_review": False,
        "revision_count": 0,
    })
    log("dev_team", "RESULT", result.get("team_result", ""))
    return {
        "messages": result["messages"],
        "dev_result": result.get("team_result", "")
    }

# 9) 최상위 그래프 조립
work_flow = StateGraph(TopState)
work_flow.add_node("orchestrator", orchestrator)
work_flow.add_node("research_team", research_team_node)
work_flow.add_node("dev_team", dev_team_node)
work_flow.add_edge(START, "orchestrator")
work_flow.add_edge("research_team", "orchestrator")
work_flow.add_edge("dev_team", "orchestrator")
graph = work_flow.compile()

# 10) 실행
if __name__ == "__main__":
    print("=== 실행 로그 ===")
    result = graph.invoke({
        "messages": [("user",
            "AI 에이전트의 최신 동향을 조사하고, "
            "간단한 슈퍼바이저 패턴 예제 코드를 작성해줘")],
        "research_result": "",
        "dev_result": "",
        "round_count": 0
    })

    # 11) 흐름 추적(요약)
    # print("\n=== 최종 결과 ===")
    # print(f"[리서치 결과] {result.get('research_result', '')[:200]}")
    # print(f"[개발 결과] {result.get('dev_result', '')[:200]}")
    # print(f"[총 라운드] {result.get('round_count', 0)}")