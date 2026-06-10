
from datetime import datetime, timedelta
import FinanceDataReader as fdr
 
# @with_retry(tries=3) 필요할수도
def _read_closes(symbol: str, lookback_days: int = 12):
    """심볼의 최근 종가 시리즈를 반환. 휴장일/주말이 섞여 있어도
    실제 거래가 있던 날의 종가만 dropna로 추출합니다."""
    start = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    df = fdr.DataReader(symbol, start)
    if df is None or df.empty or "Close" not in df.columns:
        raise ValueError(f"{symbol}: 응답에 종가(Close)가 없음")
    closes = df["Close"].dropna()
    if len(closes) < 2:
        raise ValueError(f"{symbol}: 비교할 종가가 부족({len(closes)}건)")
    return closes
 
def fetch_index(symbol: str) -> dict:
    """지수·환율의 최근 종가와 전일 대비 등락을 계산합니다."""
    closes = _read_closes(symbol)
    # 라이브러리가 주는 Change를 쓰지 않고, 
		# 오늘 종가(last)와 어제 종가(prev)를 직접 빼서 등락금액(change)을 계산함
    last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
    change = last - prev
    return {
        "last": last,
        "change": change,
        # 등락률(pct)도 직접 공식으로 계산함
        "pct": (change / prev * 100) if prev else 0.0,
        "asof": closes.index[-1].strftime("%Y-%m-%d"),
    }

def fetch_stock(code: str) -> dict:
    """개별 종목의 종가, 전일 대비 등락, 5일 이동평균을 계산합니다.
    5일선 대비 위치(vs_ma5)는 단기 추세 판단의 간단한 보조 지표입니다."""
    closes = _read_closes(code, lookback_days=18)
    last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
    change = last - prev
    ma5 = float(closes.tail(5).mean())
    return {
        "last": last,
        "change": change,
        "pct": (change / prev * 100) if prev else 0.0,
        "ma5": ma5,
        "vs_ma5": (last / ma5 - 1) * 100 if ma5 else 0.0,
        "asof": closes.index[-1].strftime("%Y-%m-%d"),
    }
