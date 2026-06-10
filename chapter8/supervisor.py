from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv() # .env 환경변수 로드

# 1) 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str       # 다음에 실행할 에이전트 (관찰·디버깅용)
    round_count: int      # 무한 루프 방지용

# 2) Tool 정의
@tool
def web_search(query: str) -> str:
    """웹에서 정보를 검색합니다."""
    # 더미 데이터: 쿼리에 따라 서로 다른 결과를 반환
    results = {
        "시장": "2025년 글로벌 AI 에이전트 시장 규모는 약 50억 달러이며, 연평균 약 45% 성장 중입니다.",
        "RAG": "Agentic RAG는 검색→추론→재검색을 반복해 답변 정확도를 높이는 기법입니다.",
        "멀티": "멀티 에이전트 시스템은 슈퍼바이저가 전문 에이전트에게 작업을 분배하는 구조입니다.",
        "트렌드": "2026년 AI 에이전트 트렌드는 Agentic RAG와 멀티 에이전트 오케스트레이션입니다.",
    }
    for key, val in results.items():
        if key in query:
            return val
    return f"'{query}'에 대한 검색 결과: 관련 정보를 찾았습니다."

@tool
def project_growth(current: float, growth_rate: float, years: int) -> str:
    """현재 수치와 연간 성장률로 향후 예상치를 계산합니다. 성장률은 0~1 또는 % 단위 모두 허용합니다."""
    rate = growth_rate / 100 if growth_rate > 1 else growth_rate
    future = current * (1 + rate) ** years
    return f"현재 {current:g} → {years}년 후 약 {future:,.1f} (연 {rate:.0%} 성장 가정)"

# 3) 모델 및 상수 초기화
llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
MAX_ROUNDS = 8        # 슈퍼바이저 ↔ 워커 왕복 횟수 제한
MAX_TOOL_LOOPS = 5    # 워커 1회 실행 내부의 도구 루프 제한

# 4) 로깅 유틸리티 (실시간 추적용)
def log(role: str, text: str) -> None:
    """실행 도중 발생하는 이벤트를 즉시 출력합니다."""
    print(f"[{role}] {text}")

def extract_text(content) -> str:
    """content가 문자열이든 블록 리스트든 텍스트 부분만 추출합니다."""
    if isinstance(content, str):
        return content
    return " ".join(
        b.get("text", "") for b in content
        if isinstance(b, dict) and b.get("type") == "text"
    ).strip()


# 5) 라우팅 결정용 스키마 (구조화 출력)
class Route(BaseModel):
    """다음에 실행할 팀원을 선택합니다."""
    next_agent: Literal["researcher", "analyst", "FINISH"] = Field(
        description="다음에 실행할 팀원. 모든 작업이 끝났으면 FINISH."
    )

SUPERVISOR_PROMPT = """당신은 팀을 관리하는 슈퍼바이저입니다.
주어진 작업을 분석하여 적절한 팀원에게 위임하세요.
- researcher: 정보 검색, 조사, 사실 수집 담당
- analyst: 수집된 정보를 바탕으로 분석 및 향후 예측 담당
아직 끝나지 않은 작업이 있으면 해당 팀원을, 모든 작업이 끝났으면 FINISH를 선택하세요."""

# 6) 슈퍼바이저 노드
def supervisor(state: State) -> Command:
    """작업을 분석하고 적절한 에이전트에게 위임합니다."""
    count = state.get("round_count", 0) + 1

    # 핑퐁 루프 방지
    if count >= MAX_ROUNDS:
        log("supervisor", "최대 라운드에 도달하여 종료합니다.")
        return Command(goto=END, update={
            "messages": [{"role": "assistant", "content": "최대 라운드에 도달하여 종료합니다."}],
            "round_count": count,
        })

    router_llm = llm.with_structured_output(Route)
    decision = router_llm.invoke([
        {"role": "system", "content": SUPERVISOR_PROMPT},
        *state["messages"],
        # 대화가 항상 user 턴으로 끝나도록 라우팅 질문을 덧붙임 (prefill 에러 방지)
        {"role": "user", "content": "지금까지의 진행 상황을 보고 다음에 실행할 팀원을 선택하세요."},
    ])

    next_agent = decision.next_agent  # 항상 researcher / analyst / FINISH 중 하나

    if next_agent == "FINISH":
        log("supervisor", "모든 작업 완료 → FINISH")
        return Command(goto=END, update={"next_agent": "finish", "round_count": count})

    log("supervisor", f"→ '{next_agent}' 에게 위임")
    return Command(goto=next_agent, update={"next_agent": next_agent, "round_count": count})

