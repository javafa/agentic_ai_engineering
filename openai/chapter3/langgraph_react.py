import json, os, requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent

load_dotenv()

@tool
def get_weather(city: str) -> str:
    """도시 이름을 받아 현재 기온과 날씨 설명을 반환합니다. 도시명이 영어가 아닐때는 영어로 변환해서 사용합니다."""
    api_key = os.getenv('WEATHER_API_KEY')
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'appid': api_key, 'units': 'metric', 'lang': 'kr'}
    
    resp = requests.get(url, params=params)
    data = resp.json()
    result = {
			'city': city,
			'temp': data['main']['temp'],
			'description': data['weather'][0]['description'],
    }
    return json.dumps(result, ensure_ascii=False)

@tool
def calculate(expr: str) -> str:
    """수학 수식을 계산합니다. 예: '18.5 - 15.2'"""
    return eval(expr, {"__builtins__": None}, {})


model = ChatOpenAI(model="gpt-5.4-mini", temperature=0)
tools = [get_weather, calculate]
agent = create_agent(model, tools=tools)

inputs = {"messages": [("user", "서울과 도쿄 기온 차이 알려줘")]}

for chunk in agent.stream(inputs, stream_mode="values"):
    chunk["messages"][-1].pretty_print()