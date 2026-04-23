import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

class HybridTokenMemory:
    def __init__(self, threshold=4000, model="gpt-5.4-mini"):
        self.threshold = threshold
        self.model = model
        self.enc = tiktoken.get_encoding("o200k_base")
        self.messages = []      # Sliding Window: 최근 대화 원문
        self.summary = None     # Summary: 이전 대화들의 압축본
        self.system_msg = {"role": "system", "content": "당신은 친절한 AI 비서입니다."}

    def _count_tokens(self, msgs: list[dict]) -> int:
        """메시지 리스트의 총 토큰 수를 계산합니다."""
        total = 0
        for msg in msgs:
            total += 4 # role, content 오버헤드
            total += len(self.enc.encode(msg["content"]))
        total += 2
        return total

    def add_message(self, role, content):
        """새 메시지를 추가하고, 임계값을 넘으면 요약 프로세스를 실행합니다."""
        self.messages.append({"role": role, "content": content})
        
        # 현재 전체 토큰(시스템 메시지 + 요약본 + 대화 리스트) 계산
        current_context = self.get_messages()
        if self._count_tokens(current_context) > self.threshold:
            self._compress_memory()

    def _compress_memory(self):
        """임계값 초과 시, 앞부분 메시지의 절반을 요약본에 합치고 리스트에서 제거합니다."""
        mid = len(self.messages) // 2
        to_summarize = self.messages[:mid]
        self.messages = self.messages[mid:] # 슬라이딩 윈도우 적용 (절반 제거)

        text_to_sum = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])
        
        print(f"\n[시스템] 토큰 한도 초과로 인한 요약 업데이트 중...")
        
        # LLM을 사용하여 기존 요약과 새 대화를 병합 요약
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "당신은 대화의 핵심 맥락과 중요한 정보(이름, 장소, 결정사항)를 보존하는 요약 전문가입니다."},
                {"role": "user", "content": f"기존 요약: {self.summary}\n추가된 대화:\n{text_to_sum}\n\n위 내용을 합쳐서 하나의 간결한 요약으로 만들어주세요."}
            ]
        )
        self.summary = response.choices[0].message.content

    def get_messages(self):
        """LLM에 전달할 최종 메시지 리스트를 구성합니다."""
        full_context = [self.system_msg]
        
        # 요약본이 있다면 시스템 메시지 바로 뒤에 배치
        if self.summary:
            full_context.append({
                "role": "system", 
                "content": f"이것은 이전 대화의 요약입니다: {self.summary}"
            })
            
        # 최근 상세 대화(Sliding Window) 추가
        return full_context + self.messages

# --- 실행 예시 ---
def chat_hybrid():
    # 테스트를 위해 threshold를 낮게 설정 가능 (예: 500)
    memory = HybridTokenMemory(threshold=2000)
    
    print("하이브리드 메모리 챗봇입니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break
            
        memory.add_message("user", user_input)
        
        # AI 응답 생성
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=memory.get_messages()
        )
        
        ai_msg = response.choices[0].message.content
        memory.add_message("assistant", ai_msg)
        
        print(f"\nAI: {ai_msg}")
        
        # 상태 확인용 출력
        current_tokens = memory._count_tokens(memory.get_messages())
        print(f"  [상태] 토큰: {current_tokens} | 윈도우 내 메시지: {len(memory.messages)}개 | 요약 존재: {bool(memory.summary)}")


if __name__ == "__main__":
    chat_hybrid()