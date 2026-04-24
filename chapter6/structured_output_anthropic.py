import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    tools=[
        {
            "name": "record_event",
            "description": "이벤트 정보를 기록합니다.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "date": {"type": "string"},
                    "location": {"type": "string"}
                },
                "required": ["name", "date", "location"]
            }
        }
    ],
    # 이 도구를 사용하도록 강제 (JSON만 출력됨)
    tool_choice={"type": "tool", "name": "record_event"},
    messages=[
        {"role": "user", "content": "내일 오후 2시에 강남역에서 영희랑 점심 약속 있어."}
    ]
)

print("Anthropic :")
event_data = response.content[0].input
print(event_data["name"])