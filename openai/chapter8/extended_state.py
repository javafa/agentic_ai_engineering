from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv()

# 상태 커스터 마이징
class ExtendedState(TypedDict):
    messages: Annotated[list, add_messages]
    classification: str   # 분류
    step: int             # 단계

llm = ChatOpenAI(model="gpt-5.4-mini")

# 분류 노드
def classify(state: ExtendedState):
    user_msg = state["messages"][-1].content
    res = llm.invoke(f"""
    질문을 다음 중 하나로 분류한다:
    tech / business / general
    질문: {user_msg}
    """)

    return {
        "classification": res.content.strip(),
        "step": state.get("step", 0) + 1
    }

# 응답 노드
def respond(state: ExtendedState):
    category = state["classification"]
    res = llm.invoke(f"""
    너는 {category} 전문가야.
    질문에 전문지식을 활용해서 답을 해야돼:
    {state["messages"][-1].content}
    """)

    return {
        "messages": [res],
        "step": state["step"] + 1
    }

# 그래프
work_flow = StateGraph(ExtendedState)

work_flow.add_node("classify", classify)
work_flow.add_node("respond", respond)

work_flow.add_edge(START, "classify")
work_flow.add_edge("classify", "respond")
work_flow.add_edge("respond", END)

graph = work_flow.compile()

# 실행
result = graph.invoke({
    "messages": [("user", "LangGraph가 뭐야?")]
})

print("분류:", result["classification"])
print("단계:", result["step"])
print("응답:", result["messages"][-1].content[:100])
