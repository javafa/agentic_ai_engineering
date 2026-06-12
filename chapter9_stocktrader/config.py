import os
from dotenv import load_dotenv
 
# 실행 파일기준의 .env 파일 경로
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, '.env')
load_dotenv(override=True, dotenv_path=ENV_PATH)
 
# 시장 지표: 표시명 > FinanceDataReader 심볼
INDEX_SYMBOLS = {
    "KOSPI":   "KS11",     # 코스피 지수
    "KOSDAQ":  "KQ11",     # 코스닥 지수
    "S&P500":  "US500",    # S&P 500
    "나스닥":  "IXIC",     # 나스닥 종합
    "다우":    "DJI",      # 다우존스 산업평균
    "VIX":     "VIX",      # 변동성 지수(공포지수)
    "USD/KRW": "USD/KRW",  # 원/달러 환율
}
 
# 관심 종목 — 증권사에서는 RA가 관리하는 커버리지 유니버스를 넣는다
# code는 국내 6자리 코드 또는 해외 티커 모두 가능
WATCHLIST = [
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"},
    {"code": "035720", "name": "카카오"},
    {"code": "NVDA",   "name": "엔비디아"},
    {"code": "AAPL",   "name": "애플"},
]
 
# 뉴스 검색 키워드 (구글 뉴스에서 한국어로 검색)
NEWS_KEYWORDS = ["코스피", "반도체", "원달러 환율", "엔비디아"]
 
# 채널 — 전송에 필요한 비밀값
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
KAKAO_REFRESH_TOKEN = os.getenv("KAKAO_REFRESH_TOKEN", "")

# 한국어/한국 지역 설정의 구글 뉴스 검색 RSS
NEW_RSS = "https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"