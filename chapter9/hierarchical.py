from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

# 1) 상태 정의
class TopState(TypedDict):
    messages: Annotated[list, add_messages]
    research_result: str    # 리서치 팀의 결과
    dev_result: str         # 개발 팀의 결과
    round_count: int        # 무한 루프 방지

class TeamState(TypedDict):
    messages: Annotated[list, add_messages]
    team_result: str        # 팀 내부에서 최상위로 올릴 결과

# 2) 라우팅 스키마 정의
class OrchestratorDecision(BaseModel):
    reasoning: str
    next_team: Literal["research_team", "dev_team", "FINISH"]

class ResearchRouteDecision(BaseModel):
    reasoning: str
    next_worker: Literal["searcher", "analyzer"]

class DevRouteDecision(BaseModel):
    reasoning: str
    next_worker: Literal["coder", "reviewer"]

# 3) Tool 정의 - 9.3 섹션의 코드 재사용
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

# 4) 모델과 상수
llm = ChatOpenAI(model="gpt-5.4-mini")
MAX_ROUNDS = 8

# 5) 리서치 팀 구현
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
                *state["messages"]
            ])
            return Command(goto=decision.next_worker)
        except Exception:
            # 팀 진입 시점에는 항상 searcher 부터 시작
            return Command(goto="searcher")

    def searcher(state: TeamState) -> Command:
        """검색 워커: web_search Tool 활용"""
        search_llm = llm.bind_tools([web_search])
        response = search_llm.invoke([
            {"role": "system", "content":
             "당신은 검색 전문가입니다. web_search 도구를 활용해 정보를 찾으세요."},
            *state["messages"]
        ])
        if response.tool_calls:
            new_messages = [response]
            for tc in response.tool_calls:
                result = web_search.invoke(tc["args"])
                new_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(result)
                })
            return Command(goto="analyzer", update={"messages": new_messages})
        return Command(goto="analyzer", update={"messages": [response]})

    def analyzer(state: TeamState) -> Command:
        """분석 워커: 검색 결과를 종합하고 팀 결과 확정"""
        response = llm.invoke([
            {"role": "system", "content":
             "당신은 분석가입니다. 검색 결과를 종합해 핵심 인사이트를 도출하세요."},
            *state["messages"]
        ])
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

# 6) 개발 팀 구현
def build_dev_team():
    def dev_supervisor(state: TeamState) -> Command:
        """개발 팀 슈퍼바이저"""
        decision_llm = llm.with_structured_output(DevRouteDecision)
        try:
            decision = decision_llm.invoke([
                {"role": "system", "content": """당신은 개발 팀의 슈퍼바이저입니다.
                가용 워커:
                - coder: 요구사항을 코드로 구현. 메시지에 ```python 코드 블록이 없을 때 선택.
                - reviewer: 작성된 코드를 검토. 메시지에 ```python 코드 블록이 있을 때만 선택.

                원칙: 코드 블록이 없으면 무조건 coder를 선택하세요. 리서치 팀의 분석 텍스트는 코드가 아닙니다."""},
                *state["messages"]
            ])
            return Command(goto=decision.next_worker)
        except Exception:
            # 팀 진입 시점에는 항상 coder 부터 시작
            return Command(goto="coder")

    def coder(state: TeamState) -> Command:
        response = llm.invoke([
            {"role": "system", "content":
             "당신은 코드 작성 전문가입니다. 요구사항에 맞는 파이썬 코드를 작성하세요."},
            *state["messages"]
        ])
        return Command(
            goto="reviewer",
            update={"messages": [response]}
        )

    def reviewer(state: TeamState) -> Command:
        response = llm.invoke([
            {"role": "system", "content":
             "당신은 코드 리뷰어입니다. 코드의 문제점과 개선안을 간결히 제시하세요."},
            *state["messages"]
        ])
        return Command(
            goto=END,
            update={
                "messages": [response],
                "team_result": response.content
            }
        )

    team_work_flow = StateGraph(TeamState)
    team_work_flow.add_node("dev_supervisor", dev_supervisor)
    team_work_flow.add_node("coder", coder)
    team_work_flow.add_node("reviewer", reviewer)
    team_work_flow.add_edge(START, "dev_supervisor")
    return team_work_flow.compile()

# 7) 오케스트레이터
def orchestrator(state: TopState) -> Command:
    """최상위 오케스트레이터: 어느 팀에 작업을 맡길지 결정"""
    count = state.get("round_count", 0) + 1
    # 핑퐁 루프 방지
    if count >= MAX_ROUNDS:
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
            *state["messages"]
        ])
        next_team = decision.next_team
    except Exception:
        # 구조화 출력 파싱 실패 시 진행 상태 기반 폴백
        if not state.get("research_result"):
            next_team = "research_team"
        elif not state.get("dev_result"):
            next_team = "dev_team"
        else:
            next_team = "FINISH"

    if next_team == "FINISH":
        return Command(goto=END, update={"round_count": count})
    return Command(
        goto=next_team,
        update={"round_count": count}
    )

# 8) 팀 노드: 서브그래프를 최상위에서 호출하는 래퍼
research_team = build_research_team()
def research_team_node(state: TopState):
    result = research_team.invoke({
        "messages": state["messages"],
        "team_result": ""
    })
    return {
        "messages": result["messages"],
        "research_result": result.get("team_result", "")
    }

dev_team = build_dev_team()
def dev_team_node(state: TopState):
    result = dev_team.invoke({
        "messages": state["messages"],
        "team_result": ""
    })
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
result = graph.invoke({
    "messages": [("user",
        "AI 에이전트의 최신 동향을 조사하고, "
        "간단한 슈퍼바이저 패턴 예제 코드를 작성해줘")],
    "research_result": "",
    "dev_result": "",
    "round_count": 0
})

# 10) 흐름 추적
print("=== 최종 결과 ===")
print(f"[리서치 결과] {result.get('research_result', '')[:200]}")
print(f"[개발 결과] {result.get('dev_result', '')[:200]}")
print(f"[총 라운드] {result.get('round_count', 0)}")
