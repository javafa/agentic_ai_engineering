from typing import Annotated, Literal
from typing_extensions import TypedDict
from operator import add
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

load_dotenv()

MAX_HANDOFFS = 5

# 0) 로그 헬퍼 — 형식: [에이전트명(12)] EVENT(7) 메시지
def log(agent_name: str, event: str, message: str = ""):
    if message:
        message = message.replace("\n", " ").strip()
        if len(message) > 120:
            message = message[:117] + "..."
    print(f"[{agent_name:<12}] {event:<7} {message}")

# 1) 라우팅 스키마
class Route(BaseModel):
    """에이전트의 응답 + 라우팅 결정"""
    answer: str = Field(description="사용자 또는 다음 에이전트에게 전달할 내용")
    next_agent: Literal["tech_support", "billing", "done"] = Field(
        description="다음으로 보낼 에이전트. 작업이 끝났으면 'done'."
    )

# 2) 공유 상태
class State(TypedDict):
    messages: Annotated[list, add_messages]
    handoff_count: int
    handoff_note: str
    trace: Annotated[list, add] # 에이전트 이름, 답변을 누적
    resolved: Annotated[list, add]   # ["tech_support", "billing"] 누적

# 3) LLM
llm = ChatAnthropic(model="claude-sonnet-5")
router_llm = llm.with_structured_output(Route)

# 4) 공통 실행 헬퍼 — 모든 에이전트가 이걸 통해 동작
def run_agent(state, system_prompt, allowed_routes, agent_name):
    count = state.get("handoff_count", 0)
    note = state.get("handoff_note", "")
    
    log(agent_name, "START", f"handoff {count}/{MAX_HANDOFFS}"
        + (f" | 인계메모: {note}" if note else ""))

    # 무한 루프 탈출
    if count >= MAX_HANDOFFS:
        return Command(goto=END, update={
            "messages": [{"role": "assistant", "content": "상담을 종료합니다."}],
            "trace": [(agent_name, "상담을 종료합니다.")],
        })

    # 에이전트 누적 처리    
    resolved = state.get("resolved", [])
    sys = system_prompt + f"\n\n[이미 처리된 에이전트]: {resolved or '없음'}\n"
    sys += "이미 처리된 도메인의 이슈는 다시 다루지 마세요. 처리할 게 없으면 next_agent='done'."

    # 다음 에이전트 선택
    sys += (f"\n\n[이전 에이전트 인계 메모]: {note}" if note else "")
		# Prefill 에러 방지
    msgs = state["messages"]
    if msgs and getattr(msgs[-1], "type", None) == "ai":
        msgs = [*msgs, {"role": "user", "content": "위 내용을 바탕으로 답변과 다음 에이전트를 결정하세요."}]
    decision = router_llm.invoke([{"role": "system", "content": sys}, *msgs])

    
    log(agent_name, "ANSWER", decision.answer)

    # 에이전트 로깅
    entry = (agent_name, decision.answer)
    # 종료 구분
    is_terminal = decision.next_agent == "done" or decision.next_agent not in allowed_routes
    if is_terminal:
        return Command(goto=END, update={
            "messages": [{"role": "assistant", "content": decision.answer}],
            "trace": [entry],
        })
    # 다음 에이전트로 이동
    log(agent_name, "ROUTE", f"→ {decision.next_agent} (handoff {count + 1}/{MAX_HANDOFFS})")
    return Command(
        goto=decision.next_agent,
        update={
            "messages": [{"role": "assistant", "content": decision.answer}],
            "handoff_count": count + 1,
            "handoff_note": decision.answer,
            "trace": [entry],
            "resolved": [agent_name],   # 에이전트 이름 추가
        }
    )


def general_support(state: State) -> Command[Literal["tech_support", "billing", "__end__"]]:
    return run_agent(state,
        system_prompt="""당신은 일반 고객 상담원입니다.
- 기술 문제(앱 크래시, 버그, 설치 등) → next_agent='tech_support'
- 결제/환불 문제 → next_agent='billing'
- 직접 답변 가능 → answer 작성 후 next_agent='done'
answer에는 사용자 또는 다음 에이전트에게 전달할 내용을 적으세요.""",
        allowed_routes=("tech_support", "billing"),
        agent_name="general",
    )

def tech_support(state: State) -> Command[Literal["billing", "__end__"]]:
    return run_agent(state,
        system_prompt="""당신은 기술 지원 전문가입니다.
처리 순서:
1. 사용자의 기술 문제에 대해 먼저 구체적인 답변/해결책을 answer에 작성하세요.
2. 메시지에 결제/환불 이슈가 함께 있으면 next_agent='billing'.
3. 그 외에는 next_agent='done'.
기술 답변 없이 라우팅만 하지 마세요.""",
        allowed_routes=("billing",),
        agent_name="tech_support",
    )

def billing(state: State) -> Command[Literal["tech_support", "__end__"]]:
    return run_agent(state,
        system_prompt="""당신은 결제 담당자입니다. 환불/청구/구독 문제를 처리합니다.
처리 순서:
1. 결제/환불 문제에 대해 먼저 구체적인 답변을 answer에 작성하세요.
2. 메시지에 미해결 기술 이슈가 있으면 next_agent='tech_support'.
3. 그 외에는 next_agent='done'.
결제 답변 없이 라우팅만 하지 마세요.""",
        allowed_routes=("tech_support",),
        agent_name="billing",
    )

# 6) 그래프
builder = StateGraph(State)
builder.add_node("general", general_support)
builder.add_node("tech_support", tech_support)
builder.add_node("billing", billing)
builder.add_edge(START, "general")
graph = builder.compile()

# 7) 실행
if __name__ == "__main__":
    print("=== 실행 로그 ===")
    result = graph.invoke({
        "messages": [("user", "앱이 자꾸 크래시가 나는데, 환불도 받고 싶어요")],
        "handoff_count": 0,
        "handoff_note": "",
        "trace": [],
    })
