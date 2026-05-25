from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

text = "안녕하세요, Claude의 토큰 수를 측정합니다!"

# 메시지의 토큰 수 계산 (Anthropic 공식 count_tokens API)
response = client.messages.count_tokens(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": text}]
)

# 입력 토큰 수 (실제 호출에 사용되는 토크나이저와 동일하게 계산됨)
print("총 토큰 수:", response.input_tokens)
# 출력 예시: 총 토큰 수: 31
