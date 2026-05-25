from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

SYSTEM_PROMPT = "당신은 친절한 AI 비서입니다."

def count_tokens(messages: list[dict], system: str = SYSTEM_PROMPT) -> int:
    """Anthropic의 count_tokens API로 메시지 목록의 총 토큰 수를 계산합니다."""
    if not messages:
        return 0
    response = client.messages.count_tokens(
        model="claude-sonnet-4-5",
        system=system,
        messages=messages,
    )
    return response.input_tokens

def sliding_window_memory(
    messages: list[dict],
    max_tokens: int = 4000,
    system: str = SYSTEM_PROMPT
) -> list[dict]:
    """최근 메시지만 유지하되, 토큰 한도를 넘지 않도록 조절합니다."""
    # 전체 메시지가 한도 이내라면 그대로 사용
    if count_tokens(messages, system) <= max_tokens:
        return messages

    # —---- 핵심 코드 —-----------
    # 한도를 넘으면, user 메시지에서 시작하는 가장 긴 최근 구간을 찾는다
    # (Claude는 messages가 user 메시지로 시작해야 한다)
    for start in range(1, len(messages)):
        if messages[start]["role"] != "user":
            continue
        window = messages[start:]
        if count_tokens(window, system) <= max_tokens:
            return window
    # —---- 핵심 코드 —-----------
    return messages[-1:]


def chat_with_memory():
    # 1. 메시지 저장소 - 사용자 대화와, ai 응답을 모두 저장
    #    (Anthropic은 system을 별도 파라미터로 받으므로 messages에 포함하지 않는다)
    messages = []

    print("대화를 시작합니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break

        # 2. 사용자 메시지 저장
        messages.append({"role": "user", "content": user_input})

        # 3. 슬라이딩 윈도우 적용 (예시로 500토큰 제한 설정)
        #    실제 환경에서는 모델의 context window에 맞춰 4000~200000 등으로 설정합니다.
        windowed_history = sliding_window_memory(
            messages=messages,
            max_tokens=500,
            system=SYSTEM_PROMPT
        )

        # 4. 슬라이딩된 메시지로 API 호출
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=windowed_history
        )

        assistant_msg = response.content[0].text

        # 5. AI 응답 저장
        messages.append({"role": "assistant", "content": assistant_msg})

        print(f"\nAI: {assistant_msg}")

if __name__ == "__main__":
    chat_with_memory()