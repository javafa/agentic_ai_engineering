from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
import datetime

load_dotenv()

# 1) 서비스용 Tool 정의
@tool
def get_current_time() -> str:
    """현재 시간을 반환합니다."""
    return datetime.datetime.now().isoformat(timespec="seconds")

# 2) 체크포인터를 받아 ReAct 에이전트를 만드는 함수
def build_agent(memory):
    """SQLite 체크포인터와 Tool을 연결한 ReAct 에이전트를 생성한다."""
    model = ChatAnthropic(model="claude-sonnet-4-5")
    tools = [get_current_time]
    return create_react_agent(model, tools, checkpointer=memory)

# 3) 사용자별 thread_id로 메시지를 보내고 답변을 받는 함수
def chat(agent, user_id: str, message: str) -> str:
    """thread_id에 user_id를 매핑해 사용자별 대화 상태를 분리한다."""
    config = {"configurable": {"thread_id": user_id}}
    result = agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    return result["messages"][-1].content

# 4) 서비스 실행 시뮬레이션
#    with 블록이 끝날 때 DB 연결이 안전하게 해제된다.
with SqliteSaver.from_conn_string("service.db") as memory:
    agent = build_agent(memory)
    print("[Alice]", chat(agent, "alice", "내 이름은 앨리스고 강릉에 살아."))
    print("[Bob]  ", chat(agent, "bob", "나는 밥이고 다음 주 월요일에 시험이 있어."))
