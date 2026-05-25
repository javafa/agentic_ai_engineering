import json, os, requests
from dotenv import load_dotenv
from langchain_core.tools import tool

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

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

""" State Graph """

# 1. 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 2. LLM 노드
llm_with_tools = ChatOpenAI(model='gpt-5.4-mini').bind_tools(
    [get_weather, calculate]
)

def call_llm(state: State):
    response = llm_with_tools.invoke(state['messages'])
    return {'messages': [response]}

# 3. 그래프 구성
graph = StateGraph(State)
graph.add_node('llm', call_llm)
graph.add_node('tools', ToolNode([get_weather, calculate]))

graph.add_edge(START, 'llm')
graph.add_conditional_edges('llm', tools_condition)
graph.add_edge('tools', 'llm')

# 4. 컴파일 및 실행
agent = graph.compile()
result = agent.invoke({
    'messages': [{'role': 'user', 'content': '서울 날씨 알려줘'}]
})
