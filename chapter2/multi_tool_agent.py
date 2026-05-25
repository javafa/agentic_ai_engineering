import os, json, requests
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()
client = Anthropic()

# 1. 날씨 (앞에서 만든 것과 동일)
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

# 2. 계산기
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

# 3. 메모 저장
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


# Tool 목록
tools = [
    {
        'name': 'get_weather',
        'description': '도시의 현재 날씨를 조회합니다.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'city': {'type': 'string', 'description': '영문 도시 이름'}
            },
            'required': ['city'],
        },
    },
    {
        'name': 'calculate',
        'description': '수학 계산식을 계산합니다. 사칙연산, 거듭제곱 등을 지원합니다.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'expression': {'type': 'string', 'description': '계산할 수식 (예: 2+3*4)'}
            },
            'required': ['expression'],
        },
    },
    {
        'name': 'save_memo',
        'description': '사용자가 기억해달라고 하는 내용을 메모로 저장합니다.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'content': {'type': 'string', 'description': '저장할 메모 내용'}
            },
            'required': ['content'],
        },
    },
]

# Tool 이름 → 실제 함수 매핑
tool_map = {
    'get_weather': get_weather,
    'calculate': calculate,
    'save_memo': save_memo,
}

def run_agent(user_message):
    print(f'\n사용자: {user_message}')

    system_prompt = '당신은 날씨 조회, 계산, 메모 저장을 할 수 있는 도우미입니다.'
    messages = [
        {'role': 'user', 'content': user_message},
    ]

    response = client.messages.create(
        model='claude-sonnet-4-5',
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
        tools=tools,
    )

    # Tool 호출이 있으면 전부 실행
    while response.stop_reason == 'tool_use':
        messages.append({'role': 'assistant', 'content': response.content})

        tool_results = []
        # 1. 응답의 content 블록을 돌면서
        for block in response.content:
            if block.type != 'tool_use':
                continue
            # 2. tool_map에 있는 실제 함수를 가져온다
            func = tool_map[block.name]
            args = block.input
            print(f'  Tool: {block.name}({args})')

            # 3. 매핑된 함수를 실행하고 결과값을 얻는다.
            result = func(**args)

            tool_results.append({
                'type': 'tool_result',
                'tool_use_id': block.id,
                'content': result,   # 4. 결과값을 모은다.
            })

        # 5. tool_result들을 user 메시지로 추가한다
        messages.append({'role': 'user', 'content': tool_results})

        # 6. 모든 메시지를 LLM에 보내서 응답을 받는다.
        response = client.messages.create(
            model='claude-sonnet-4-5',
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

    # 최종 텍스트 응답을 추출한다
    final_text = ''.join(b.text for b in response.content if b.type == 'text')
    print(f'에이전트: {final_text}')
    return final_text


# 날씨 질문
# run_agent('부산 날씨 어때?')

# 계산 질문
# run_agent('15% 팁 포함해서 45000원이면 총 얼마야?')

# 메모 저장
# run_agent('내일 오후 3시에 치과 예약이야. 메모해줘')

# 복합 질문: Tool 두 개를 연속으로 사용
run_agent('도쿄 날씨 알려주고, 기억해둬')
