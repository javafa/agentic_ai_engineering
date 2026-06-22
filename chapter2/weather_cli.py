# 터미널에서 바로 실행하는 CLI 도구
import os, sys, json, requests
from dotenv import load_dotenv

load_dotenv()

def get_weather(city: str) -> str:
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
    print(get_weather(sys.argv[1]))    # 예: python weather_cli.py Seoul
