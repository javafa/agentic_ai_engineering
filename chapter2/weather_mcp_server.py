# 날씨 Tool을 MCP Server로 감싸기
import os, json, requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
mcp = FastMCP('weather')           # MCP Server 생성

@mcp.tool()                        # 함수 위에 데코레이터만 붙이면 Tool로 등록된다
def get_weather(city: str) -> str:
    """도시의 현재 날씨를 조회합니다."""
    api_key = os.getenv('WEATHER_API_KEY')
    url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'q': city, 'appid': api_key, 'units': 'metric', 'lang': 'kr'}
    data = requests.get(url, params=params).json()
    return json.dumps({
        'city': city,
        'temp': data['main']['temp'],
        'description': data['weather'][0]['description'],
    }, ensure_ascii=False)

if __name__ == '__main__':
    mcp.run(transport='stdio')     # 표준 입출력(stdio)으로 Server 실행
