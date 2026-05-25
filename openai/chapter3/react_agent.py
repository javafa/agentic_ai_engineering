import os, json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

REACT_SYSTEM_PROMPT = """
당신은 Tool을 사용할 수 있는 AI 에이전트입니다.

반드시 다음 형식을 따릅니다:

현재 상황을 분석하고 다음에 할 일을 추론합니다.
그런 다음, 필요하면 Tool을 호출합니다.
Tool 결과를 받으면 다시 Thought로 돌아가서 분석합니다.

충분한 정보가 모이면, 최종 답변을 생성합니다.
최종 답변 시에는 Thought 없이 바로 사용자에게 답합니다.
"""

# 날씨 Tool
def get_weather(city: str) -> str:
    """도시의 현재 날씨를 조회합니다."""
    # 학습용으로 더미 데이터를 반환합니다
    weather_data = {
        'Seoul': {'temp': 18.5, 'description': '맑음', 'humidity': 45},
        'Tokyo': {'temp': 15.2, 'description': '가벼운 비', 'humidity': 78},
        'New York': {'temp': 22.1, 'description': '구름 많음', 'humidity': 55},
    }
    data = weather_data.get(city, {'temp': 0, 'description': '알 수 없음', 'humidity': 0})
    return json.dumps({'city': city, **data}, ensure_ascii=False)

# 계산기 Tool
def calculate(expression: str) -> str:
    """수학 계산식을 계산합니다."""
    try:
        result = eval(expression, {'__builtins__': {}})
        return json.dumps({'expression': expression, 'result': result})
    except Exception as e:
        return json.dumps({'error': str(e)})

# Tool 매핑
tool_map = {
    'get_weather': get_weather,
    'calculate': calculate,
}

# Tool 스키마 (OpenAI 형식)
tools = [
    {
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': '도시의 현재 기온, 날씨 상태, 습도를 조회합니다.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {'type': 'string',
                             'description': '영문 도시 이름 (예: Seoul, Tokyo)'}
                },
                'required': ['city'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'calculate',
            'description': '수학 계산식을 평가합니다. 사칙연산, 거듭제곱을 지원합니다.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'expression': {'type': 'string',
                                   'description': '계산할 수식 (예: 2+3*4)'}
                },
                'required': ['expression'],
            },
        },
    },
]

def run_react_agent(user_message, max_iterations=5):
    print(f'\n{"="*50}')
    print(f'사용자: {user_message}')
    print('='*50)

    messages = [
        {'role': 'system', 'content': REACT_SYSTEM_PROMPT},
        {'role': 'user', 'content': user_message},
    ]

    for i in range(max_iterations):
        response = client.chat.completions.create(
            model='gpt-5.4-mini',
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message

        # Thought 출력 (LLM이 생성한 텍스트)
        if message.content:
            print(f'\n[Thought] {message.content}')

        # Tool 호출이 없으면 최종 답변
        if not message.tool_calls:
            print(f'[Answer] {message.content}')
            return message.content
        
        # Action: Tool 호출 가져오기
        messages.append(message)
        for tc in message.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)
            print(f'[Action] {name}({args})')

            # Tool 실행
            result = tool_map[name](**args)
            print(f'[Observation] {result}')

            # 결과를 메시지에 추가
            messages.append({
                'role': 'tool', # role 에 tool을 사용해서 도구사용 결과값임을 알려줍니다
                'tool_call_id': tc.id,
                'content': result,
            })

    print('\n[경고] 최대 반복 횟수에 도달했습니다.')
    return '죄송합니다. 처리 중 문제가 발생했습니다.'

# 단일 질문
# run_react_agent('서울 날씨 어때?')

# 복합 질문: Tool 두 개 + 추론
# run_react_agent('서울과 도쿄 기온 차이를 계산해줘')

# 복합 질문:
run_react_agent('뉴욕 날씨를 섭씨에서 화씨로 변환해줘')