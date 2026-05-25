from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv()
client = OpenAI()

# OpenAI
response = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[
        {"role": "system", "content": "맛집 정보를 제공합니다."},
        {"role": "user", "content": "서울의 맛집 3곳 추천해줘"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "restaurant_recommendations",
            "strict": True,
            "schema": {
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
                            "required": ["name", "cuisine", "reason"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["restaurants"],
                "additionalProperties": False
            }
        }
    }
)

data = json.loads(response.choices[0].message.content)

print("OpenAI :")

for r in data["restaurants"]:
    print(f"{r['name']} ({r['cuisine']}): {r['reason']}")

