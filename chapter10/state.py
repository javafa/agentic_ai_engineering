from typing import Annotated, Optional
from typing_extensions import TypedDict
from operator import add
from langchain_anthropic import ChatAnthropic
 
from config import MODEL, BOOTSTRAP_CODE
from executor import KernelExecutor
from memory import ExperienceMemory
 
llm = ChatAnthropic(model=MODEL, temperature=0)
KERNEL = KernelExecutor(bootstrap=BOOTSTRAP_CODE)   # 커널 하나를 계속 살려 둔다
MEMORY = ExperienceMemory()

class AnalystState(TypedDict):
    question: str                   # 사용자의 자연어 질문
    few_shots: list                 # 과거 성공 사례(외부 메모리에서 검색) — 계층 1
    code: str                       # 최신 생성 코드
    stdout: str                     # 실행 표준출력
    result: str                     # 실행 결과값
    images: list                    # 생성된 차트 파일 경로
    error: Optional[str]            # 실행 에러(없으면 None)
    traceback: str                  # 에러 트레이스백
    code_attempts: int              # 에러 자기수정 횟수 — 계층 2
    review_rounds: int              # 자기검토 재작성 횟수 — 계층 1, 4
    review_feedback: str            # 검토가 코드 생성에 주는 피드백
    verdict: str                    # 검토 결과: 'ok' │ 'revise'
    risky: list                     # 위험 요소(있으면 승인 게이트로) — 계층 4 하드
    answer: str                     # 최종 자연어 답변
    history: Annotated[list, add]   # 모든 시도 기록(평가, 디버깅용, 누적)
