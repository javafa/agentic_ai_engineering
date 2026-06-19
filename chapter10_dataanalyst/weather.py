# 가입 불필요, CC BY 4.0. '비 오는 날 택시 수요가 느는가?' 같은 질문에 사용한다.
import requests
import pandas as pd

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_weather(start: str, end: str,
                  lat: float = 40.71, lon: float = -74.01) -> pd.DataFrame:
    """기간별 일 단위 최고기온, 강수량을 DataFrame으로 돌려준다(기본 위치: 뉴욕)."""
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start, "end_date": end,
        "daily": "temperature_2m_max,precipitation_sum",
        "timezone": "America/New_York",
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=15)
    r.raise_for_status()
    daily = r.json()["daily"]
    wx = pd.DataFrame(daily)
    wx["date"] = pd.to_datetime(wx["time"]).dt.date
    return wx[["date", "temperature_2m_max", "precipitation_sum"]]

# 에이전트가 날씨를 쓰는 방식: 부트스트랩이나 도구로 wx를 커널에 올려 두면,
# 모델이 trips와 날짜로 조인해 'precipitation_sum 과 일별 운행건수의 상관'을 구할 수 있다.
# 예) con.register("wx", fetch_weather("2026-04-01", "2026-04-31"))
