from openai import OpenAI
from pydantic import BaseModel
import json
 
client = OpenAI()
 
def call_with_recovery(
    messages: list[dict],
    response_model: type[BaseModel],
    max_retries: int = 3
) -> BaseModel | None:
    """LLM 호출 + Pydantic 검증, 실패 시 자동 재시도"""
 
    for attempt in range(max_retries):
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=messages,
            response_format={"type": "json_object"}
        )
 
        raw = response.choices[0].message.content
 
        try:
            data = json.loads(raw)
            return response_model.model_validate(data)
        except Exception as e:
            print(f"[시도 {attempt + 1}] 검증 실패: {e}")

            # 에러 정보를 대화에 추가해서 LLM이 수정하도록 유도
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"출력이 올바르지 않습니다. 오류: {e}. 올바른 형식으로 다시 시도하세요."
            })
 
    print("최대 재시도 횟수 초과")
    return None
