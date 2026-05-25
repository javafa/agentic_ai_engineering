from anthropic import Anthropic
from dotenv import load_dotenv
import json

load_dotenv()
client = Anthropic()

# Anthropic
tools = [
    {
        "name": "restaurant_recommendations",
        "description": "추천 맛집 목록을 구조화된 형식으로 반환합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "restaurants": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "cuisine": {"type": "string"},
                            "reason": {"type": "string"}
                        },
                        "required": ["name", "cuisine", "reason"]
                    }
                }
            },
            "required": ["restaurants"]
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system="맛집 정보를 제공합니다.",
    messages=[
        {"role": "user", "content": "서울의 맛집 3곳 추천해줘"}
    ],
    tools=tools,
    # tool_choice로 특정 도구를 강제하면 스키마에 맞는 출력을 보장한다
    tool_choice={"type": "tool", "name": "restaurant_recommendations"}
)

# tool_use 블록의 input이 곧 스키마에 맞는 구조화된 데이터
data = next(b.input for b in response.content if b.type == "tool_use")
for r in data["restaurants"]:
    print(f"{r['name']} ({r['cuisine']}): {r['reason']}")
