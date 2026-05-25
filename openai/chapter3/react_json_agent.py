import os, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# 1. 날씨 Tool 함수
def get_weather(city: str) -> str:
    """도시의 현재 날씨를 조회합니다."""
    weather_data = {
        'Seoul': {'temp': 18.5, 'description': '맑음', 'humidity': 45},
        'Tokyo': {'temp': 15.2, 'description': '가벼운 비', 'humidity': 78},
        'New York': {'temp': 22.1, 'description': '구름 많음', 'humidity': 55},
    }
    # 대소문자 구분 없이 처리하기 위해 title() 사용
    data = weather_data.get(city.title(), {'temp': 0, 'description': '알 수 없음', 'humidity': 0})
    return json.dumps({'city': city, **data}, ensure_ascii=False)

# 2. 계산 Tool
def calculate(expression: str) -> str:
    """수학 계산식을 계산합니다."""
    try:
        # 안전한 계산을 위해 아주 기본적인 제한만 둠
        result = eval(expression, {"__builtins__": None}, {})
        return json.dumps({'expression': expression, 'result': result})
    except Exception as e:
        return json.dumps({'error': str(e)})

# 3. 커스텀 Tool 스키마
TOOLS = {
    'get_weather': {
        'func': get_weather,
        'description': '도시의 기온, 날씨, 습도를 조회합니다.',
        'parameters': {'city': '영문 도시 이름 (예: Seoul, Tokyo)'},
    },
    'calculate': {
        'func': calculate,
        'description': '수학 계산식을 평가합니다.',
        'parameters': {'expression': '계산할 수식 (예: 2+3*4)'},
    },
}

def build_tool_description() -> str:
    lines = ["사용 가능한 Tool 목록:"]
    for name, info in TOOLS.items():
        lines.append(f"- {name}: {info['description']}")
        lines.append(f"  매개변수: {info['parameters']}")
    return '\n'.join(lines)

# 4. 시스템 프롬프트 개선 (역할 분담 명확화)
SYSTEM_PROMPT = f"""당신은 유능한 AI 에이전트입니다. 사용자의 질문에 답하기 위해 Tool을 사용할 수 있습니다.

{build_tool_description()}

**응답 규칙:**
1. 반드시 JSON 형식으로만 응답하십시오.
2. 정보가 부족하여 Tool이 필요하다면 'action' 형식을 사용하세요.
3. Tool 결과(Observation)를 확인한 후 답변이 가능하다면 'answer' 형식을 사용하세요.

**JSON 응답 형식:**
1) Tool 호출 시:
{{"thought": "상황 분석", "action": "Tool_이름", "action_input": {{"매개변수명": "값"}}}}

2) 최종 답변 시:
{{"thought": "최종 분석", "answer": "사용자에게 전달할 답변"}}
"""

def parse_llm_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # JSON 형식이 아닐 경우를 대비한 최소한의 방어 로직
        return {"thought": "Parsing failed", "answer": text}

def run_react_json_agent(user_message: str, max_iterations: int = 5):
    print(f'\n{"="*50}')
    print(f'사용자: {user_message}')
    print('='*50)

    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': user_message},
    ]

    for i in range(max_iterations):
        response = client.chat.completions.create(
            model='gpt-5.4-mini', 
            messages=messages,
            response_format={'type': 'json_object'},
        )
        
        raw_content = response.choices[0].message.content
        parsed = parse_llm_response(raw_content)

        thought = parsed.get('thought', '')
        if thought:
            print(f'\n[Thought] {thought}')

        # 최종 답변인 경우
        if 'answer' in parsed:
            print(f'\n[Answer] {parsed["answer"]}')
            return parsed['answer']

        # Tool 호출인 경우
        action = parsed.get('action')
        action_input = parsed.get('action_input', {})

        if action in TOOLS:
            print(f'[Action] {action}({action_input})')
            
            # Tool 실행
            tool_func = TOOLS[action]['func']
            try:
                result = tool_func(**action_input)
            except Exception as e:
                result = f"Error executing tool: {str(e)}"
            
            print(f'[Observation] {result}')

            # 대화 기록 업데이트
            messages.append({'role': 'assistant', 'content': raw_content})
            messages.append({
                'role': 'user', 
                'content': f"Observation: {result}\n\n위 결과를 바탕으로 다음 단계(추가 Tool 호출 또는 최종 답변)를 진행하세요."
            })
        else:
            print(f'[Error] 알 수 없는 Tool: {action}')
            break

    print('\n[경고] 최대 반복 횟수에 도달했습니다.')

# 실행
# run_react_json_agent('서울 날씨 어때?')

# 복합질문
run_react_json_agent('서울과 도쿄 기온 차이를 계산해줘')