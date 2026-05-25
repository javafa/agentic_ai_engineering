from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv()

# 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]

# LLM
llm = ChatOpenAI(model="gpt-5.4-mini", streaming=True)

# 노드
def chatbot(state: State):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

# 그래프 구성
work_flow = StateGraph(State)
work_flow.add_node("chatbot", chatbot)

work_flow.add_edge(START, "chatbot")
work_flow.add_edge("chatbot", END)

graph = work_flow.compile()

# 실행
for event in graph.stream(
    {"messages": [("user", "AI가 세상을 바꾸는 이유 3가지만 말해줘")]},
    stream_mode="messages"
):
    print(event)