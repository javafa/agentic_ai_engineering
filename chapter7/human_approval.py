from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

class State(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """이메일을 발송합니다."""
    return f"{to}에게 '{subject}' 이메일 발송 완료"

tools = [send_email]
llm = ChatAnthropic(model="claude-sonnet-4-6").bind_tools(tools, tool_choice="any") # tool_choice 옵션이 any 이면 꼭 하나를 선택한다. 

def agent_node(state: State) -> dict:
    return {"messages": [llm.invoke(state["messages"])]}

# 그래프 구성
work_flow = StateGraph(State)
work_flow.add_node("agent", agent_node)
work_flow.add_node("tools", ToolNode(tools))

work_flow.add_edge(START, "agent")
work_flow.add_conditional_edges("agent", tools_condition)
work_flow.add_edge("tools", "agent")

# 핵심: tools 노드 실행 전에 중단!
memory = MemorySaver()
graph = work_flow.compile(
    checkpointer=memory,
    interrupt_before=["tools"]  # Tool 실행 전 멈춤
)

config = {"configurable": {"thread_id": "approval_demo"}}

# 1단계: 에이전트 실행 (Tool 호출 직전에 멈춤)
result = graph.invoke(
    {"messages": [
        ("user", "팀장에게 회의 일정 변경 이메일 보내줘")
    ]},
    config=config
)

last_msg = result["messages"][-1]
# tool 호출 없을 경우 예외처리
# if not last_msg.tool_calls:
#     print("LLM이 tool을 호출하지 않았습니다. 응답 내용:")
#     print(last_msg.content)
#     raise SystemExit(0)

pending_call = last_msg.tool_calls[0]

print(f"보류 중인 작업: {pending_call['name']}")
print(f"  수신자: {pending_call['args']['to']}")
print(f"  제목: {pending_call['args']['subject']}")

# 2단계: 사용자 승인 후 계속 실행
approval = input("이메일을 발송할까요? (y/n): ")
if approval.lower() == "y":
    # None을 보내면 중단된 지점부터 계속 실행
    result = graph.invoke(None, config=config)
    print(result["messages"][-1].content)
else:
    print("발송이 취소되었습니다.")

