import os, json, requests
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# Tool 1: 날씨 (앞에서 만든 것과 동일)
def get_weather(city: str) -> str:
    """도시의 현재 날씨를 조회합니다."""
    api_key = os.getenv('WEATHER_API_KEY')
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'appid': api_key, 'units': 'metric', 'lang': 'kr'}
    resp = requests.get(url, params=params).json()
    return json.dumps({
        'city': city, 'temp': resp['main']['temp'],
        'description': resp['weather'][0]['description'],
    }, ensure_ascii=False)


# Tool 2: 계산기
def calculate(expression: str) -> str:
    """수학 계산식을 받아서 결과를 반환합니다."""
    try:
        # 주의: 프로덕션에서는 eval 대신 안전한 파서를 사용하세요
        result = eval(expression, {'__builtins__': {}})
        return json.dumps({'expression': expression, 'result': result})
    except Exception as e:
        return json.dumps({'error': str(e)})

# 메모 저장소
memo_store = []

# Tool 3: 메모 저장
def save_memo(content: str) -> str:
    """메모를 저장합니다."""
    memo = {
        'content': content,
        'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }
    memo_store.append(memo)
    return json.dumps({
        'status': '저장 완료',
        'total_memos': len(memo_store),
    }, ensure_ascii=False)


# Tool 4: 현재 시간
def get_current_time() -> str:
    """서버의 현재 날짜와 시간을 반환합니다."""
    now = datetime.now()
    return json.dumps({
        'current_time': now.strftime('%Y-%m-%d %H:%M:%S')
    }, ensure_ascii=False)


# Tool 목록
tools = [
    {
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': '도시의 현재 날씨를 조회합니다.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {'type': 'string', 'description': '영문 도시 이름'}
                },
                'required': ['city'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'calculate',
            'description': '수학 계산식을 계산합니다. 사칙연산, 거듭제곱 등을 지원합니다.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'expression': {'type': 'string', 'description': '계산할 수식 (예: 2+3*4)'}
                },
                'required': ['expression'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'save_memo',
            'description': '사용자가 기억해달라고 하는 내용을 메모로 저장합니다.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'content': {'type': 'string', 'description': '저장할 메모 내용'}
                },
                'required': ['content'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_current_time',
            'description': '현재 날짜와 시간을 조회합니다. 답변은 질문자의 언어에 맞도록 로케일을 적용합니다. 예) 한국어 : 2026년 3월 1일 오후 3시 15분 21초',
            'parameters': {
                'type': 'object',
                'properties': {}, # 매개변수가 필요 없음
            },
        },
    },
]


# 도구 이름 → 실제 함수 매핑
tool_map = {
    'get_weather': get_weather,
    'calculate': calculate,
    'save_memo': save_memo,
    'get_current_time': get_current_time, # 매핑 추가
}

def run_agent(user_message):
    print(f'\n사용자: {user_message}')

    messages = [
        {'role': 'system', 'content':
         '당신은 날씨 조회, 계산, 메모 저장, 현재 시간 안내를 할 수 있는 도우미입니다.'}, # 시스템 메시지 수정
        {'role': 'user', 'content': user_message},
    ]

    response = client.chat.completions.create(
        model='gpt-5.4-mini',
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message

    # 도구 호출이 있으면 전부 실행
    while message.tool_calls:
        messages.append(message)

        for tc in message.tool_calls:
            func = tool_map[tc.function.name]
            args = json.loads(tc.function.arguments)
            print(f'  도구: {tc.function.name}({args})')

            result = func(**args)

            messages.append({
                'role': 'tool',
                'tool_call_id': tc.id,
                'content': result,
            })

        response = client.chat.completions.create(
            model='gpt-5.4-mini',
            messages=messages,
            tools=tools,
        )
        message = response.choices[0].message

    print(f'에이전트: {message.content}')
    return message.content


run_agent('지금 몇시야?')
