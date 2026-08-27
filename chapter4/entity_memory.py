import json
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

class EntityMemory:
    """대화에서 엔티티(사람, 장소, 일정 등)를 추출해 구조화 저장한다."""

    EXTRACT_PROMPT = """다음 대화에서 정보를 추출하고 JSON 형식으로만 반환합니다.
        형식: {"entities": [
                {"name": "...", "facts": ["..."],
                "type": "person|place|event|preference"}]}
        새로운 정보만 추출하는데 인사말이나 감정 표현은 제외합니다.
        설명 없이 JSON 객체만 출력합니다."""

    def __init__(self):
        self.entities: dict[str, dict] = {}  # name -> {type, facts}

    def extract_and_store(self, user_msg: str, ai_msg: str):
        """대화에서 엔티티를 추출하고 저장한다."""
        # Anthropic에는 response_format 같은 JSON 강제 옵션이 없으므로,
        # assistant 메시지를 "{"로 미리 채워(prefill) JSON 출력을 유도한다.
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=self.EXTRACT_PROMPT,
            messages=[
                {"role": "user", "content": f"User: {user_msg}\nAI: {ai_msg}"},
                {"role": "assistant", "content": "{"}
            ]
        )

        try:
            # prefill한 "{"를 응답 앞에 다시 붙여 완전한 JSON으로 만든다
            data = json.loads("{" + response.content[0].text)
            for entity in data.get("entities", []):
                name = entity["name"]
                if name in self.entities:
                    # 기존 엔티티에 새 정보 추가 (중복 제거)
                    existing = set(self.entities[name]["facts"])
                    existing.update(entity["facts"])
                    self.entities[name]["facts"] = list(existing)
                else:
                    self.entities[name] = {
                        "type": entity["type"],
                        "facts": entity["facts"]
                    }
        except (json.JSONDecodeError, KeyError):
            pass  # 추출 실패 시 무시

    def get_context(self) -> str:
        """저장된 엔티티 정보를 시스템 프롬프트용 텍스트로 변환한다."""
        if not self.entities:
            return ""
        lines = ["알려진 정보:"]
        for name, info in self.entities.items():
            facts_str = ", ".join(info["facts"])
            lines.append(f"- {name} ({info['type']}): {facts_str}")
        return "\n".join(lines)


def chat_with_entity_memory():
    """엔티티 메모리 챗봇"""
    # 1. 엔티티 메모리 + 대화 기록 초기화
    memory = EntityMemory() # 대화 전반에서 추출된 사람/장소/일정 등을 구조화 저장
    messages = [] # 한 세션 안에서의 대화 흐름 (Claude messages 파라미터로 전달)
    base_system = "당신은 친절한 AI 비서입니다."

    print("엔티티 메모리 챗봇입니다. (종료: quit)")
    while True:
        user_input = input("\n사용자: ")
        if user_input.lower() == "quit":
            break

        # 2. 사용자 메시지를 대화 기록에 추가
        messages.append({"role": "user", "content": user_input})

        # 3. 엔티티가 하나도 없을 때는 base_system만 사용
        entity_context = memory.get_context()
        system_prompt = (
            f"{base_system}\n\n{entity_context}" if entity_context else base_system
        )

        # 4. Claude 호출
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )

        assistant_msg = response.content[0].text
        messages.append({"role": "assistant", "content": assistant_msg})
        print(f"\nAI: {assistant_msg}")

        # 5. 내부적으로 Claude를 한 번 더 호출해 JSON으로 엔티티를 뽑아낸다.
        memory.extract_and_store(user_input, assistant_msg)

        # 6. 디버깅
        if memory.entities:
            names = ", ".join(memory.entities.keys())
            print(f"  [엔티티 {len(memory.entities)}개: {names}]")

if __name__ == "__main__":
    chat_with_entity_memory()
