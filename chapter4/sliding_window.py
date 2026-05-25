from openai import OpenAI
from dotenv import load_dotenv
import tiktoken
 
def count_tokens(messages: list[dict], model: str = "gpt-5.4-mini") -> int:
    """메시지 리스트의 총 토큰 수를 계산합니다."""
    enc = tiktoken.get_encoding("o200k_base")  # gpt-5.4-mini용 인코딩
    total = 0
    for msg in messages:
        # 메시지 오버헤드: role, content 구분 등 약 4토큰
        total += 4
        total += len(enc.encode(msg["content"]))
    total += 2  # 시작/끝 토큰
    return total
 
def sliding_window_memory(
    messages: list[dict],
    max_tokens: int = 4000,
    system_msg: dict | None = None
) -> list[dict]:
    """최근 메시지만 유지하되, 토큰 한도를 넘지 않도록 조절합니다."""
    if system_msg:
        reserved = count_tokens([system_msg])
    else:
        reserved = 0
 
    # 뒤에서부터 메시지를 추가하며 토큰 수 확인
    result = []
    current_tokens = reserved
 
    for msg in reversed(messages):
        msg_tokens = count_tokens([msg])
        if current_tokens + msg_tokens > max_tokens:
            break
        result.insert(0, msg)
        current_tokens += msg_tokens
 
    # 시스템 메시지는 항상 맨 앞에 유지
    if system_msg:
        result.insert(0, system_msg)
 
    return result

 
load_dotenv()
client = OpenAI()  # OPENAI_API_KEY 환경변수 자동 로드
 
def chat_with_memory():
    """단기 메모리가 있는 챗봇"""
    
    messages = [
        {"role": "system", "content": "당신은 친절한 AI 비서입니다."}
    ]
 
    print("대화를 시작합니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break

        messages.append({"role": "user", "content": user_input})
        
        # 먼저 시스템 메시지와 대화 목록을 분리한다. 대화 목록을 기준으로 슬라이딩 되기 때문이다.
        system_msg = next((m for m in messages if m["role"] == "system"), None)
        chat_history = [m for m in messages if m["role"] != "system"]

        # 슬라이딩 윈도우 적용 (예시로 500토큰 제한 설정)
        # 실제 환경에서는 모델의 context window에 맞춰 4000~128000 등으로 설정합니다.
        windowed_history = sliding_window_memory(
            messages=chat_history, 
            max_tokens=500, 
            system_msg=system_msg
        )
        
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=windowed_history
        )
 
        assistant_msg = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_msg})
 
        print(f"\nAI: {assistant_msg}")
 
if __name__ == "__main__":
    chat_with_memory()