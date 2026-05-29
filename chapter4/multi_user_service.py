"""
4.6.2.4 실전 응용: 다중 사용자 챗봇 서비스

앞에서 학습한 SQLiteSaver 체크포인터를 실제 서비스에 가깝게 응용한 예제입니다.
핵심 포인트:
  1) 사용자별 격리 - thread_id에 user_id를 매핑해 대화 상태를 분리
  2) DB 연결 재사용 - 요청마다 열고 닫지 않고, 서비스 수명 동안 유지
  3) Tool과 결합 - ReAct 에이전트가 실시간 정보 조회와 메모리를 함께 사용
"""

import datetime
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.agents import create_agent

load_dotenv()


# 1) 서비스용 Tool 정의
@tool
def get_current_time() -> str:
    """현재 시간을 ISO 8601 형식으로 반환합니다."""
    return datetime.datetime.now().isoformat(timespec="seconds")


@tool
def calculate(expression: str) -> str:
    """간단한 수학 수식을 계산합니다. 예: '12 * 7 + 3'"""
    try:
        return str(eval(expression, {"__builtins__": None}, {}))
    except Exception as e:
        return f"계산 오류: {e}"


# 2) 다중 사용자 챗봇 서비스 클래스
class ChatService:
    """SQLite 체크포인터 기반의 다중 사용자 챗봇 서비스."""

    def __init__(self, db_path: str = "service.db"):
        self.db_path = db_path
        self.tools = [get_current_time, calculate]
        self.model = ChatAnthropic(model="claude-sonnet-4-5")
        self._memory_cm = None
        self.agent = None

    def __enter__(self):
        # 서비스 시작 시 한 번만 DB를 연다 (요청마다 열고 닫지 않는다)
        self._memory_cm = SqliteSaver.from_conn_string(self.db_path)
        memory = self._memory_cm.__enter__()
        self.agent = create_agent(
            self.model, self.tools, checkpointer=memory
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 서비스 종료 시 DB 연결을 안전하게 해제
        if self._memory_cm:
            self._memory_cm.__exit__(exc_type, exc_val, exc_tb)

    def chat(self, user_id: str, message: str) -> str:
        """user_id별 독립된 대화 스레드로 메시지를 처리한다."""
        # thread_id가 곧 사용자 식별자가 된다 → 사용자마다 상태가 분리
        config = {"configurable": {"thread_id": user_id}}
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": message}]},
            config=config,
        )
        return result["messages"][-1].content


# 3) 서비스 실행 시뮬레이션
if __name__ == "__main__":
    # --- 첫 번째 서비스 가동 (두 사용자가 각자 대화) ---
    with ChatService("service.db") as svc:
        print("[Alice]", svc.chat("alice", "안녕, 내 이름은 앨리스고 강릉에 살아."))
        print("[Bob]  ", svc.chat("bob", "나는 밥이야. 다음 주 월요일에 시험이 있어."))
        print("[Alice]", svc.chat("alice", "지금 몇 시야?"))

    # --- 서비스 재시작 (프로세스 완전 종료 후 재기동 가정) ---
    print("\n--- 서비스 재시작 ---\n")
    with ChatService("service.db") as svc:
        # thread_id만 같으면 이전 대화가 그대로 복원된다
        print("[Alice]", svc.chat("alice", "내가 어디 산다고 했지?"))
        print("[Bob]  ", svc.chat("bob", "내가 다음 주에 뭐 한다고 했지?"))
