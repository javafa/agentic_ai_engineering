from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool

from dotenv import load_dotenv
load_dotenv()

@tool
def get_weather(city: str) -> str:
    """도시의 현재 날씨를 조회합니다."""
    # 더미 데이터
    weather_data = {"서울": "맑음, 22도", "부산": "흐림, 19도"}
    return weather_data.get(city, f"{city}의 날씨 정보가 없습니다.")

# 체크포인터 생성
memory = MemorySaver()

# 에이전트에 체크포인터 연결
llm = ChatAnthropic(model="claude-sonnet-4-5")
agent = create_agent(llm, [get_weather], checkpointer=memory)

# thread_id로 대화 구분
config1 = {"configurable": {"thread_id": "user_A_session_1"}}
config2 = {"configurable": {"thread_id": "user_B_session_1"}}

# 사용자 A의 대화
result1 = agent.invoke(
    {"messages": [("user", "서울 날씨 어때?")]},
    config=config1
)
print("사용자 A:", result1["messages"][-1].content)

# 사용자 B의 대화 (다른 thread)
result2 = agent.invoke(
    {"messages": [("user", "부산 날씨 알려줘")]},
    config=config2
)
print("사용자 B:", result2["messages"][-1].content)

# 사용자 A가 이어서 대화 (이전 컨텍스트 자동 복원)
result3 = agent.invoke(
    {"messages": [("user", "아까 물어본 도시 말고, 부산은?")]},
    config=config1  # 같은 thread_id
)
print("사용자 A (계속):", result3["messages"][-1].content)
