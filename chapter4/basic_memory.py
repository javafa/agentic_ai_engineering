from anthropic import Anthropic
from dotenv import load_dotenv
 
load_dotenv()
client = Anthropic()  # .env에 작성된 ANTHROPIC_API_KEY 환경변수 자동 로드
 
def chat_with_memory():
    """단기 메모리가 있는 챗봇"""
    # 1. 메시지 저장소 - 사용자 대화와, ai 응답을 모두 저장
    messages = [
        {"role": "system", "content": "당신은 친절한 AI 비서입니다."}
    ]
 
    print("대화를 시작합니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break

        # 2. 사용자 메시지 저장
        messages.append({"role": "user", "content": user_input})
        
        # 3. 저장소에 있는 모든 내용으로 API 호출
        # messages에서 system 메시지를 분리한다 (Anthropic은 system이 별도 파라미터)
        system_text = next((m["content"] for m in messages
                             if m["role"] == "system"), "")
        chat_msgs = [m for m in messages if m["role"] != "system"]
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=system_text,
            messages=chat_msgs
        )

        assistant_msg = response.content[0].text
        
        # 4. AI 응답 저장
        messages.append({"role": "assistant", "content": assistant_msg})
 
        print(f"\nAI: {assistant_msg}")
 
if __name__ == "__main__":
    chat_with_memory()
