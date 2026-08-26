from pydantic import BaseModel, Field, field_validator
from langchain_core.output_parsers import PydanticOutputParser
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
load_dotenv()

# 원하는 출력 구조를 Pydantic 모델로 정의
class TaskPlan(BaseModel):
    """에이전트의 작업 계획"""
    goal: str = Field(description="달성할 목표")
    steps: list[str] = Field(description="실행 단계들")
    estimated_minutes: int = Field(description="예상 소요 시간(분)")
 
    @field_validator("estimated_minutes")
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("소요 시간은 양수여야 합니다")
        return v
 
# 파서 생성 (자동으로 포맷팅된 지시문 생성)
parser = PydanticOutputParser(pydantic_object=TaskPlan)
 
# 파서가 생성한 지시문 확인
print(parser.get_format_instructions())
 
# LLM에게 요청
llm = ChatAnthropic(model="claude-sonnet-4-5")

prompt = f"""다음 작업의 실행 계획을 세워주세요.
작업: 블로그 포스트 작성하기
{parser.get_format_instructions()}"""
 
response = llm.invoke(prompt)
 
# 응답을 Pydantic 모델로 파싱 + 검증
try:
    plan = parser.parse(response.content)
    print(f"목표: {plan.goal}")
    print(f"단계: {len(plan.steps)}개")
    print(f"예상 시간: {plan.estimated_minutes}분")
except Exception as e:
    print(f"파싱 실패: {e}")
