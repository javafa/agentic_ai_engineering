import time, urllib.parse
from config import NEW_RSS
from datetime import datetime, timezone
import feedparser
# from common import with_retry


def _is_recent(entry, hours: int = 24) -> bool:
    """발행 시각이 최근 hours 시간 이내인지 확인 (간밤 뉴스만 추리기)."""
    pp = entry.get("published_parsed")
    if not pp:
        return True  # 시각 정보가 없으면 일단 포함
    published = datetime.fromtimestamp(time.mktime(pp), tz=timezone.utc)
    return (datetime.now(timezone.utc) - published).total_seconds() <= hours * 3600
  
# @with_retry(tries=2, delay=2.0) # 필요시 적용
def fetch_news(keyword: str, max_items: int = 3) -> list:
    url = NEW_RSS.format(q=urllib.parse.quote(keyword))
    feed = feedparser.parse(url)
    # bozo=1 이면서 항목도 없으면 파싱 실패로 간주
    if getattr(feed, "bozo", 0) and not feed.entries:
        raise ValueError(f"'{keyword}' RSS 파싱 실패")
    items = []
    for e in feed.entries:
        if not _is_recent(e):
            continue
        items.append({
            "keyword": keyword,
            # 구글 뉴스 제목은 '기사 제목 - 언론사' 형태로 옵니다.
            "title": e.get("title", "").strip(),
            "source": (e.get("source") or {}).get("title", ""),
            "link": e.get("link", ""),
            "published": e.get("published", ""),
        })
        if len(items) >= max_items:
            break
    return items
