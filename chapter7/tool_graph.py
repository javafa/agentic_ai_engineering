from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from dotenv import load_dotenv
 
load_dotenv()
 
# 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]
# Tool 정의
@tool
def calculate(expression: str) -> str:
    """수학 계산을 수행합니다. 예: 2 + 3 * 4"""
    try:
        # 주의: 실전에서는 eval 대신 안전한 파서를 사용하세요!
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"계산 오류: {e}"
 
@tool
def get_weather(city: str) -> str:
    """도시의 현재 날씨를 조회합니다."""
    weather = {"서울": "맑음 22도", "부산": "흐림 19도", "제주": "비 18도"}
    return weather.get(city, f"{city}의 날씨 정보 없음")

# Tool 연결
tools = [calculate, get_weather]
llm = ChatAnthropic(model="claude-sonnet-4-6").bind_tools(tools)

# agent 노드 함수 정의
def agent_node(state: State) -> dict:
    """에이전트 (LLM) 노드"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


# 워크플로우 구성
work_flow = StateGraph(State)
 
# 노드 추가
work_flow.add_node("agent", agent_node) # 2단계, 5단계
work_flow.add_node("tools", ToolNode(tools)) # 4단계
 
# 엣지 연결
work_flow.add_edge(START, "agent") # 1단계
work_flow.add_conditional_edges("agent", tools_condition) # 3단계, 6단계
 
# Tool 실행 후 다시 에이전트로 (루프!)
work_flow.add_edge("tools", "agent")
 
# 컴파일 & 실행
graph = work_flow.compile()

# 사용자 요청 및 메시지 저장
result = graph.invoke(
    {"messages": [("user", "서울 날씨 알려주고, 15 * 24가 얼마인지 계산해줘")]} # 요청 > START
)
# 6단계 : 종료후 invoke 를 빠져나온다.
# 종료 후 출력
print(result["messages"][-1].content)
