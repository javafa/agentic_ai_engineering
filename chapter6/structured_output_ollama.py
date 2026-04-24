from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

# 1. 출력 구조 정의
class TaskPlan(BaseModel):
    goal: str = Field(description="달성할 목표")
    steps: list[str] = Field(description="실행 단계들")
    estimated_minutes: int = Field(description="예상 소요 시간(분)")

# 2. 로컬 모델 설정
# Llama나 Mistral 등 도구 호출에 강한 모델 권장
llm = ChatOllama(
    model="llama3.1", 
    temperature=0,
    format="json" # Ollama 엔진 레벨에서 JSON 출력을 강제
)

# 3. 구조화된 출력 인터페이스 바인딩
structured_llm = llm.with_structured_output(TaskPlan)

# 4. 실행
prompt = "블로그 포스트 작성하기 계획을 세워줘."

response = structured_llm.invoke(prompt)
    
# 결과는 이미 TaskPlan 객체입니다.
print(f"목표: {response.goal}")
print(f"단계: {response.steps}")
print(f"소요 시간: {response.estimated_minutes}분")
