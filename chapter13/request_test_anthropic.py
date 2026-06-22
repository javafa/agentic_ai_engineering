from anthropic import Anthropic

# api_key는 필수 항목이므로 아무 문자열("EMPTY")이나 입력합니다.
client = Anthropic(base_url="http://localhost:8000", api_key="EMPTY")

resp = client.messages.create(
    model="Qwen/Qwen2.5-3B-Instruct",
    max_tokens=1024,
    system="당신은 친절한 한국어 비서입니다.",  # Anthropic은 system을 상위 인자로 분리합니다
    messages=[
        {"role": "user", "content": "vLLM이 무엇인지 한 문장으로 설명해줘."},
    ],
    temperature=0.3,
)

print(resp.content[0].text)
