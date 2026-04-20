import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

"""도시 이름을 받아서 현재 날씨를 반환하는 함수"""
def get_weather(city: str) -> str:

    # 1. 날씨 api 설정하기
    api_key = os.getenv('WEATHER_API_KEY')
    url = f'http://api.openweathermap.org/data/2.5/weather'
    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric',    # 섭씨
        'lang': 'kr'          # 한국어 설명
    }

    # 2.requests 로 날씨 정보 받기
    response = requests.get(url, params=params)
    data = response.json()

     #  3. 받은 정보 분석
    if response.status_code != 200:
        return f'날씨 조회 실패: {data.get("message", "알 수 없는 오류")}'

    # 4. 결과 값 반환
    return json.dumps({
        'city': city,
        'temp': data['main']['temp'],
        'description': data['weather'][0]['description'],
        'humidity': data['main']['humidity'],
    }, ensure_ascii=False)

tools = [
    {
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': '도시의 현재 날씨를 조회합니다.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'city': {
                        'type': 'string',
                        'description': '날씨를 조회할 도시 이름 (영문)',
                    }
                },
                'required': ['city'],
            },
        },
    }
]

"""에이전트를 실행하는 함수"""
def run_agent(user_message):
    print(f'사용자: {user_message}')
    
    # LLM 에 전달하는 기본 메시지 세트
    messages = [
        {'role': 'system', 'content': '당신은 날씨 정보를 알려주는 도우미입니다.'},
        {'role': 'user', 'content': user_message},
    ]

    # 1단계: LLM에게 질문 + 도구 목록 전송
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message

    # 2단계: 도구 호출이 있는지 확인
    if message.tool_calls:
        # 도구 호출 요청을 메시지에 추가
        messages.append(message)

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f'도구 호출: {name}({args})')

            # 3단계: 실제 함수를 실행
            result = get_weather(**args)
            print(f'도구 결과: {result}')

            # 4단계: 함수 실행 결과를 LLM에게 전송
            messages.append({
                'role': 'tool',
                'tool_call_id': tool_call.id,
                'content': result,
            })

        # 5단계: LLM이 최종 답변 생성
        final = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
        )
        answer = final.choices[0].message.content
    else:
        # 도구 호출 없이 바로 답변한 경우
        answer = message.content

    print(f'에이전트: {answer}')
    return answer

if __name__ == '__main__':
    run_agent('도쿄랑 뉴욕 날씨 비교해줘')