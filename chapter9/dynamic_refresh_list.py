import FinanceDataReader as fdr
from config import WATCHLIST
 
def expand_watchlist(top_n: int = 3) -> list:
    """StockListing 스냅샷에서 등락률 상위 종목을 골라 기존 목록에 더한다.
    컬럼명은 버전에 따라 다를 수 있어 방어적으로 탐색한다."""

    snap = fdr.StockListing("KOSPI")

    # 등락률 컬럼 후보 (FDR 버전에 따라 다름)
    rate_col = next((c for c in ("ChagesRatio", "Changes", "ChangeRatio")
                     if c in snap.columns), None)
    base = list(WATCHLIST)

    if rate_col is None:
        return base      # 못 찾으면 기존 목록 그대로

    movers = snap.sort_values(rate_col, ascending=False).head(top_n)
    existing = {w["code"] for w in base}

    for _, row in movers.iterrows():
        code = str(row.get("Code", "")).zfill(6)
        if code and code not in existing:
            base.append({"code": code, "name": row.get("Name", code)})
    return base
