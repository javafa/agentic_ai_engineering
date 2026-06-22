import time
from anthropic import Anthropic

# vLLM 서버를 Anthropic 호환 엔드포인트로 사용
client = Anthropic(base_url="http://localhost:8000", api_key="EMPTY")

# 길고 고정된 앞부분 설정
SYS = "당신은 시니어 데이터 분석가입니다. " * 50

def ask(q):
    t0 = time.time()
    r = client.messages.create(
        model="Qwen/Qwen2.5-3B-Instruct",
        system=SYS,                                # system은 top-level 파라미터로 분리
        messages=[{"role": "user", "content": q}], # user 메시지만 전달
        max_tokens=64,
    )
    return time.time() - t0

# 효과 측정
print("1차 실행:", round(ask("매출 추세를 요약해줘"), 3), "초")  # 앞부분 새로 계산
print("2차 실행:", round(ask("이상치를 찾아줘"), 3), "초")     # 앞부분 캐시 적중
