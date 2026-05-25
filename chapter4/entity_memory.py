import json
from openai import OpenAI
 
client = OpenAI()
 
class EntityMemory:
    """대화에서 엔티티(사람, 장소, 일정 등)를 추출해 구조화 저장한다."""
 
    EXTRACT_PROMPT = """다음 대화에서 정보를 추출하고 JSON 형식으로 반환합니다.
 
    형식: {"entities": [{"name": "...", "type": "person|place|event|preference", "facts": ["..."]}]}
    
    새로운 정보만 추출하는데 인사말이나 감정 표현은 제외합니다."""
 
    def __init__(self):
        self.entities: dict[str, dict] = {}  # name -> {type, facts}
 
    def extract_and_store(self, user_msg: str, ai_msg: str):
        """대화에서 엔티티를 추출하고 저장한다."""
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[
                {"role": "system", "content": self.EXTRACT_PROMPT},
                {"role": "user", "content": f"User: {user_msg}\nAI: {ai_msg}"}
            ],
            response_format={"type": "json_object"}
        )
 
        try:
            data = json.loads(response.choices[0].message.content)
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
