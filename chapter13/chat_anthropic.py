from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic

# (1) 모델 선언부에서 api_url을 로컬 vLLM으로 변경
llm = ChatAnthropic(
    model="Qwen/Qwen2.5-3B-Instruct",
    base_url="http://localhost:8000",
    anthropic_api_key="EMPTY",
    temperature=0,
)

class State(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot(state: State) -> dict:
    # 기존 인터페이스(invoke, stream 등)가 완벽히 호환되므로 노드 함수 수정 불필요
    return {"messages": [llm.invoke(state["messages"])]}

# (2) 그래프 정의 및 컴파일 (수정 없음)
work_flow = StateGraph(State)
work_flow.add_node("chatbot", chatbot)
work_flow.add_edge(START, "chatbot")
work_flow.add_edge("chatbot", END)
graph = work_flow.compile()

# 실행 테스트
result = graph.invoke({"messages": [("user", "에이전트가 뭐야? 한 문장으로.")]})
print(result["messages"][-1].content)