# 7) 전문가 노드 정의
RESEARCHER_PROMPT = """당신은 리서치 전문가입니다. 웹 검색 도구로 사실과 수치를 찾아 '조사 결과'만 정리하세요.
분석이나 예측은 당신의 역할이 아니므로 하지 마세요.
검색은 한두 번이면 충분하며, 같은 주제를 반복 검색하지 마세요.
정보를 모았으면 바로 정리해서 답하세요."""

def researcher(state: State) -> Command:
    """검색 전문가 에이전트"""
    # 병렬 도구 호출을 꺼서 한 번에 하나씩만 검색하게 함
    research_llm = llm.bind_tools([web_search], parallel_tool_calls=False)
    messages = [
        {"role": "system", "content": RESEARCHER_PROMPT},
        *state["messages"],
        {"role": "user", "content": "위 작업에서 조사가 필요한 부분을 수행하세요."},
    ]
    new_messages = []

    # 내부 도구 루프: 최대 MAX_TOOL_LOOPS 회까지만 반복
    for _ in range(MAX_TOOL_LOOPS):
        response = research_llm.invoke(messages)
        new_messages.append(response)
        messages.append(response)

        text = extract_text(response.content)
        if text:
            log("researcher", text[:1000])

        if not response.tool_calls:   # 도구 호출이 없으면 최종 답변 → 종료
            break

        for tc in response.tool_calls:
            log("researcher", f"→ 도구 호출: {tc['name']}({tc['args']})")
            result = web_search.invoke(tc["args"])
            log("tool", str(result)[:1000])
            tool_msg = {"role": "tool", "tool_call_id": tc["id"], "content": str(result)}
            messages.append(tool_msg)
            new_messages.append(tool_msg)
    else:
        # 루프 상한 도달: 도구 없이 마지막 정리만 시켜 강제 종료
        messages.append({"role": "user", "content": "도구를 더 사용하지 말고 지금까지 내용을 정리해 최종 답변만 작성하세요."})
        final = llm.invoke(messages)
        new_messages.append(final)
        log("researcher", extract_text(final.content)[:1000])

    return Command(goto="supervisor", update={"messages": new_messages})

ANALYST_PROMPT = """당신은 분석·예측 전문가입니다. 앞선 조사 결과의 수치를 바탕으로
project_growth 도구로 향후 추세를 계산하고, 그 결과를 해석해 분석과 예측을 작성하세요.
추가 정보 검색은 하지 마세요."""

def analyst(state: State) -> Command:
    """분석·예측 전문가 에이전트"""
    analyst_llm = llm.bind_tools([project_growth], parallel_tool_calls=False)
    messages = [
        {"role": "system", "content": ANALYST_PROMPT},
        *state["messages"],
        {"role": "user", "content": "위 작업에서 분석·예측이 필요한 부분을 수행하세요."},
    ]
    new_messages = []

    for _ in range(MAX_TOOL_LOOPS):
        response = analyst_llm.invoke(messages)
        new_messages.append(response)
        messages.append(response)

        text = extract_text(response.content)
        if text:
            log("analyst", text[:200])

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            log("analyst", f"→ 도구 호출: {tc['name']}({tc['args']})")
            result = project_growth.invoke(tc["args"])
            log("tool", str(result)[:1000])
            tool_msg = {"role": "tool", "tool_call_id": tc["id"], "content": str(result)}
            messages.append(tool_msg)
            new_messages.append(tool_msg)
    else:
        messages.append({"role": "user", "content": "도구를 더 사용하지 말고 지금까지 내용을 정리해 최종 답변만 작성하세요."})
        final = llm.invoke(messages)
        new_messages.append(final)
        log("analyst", extract_text(final.content)[:1000])

    return Command(goto="supervisor", update={"messages": new_messages})

# 8) 그래프 연결
work_flow = StateGraph(State)
work_flow.add_node("supervisor", supervisor)
work_flow.add_node("researcher", researcher)
work_flow.add_node("analyst", analyst)
work_flow.add_edge(START, "supervisor")

graph = work_flow.compile()

# 9) 실행 (이벤트는 노드 내부에서 실시간으로 출력됨)
task = "AI 에이전트 시장의 현재 동향을 조사하고, 향후 3년 성장세를 분석·예측해줘"

print("=== 실행 추적 ===")
log("human", task)

result = graph.invoke({
    "messages": [("user", task)],
    "next_agent": "",
    "round_count": 0,
})

print("=== 완료 ===")
