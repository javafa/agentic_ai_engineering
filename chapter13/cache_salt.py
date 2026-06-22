import time
from anthropic import Anthropic

# vLLM 서버를 Anthropic 호환 엔드포인트로 사용
client = Anthropic(base_url="http://localhost:8000", api_key="EMPTY")

SYSTEM = "당신은 시니어 데이터 분석가입니다. "

# API 요청 시 extra_body에 사용자별 솔트(Salt) 값을 주입
response = client.messages.create(
    model="Qwen/Qwen2.5-3B-Instruct",
    system=SYSTEM,
    messages=[{"role": "user", "content": "이번 분기 매출 분석"}],
    max_tokens=64,
    extra_body={"cache_salt": "tenant-A"},  # 같은 솔트 값을 가진 요청끼리만 캐시 공유
)

print("응답결과 :", response.content[0].text)