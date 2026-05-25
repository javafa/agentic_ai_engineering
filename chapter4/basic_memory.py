from openai import OpenAI
from dotenv import load_dotenv
 
load_dotenv()
client = OpenAI()  # OPENAI_API_KEY 환경변수 자동 로드
 
def chat_with_memory():
    """단기 메모리가 있는 챗봇"""
    
		# 1. 메시지 저장소 - 사용자 대화와, ai 응답이 모두 저장 된다
    messages = [
        {"role": "system", "content": "당신은 친절한 AI 비서입니다."}
    ]
 
    print("대화를 시작합니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break
        
				# 2 사용자 메시지를 저장
        messages.append({"role": "user", "content": user_input})
        
        # 3 저장소에 있는 모든 내용으로 API 호출
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=messages
        )
 
        assistant_msg = response.choices[0].message.content
        
        # 4 AI 응답도 저장
        messages.append({"role": "assistant", "content": assistant_msg})
 
        print(f"\nAI: {assistant_msg}")
 
if __name__ == "__main__":
    chat_with_memory()
