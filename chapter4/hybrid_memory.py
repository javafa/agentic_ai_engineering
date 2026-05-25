from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

class HybridTokenMemory:

    def __init__(self, threshold=4000, model="claude-sonnet-4-5"):
        self.threshold = threshold
        self.model = model
        self.messages = []      # Sliding Window: 최근 대화 원문
        self.summary = None     # Summary: 이전 대화들의 압축본
        self.system_prompt = "당신은 친절한 AI 비서입니다."

    def get_system(self) -> str:
        """요약을 포함한 시스템 프롬프트를 반환합니다."""
        if self.summary:
            return f"{self.system_prompt}\n\n이것은 이전 대화의 요약입니다: {self.summary}"
        return self.system_prompt

    def _count_tokens(self, msgs: list[dict]) -> int:
        """Anthropic count_tokens API로 메시지 목록의 총 토큰 수를 계산합니다."""
        if not msgs:
            return 0
        response = client.messages.count_tokens(
            model=self.model,
            system=self.get_system(),
            messages=msgs,
        )
        return response.input_tokens

    def add_message(self, role, content):
        """새 메시지를 추가하고, 임계값을 넘으면 요약 프로세스를 실행합니다."""
        self.messages.append({"role": role, "content": content})

        # 현재 전체 토큰(시스템 프롬프트 + 요약본 + 대화 리스트) 계산
        if self._count_tokens(self.messages) > self.threshold:
            self._compress_memory()

    def _compress_memory(self):
        """임계값 초과 시, 앞부분 메시지의 절반을 요약본에 합치고 리스트에서 제거합니다."""
        mid = len(self.messages) // 2
        # Claude는 user 메시지로 시작해야 하므로 분할 지점을 user 메시지에 맞춘다
        while mid < len(self.messages) and self.messages[mid]["role"] != "user":
            mid += 1
        to_summarize = self.messages[:mid]
        self.messages = self.messages[mid:] # 슬라이딩 윈도우 적용 (절반 제거)

        text_to_sum = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])

        print(f"\n[시스템] 토큰 한도 초과로 인한 요약 업데이트 중...")

        # Claude를 사용하여 기존 요약과 새 대화를 병합 요약
        response = client.messages.create(
            model=self.model,
            max_tokens=1024,
            system="당신은 대화의 핵심 맥락과 중요한 정보(이름, 장소, 결정사항)를 저장하는 요약 전문가입니다.",
            messages=[
                {"role": "user", "content": f"기존 요약: {self.summary}\n추가된 대화:\n{text_to_sum}\n\n위 내용을 합쳐서 하나의 간결한 요약으로 만들어주세요."}
            ]
        )
        self.summary = response.content[0].text

    def get_messages(self):
        """Claude에 전달할 최근 대화 메시지 리스트"""
        # 요약은 get_system()의 시스템 프롬프트에 포함되며,
        # 최근 상세 대화(Sliding Window)만 messages로 전달한다
        return self.messages

def chat_with_hybrid_memory():
    """하이브리드 메모리(슬라이딩 윈도우 + 요약) 챗봇"""
    # 1. 메모리 초기화 - threshold를 작게 잡으면 짧은 대화에서도 요약 동작을 관찰할 수 있다.
    memory = HybridTokenMemory(threshold=2000)

    print("하이브리드 메모리 챗봇입니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break

        # 2. 사용자 메시지 추가
        memory.add_message("user", user_input)

        # 3. Claude 호출
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=memory.get_system(),
            messages=memory.get_messages() # 슬라이딩 윈도우에 남아 있는 최근 대화 원문만 전달
        )

        assistant_msg = response.content[0].text

        # 4. AI 응답도 메모리에 저장 - 응답이 추가되면서 다시 임계값을 넘으면 자동으로 요약이 일어난다)
        memory.add_message("assistant", assistant_msg)
        print(f"\nAI: {assistant_msg}")

        # 5. 현재 메모리 상태를 표시해서 슬라이딩/요약 동작을 눈으로 확인
        if memory.summary:
            print(f"  [요약 존재: {len(memory.summary)}자]")
        print(f"  [활성 메시지: {len(memory.messages)}개]")

if __name__ == "__main__":
    chat_with_hybrid_memory()
