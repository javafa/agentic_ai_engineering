import tiktoken
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

class SummaryMemory:
    def __init__(self, threshold=3000):
        self.threshold = threshold
        self.messages = []
        self.summary = None
        self.enc = tiktoken.get_encoding("o200k_base")
        self.system_msg = {"role": "system", "content": "당신은 친절한 AI 비서입니다."}

    def _token_count(self, msgs):
        return sum(len(self.enc.encode(m["content"])) + 4 for m in msgs) + 2

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        
				# 메시지의 수가 threshold 보다 크면 절반은 요약, 나머지는 메시지 목록에 담는다
        if self._token_count(self.messages) > self.threshold:
            mid = len(self.messages) // 2
            to_sum = "\n".join(f"{m['role']}: {m['content']}" for m in self.messages[:mid])
            
            resp = client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=[
                    {"role": "system", "content": "개인정보/결정사항 위주 200단어 이내 요약 전문가"},
                    {"role": "user", "content": f"기존 요약: {self.summary}\n추가 대화:\n{to_sum}"}
                ]
            )
            self.summary = resp.choices[0].message.content
            self.messages = self.messages[mid:]

    def get_messages(self):
        res = [self.system_msg]
        if self.summary:
            res.append({"role": "system", "content": f"이전 대화 요약: {self.summary}"})
        return res + self.messages


def chat_with_summary_memory():
    memory = SummaryMemory(threshold=4000)
 
    print("요약 메모리 챗봇입니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break
 
        memory.add_message("user", user_input)
 
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=memory.get_messages()
        )
 
        assistant_msg = response.choices[0].message.content
        memory.add_message("assistant", assistant_msg)
        print(f"\nAI: {assistant_msg}")
 
        # 현재 메모리 상태 표시
        if memory.summary:
            print(f"  [요약 존재: {len(memory.summary)}자]")
        print(f"  [활성 메시지: {len(memory.messages)}개]")
 
if __name__ == "__main__":
    chat_with_summary_memory()
