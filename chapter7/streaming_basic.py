from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic

from dotenv import load_dotenv
load_dotenv()

# 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]

# LLM
llm = ChatAnthropic(model="claude-sonnet-5", streaming=True,
                    thinking={"type": "disabled"})

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

for event in graph.stream(
    {"messages": [("user", "AI가 세상을 바꾸는 이유 3가지만 말해줘")]},
    stream_mode="messages"
):
    chunk, metadata = event
    
    # 청크에 내용(content)이 있을 때만 실시간으로 출력 (end=""로 줄바꿈 방지)
    if chunk.content:
        print(chunk.content, end="", flush=True)

print() # 마지막 줄 바꿈 처리