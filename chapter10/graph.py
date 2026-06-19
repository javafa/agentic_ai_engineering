#   retrieve > codegen > (위험? human_gate) > execute
#     > 에러? codegen(계층2) / 성공? interpret > review
#     > revise? codegen(계층1, 4) / ok? remember > END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from state import AnalystState
from nodes import (retrieve, codegen, human_gate, execute, give_up,
                   interpret, review, remember,
                   route_after_codegen, route_after_execute, route_after_review)

wf = StateGraph(AnalystState)
wf.add_node("retrieve", retrieve)
wf.add_node("codegen", codegen)
wf.add_node("human_gate", human_gate)
wf.add_node("execute", execute)
wf.add_node("give_up", give_up)
wf.add_node("interpret", interpret)
wf.add_node("review", review)
wf.add_node("remember", remember)

wf.add_edge(START, "retrieve")
wf.add_edge("retrieve", "codegen")
wf.add_conditional_edges("codegen", route_after_codegen,
                         {"human_gate": "human_gate", "execute": "execute"})
wf.add_conditional_edges("execute", route_after_execute,
                         {"codegen": "codegen", "give_up": "give_up", "interpret": "interpret"})
wf.add_edge("interpret", "review")
wf.add_conditional_edges("review", route_after_review,
                         {"codegen": "codegen", "remember": "remember"})
wf.add_edge("give_up", END)
wf.add_edge("remember", END)

# 승인 게이트의 interrupt 때문에 checkpointer가 필요하다(7장 참고).
graph = wf.compile(checkpointer=MemorySaver())

def ask(question: str, thread_id: str = "session-1") -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    init = {"question": question, "code_attempts": 0, "review_rounds": 0,
            "error": None, "review_feedback": "", "history": []}
    state = graph.invoke(init, config=config)
    while "__interrupt__" in state:               # 승인 게이트에서 멈춤 > 사용자에 확인
        p = state["__interrupt__"][0].value
        print("승인 필요:", p["issues"]); print(p["code"])
        state = graph.invoke(Command(resume=input("실행할까요? (y/n): ")), config=config)
    return state

if __name__ == "__main__":
    out = ask("지역(pickup_borough)별 평균 요금을 막대그래프로 보여줘")
    print("\n[답변]\n", out["answer"])
