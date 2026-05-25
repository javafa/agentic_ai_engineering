from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition

from dotenv import load_dotenv
load_dotenv()

# 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def add(a: int, b: int) -> int:
    """두 수를 더합니다."""
    return a + b

tools = [add]

llm = ChatOpenAI(model="gpt-5.4-mini").bind_tools(tools)

def agent(state: State):
    return {"messages": [llm.invoke(state["messages"])]}

work_flow = StateGraph(State)

work_flow.add_node("agent", agent)
work_flow.add_node("tools", ToolNode(tools))

work_flow.add_edge(START, "agent")
work_flow.add_conditional_edges("agent", tools_condition)
work_flow.add_edge("tools", "agent")

graph = work_flow.compile()

for event in graph.stream(
    {"messages": [("user", "3 + 5 계산해줘")]},
    stream_mode="values"
):
    print("EVENT:", event)