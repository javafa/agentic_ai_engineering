from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
 
load_dotenv()

llm = ChatOpenAI(model="gpt-5.4-mini")


# ============================================================
# 라우팅 결정용 구조화 출력 스키마
# ============================================================

class ResearchEntryDecision(BaseModel):
    """리서치팀 진입 에이전트의 라우팅 결정"""
    reasoning: str = Field(description="해당 워커를 선택한 이유")
    next_worker: Literal["searcher", "analyzer"] = Field(
        description="다음에 작업을 수행할 워커. "
                    "새 정보 수집이 필요하면 searcher, "
                    "이미 데이터가 있어 분석만 필요하면 analyzer"
    )


class WorkerHandoffDecision(BaseModel):
    """워커가 작업 후 다음 행동을 결정"""
    output: str = Field(description="이번 단계의 작업 결과")
    next_action: Literal["handoff_searcher", "handoff_analyzer", "done"] = Field(
        description="다음 행동. 다른 워커에게 넘기려면 handoff_*, "
                    "팀 작업을 마치려면 done"
    )


class TopSupervisorDecision(BaseModel):
    """최상위 감독자의 팀 배분 결정"""
    reasoning: str = Field(description="해당 팀을 선택한 이유")
    next_team: Literal["research_team", "dev_team", "finish"] = Field(
        description="다음에 작업할 팀. 모든 작업이 완료되면 finish"
    )


# ============================================================
# 팀 그래프
# ============================================================

class TeamState(TypedDict):
    messages: Annotated[list, add_messages]
    team_result: str


def build_research_team():
    """리서치팀: 진입 에이전트가 라우팅, 워커끼리 자유 핸드오프"""

    entry_llm = llm.with_structured_output(ResearchEntryDecision)
    worker_llm = llm.with_structured_output(WorkerHandoffDecision)

    def entry_agent(
        state: TeamState
    ) -> Command[Literal["searcher", "analyzer"]]:
        decision = entry_llm.invoke([
            {"role": "system", "content":
                "당신은 리서치팀 진입 에이전트입니다. "
                "사용자 요청을 분석해 적절한 워커에게 작업을 분배하세요."},
            *state["messages"]
        ])
        return Command(
            goto=decision.next_worker,
            update={"messages": [
                {"role": "assistant",
                 "content": f"[라우팅] {decision.reasoning}"}
            ]}
        )

    def searcher(
        state: TeamState
    ) -> Command[Literal["analyzer", "__end__"]]:
        decision = worker_llm.invoke([
            {"role": "system", "content":
                "당신은 검색 전문가입니다. 필요한 정보를 검색해 제공하세요. "
                "분석이 더 필요하면 handoff_analyzer, "
                "검색 결과만으로 충분하면 done을 선택하세요."},
            *state["messages"]
        ])

        if decision.next_action == "handoff_analyzer":
            return Command(
                goto="analyzer",
                update={"messages": [
                    {"role": "assistant", "content": decision.output}
                ]}
            )
        return Command(
            goto=END,
            update={
                "messages": [
                    {"role": "assistant", "content": decision.output}
                ],
                "team_result": decision.output
            }
        )

    def analyzer(
        state: TeamState
    ) -> Command[Literal["searcher", "__end__"]]:
        decision = worker_llm.invoke([
            {"role": "system", "content":
                "당신은 분석 전문가입니다. 주어진 정보를 분석하세요. "
                "추가 검색이 필요하면 handoff_searcher, "
                "분석이 완료되었으면 done을 선택하세요."},
            *state["messages"]
        ])

        if decision.next_action == "handoff_searcher":
            return Command(
                goto="searcher",
                update={"messages": [
                    {"role": "assistant", "content": decision.output}
                ]}
            )
        return Command(
            goto=END,
            update={
                "messages": [
                    {"role": "assistant", "content": decision.output}
                ],
                "team_result": decision.output
            }
        )

    work_flow = StateGraph(TeamState)
    work_flow.add_node("entry_agent", entry_agent)
    work_flow.add_node("searcher", searcher)
    work_flow.add_node("analyzer", analyzer)
    work_flow.add_edge(START, "entry_agent")
    return work_flow.compile()


def build_dev_team():
    """개발팀: 하위 감독자가 코더/리뷰어 조율 (생략)"""
    work_flow = StateGraph(TeamState)
    # ... 구현 생략 ...
    return work_flow.compile()


research_team = build_research_team()
dev_team = build_dev_team()


# ============================================================
# 최상위 감독자 그래프
# ============================================================

class TopState(TypedDict):
    messages: Annotated[list, add_messages]
    research_result: str
    dev_result: str
    round_count: int


def top_supervisor(
    state: TopState
) -> Command[Literal["research_team", "dev_team", "__end__"]]:
    count = state.get("round_count", 0) + 1
    if count >= 6:  # 안전장치
        return Command(goto=END, update={"round_count": count})

    supervisor_llm = llm.with_structured_output(TopSupervisorDecision)
    decision = supervisor_llm.invoke([
        {"role": "system", "content":
            "당신은 최상위 감독자입니다. "
            "리서치팀(research_team)과 개발팀(dev_team)을 보유하고 있습니다. "
            "각 팀의 결과를 검토하여 다음에 작업할 팀을 결정하세요. "
            "모든 작업이 완료되었다면 finish를 선택하세요."},
        *state["messages"]
    ])

    if decision.next_team == "finish":
        return Command(
            goto=END,
            update={"round_count": count}
        )

    return Command(
        goto=decision.next_team,
        update={
            "round_count": count,
            "messages": [
                {"role": "assistant",
                 "content": f"[배분] {decision.reasoning}"}
            ]
        }
    )


def research_team_node(state: TopState) -> dict:
    result = research_team.invoke({
        "messages": state["messages"],
        "team_result": ""
    })
    return {
        "messages": result["messages"],
        "research_result": result.get("team_result", "")
    }


def dev_team_node(state: TopState) -> dict:
    result = dev_team.invoke({
        "messages": state["messages"],
        "team_result": ""
    })
    return {
        "messages": result["messages"],
        "dev_result": result.get("team_result", "")  # ← 버그 수정
    }


# ============================================================
# 그래프 조립
# ============================================================

work_flow = StateGraph(TopState)
work_flow.add_node("supervisor", top_supervisor)
work_flow.add_node("research_team", research_team_node)
work_flow.add_node("dev_team", dev_team_node)

work_flow.add_edge(START, "supervisor")
work_flow.add_edge("research_team", "supervisor")
work_flow.add_edge("dev_team", "supervisor")

graph = work_flow.compile()