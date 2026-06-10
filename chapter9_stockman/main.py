from typing import Annotated
from typing_extensions import TypedDict
from operator import add
from datetime import datetime
from langgraph.graph import StateGraph, START, END
from langchain_anthropic import ChatAnthropic
 
from config import (INDEX_SYMBOLS, WATCHLIST, NEWS_KEYWORDS, KAKAO_CLIENT_SECRET,
                    SLACK_WEBHOOK_URL, KAKAO_REST_API_KEY, KAKAO_REFRESH_TOKEN)
from market import fetch_index, fetch_stock
from news import fetch_news
from formatter import serialize_for_llm, fmt, sign
from notify import send_slack, send_kakao
from common import log
 
llm = ChatAnthropic(model="claude-haiku-4-5")
 
# 5개 노드가 공유하는 상태
class BriefingState(TypedDict):
    target_date: str                  # 브리핑 기준일
    indicators: dict                  # 지표 수집 결과
    stocks: list                      # 관심 종목 점검 결과
    news: list                        # 뉴스 수집 결과
    briefing_md: str                  # LLM이 작성한 브리핑(마크다운)
    errors: Annotated[list, add]      # 각 노드의 경고를 누적 (덮어쓰기 X)
    delivery: dict                    # 전송 결과

# 1) 지표 수집 노드
def collect_indicators(state: BriefingState) -> dict:
    log.info("1) 지표 수집 시작")
    out, errors = {}, []
    for name, symbol in INDEX_SYMBOLS.items():
        try:
            out[name] = fetch_index(symbol)
            d = out[name]
            log.info("  %s: %s (%s%.2f%%)", name, fmt(d["last"]), sign(d["change"]), abs(d["pct"]))
        except Exception as e:
            out[name] = None                       # 실패는 None으로 남겨 둠(지어내지 않음)
            errors.append(f"지표 {name} 실패: {e}")
            log.warning("  %s 수집 실패: %s", name, e)
    return {"indicators": out, "errors": errors}
 
 
# 2) 관심 종목 점검 노드
def check_watchlist(state: BriefingState) -> dict:
    log.info("2) 관심 종목 점검 시작")
    rows, errors = [], []
    for item in WATCHLIST:
        try:
            d = fetch_stock(item["code"])
            d.update(item)                          # name, code 합치기
            rows.append(d)
            log.info("  %s: %s (%s%.2f%%)", item["name"], fmt(d["last"]),
                     sign(d["change"]), abs(d["pct"]))
        except Exception as e:
            rows.append({**item, "error": str(e)})  # 실패해도 행은 남김
            errors.append(f"종목 {item['name']} 실패: {e}")
            log.warning("  %s 수집 실패: %s", item["name"], e)
    return {"stocks": rows, "errors": errors}

# 3) 뉴스 수집 노드
def collect_news(state: BriefingState) -> dict:
    log.info("3) 뉴스 수집 시작")
    seen, news, errors = set(), [], []
    for kw in NEWS_KEYWORDS:
        try:
            for n in fetch_news(kw):
                if n["title"] in seen:              # 키워드 간 중복 제거
                    continue
                seen.add(n["title"])
                news.append(n)
        except Exception as e:
            errors.append(f"뉴스 '{kw}' 실패: {e}")
            log.warning("  뉴스 '%s' 수집 실패: %s", kw, e)
    log.info("  뉴스 %d건 수집", len(news))
    return {"news": news, "errors": errors}

# 4) 브리핑 작성 노드
SYSTEM = """당신은 증권사 리서치 데스크의 애널리스트입니다.
주어진 '데이터'만 근거로 출근 전에 읽을 아침 시장 브리핑을 작성합니다.
반드시 지킬 규칙:
1. 데이터에 없는 수치나 사실을 절대 지어내지 마세요(할루시네이션 금지).
2. '수집 실패' 항목은 추정하지 말고 '데이터 미수집'으로 명시하세요.
3. 사실과 해석을 구분하세요.
4. 바쁜 영업점 직원이 5분 안에 훑도록 간결한 한국어로 작성하세요."""
 
USER_TMPL = """오늘 날짜: {date}
 
아래 데이터만 사용해 브리핑을 작성하세요. 다음 마크다운 구조를 그대로 따르세요.
 
# {date} 모닝 마켓 브리핑
## 한 줄 요약
## 글로벌·국내 지표
## 관심 종목 점검
## 주요 뉴스
## 오늘의 체크포인트
 
[데이터]
{data}
"""
 
def write_briefing(state: BriefingState) -> dict:
    log.info("4) 브리핑 작성 시작")
    data = serialize_for_llm(state["indicators"], state["stocks"], state["news"])
    res = llm.invoke([
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER_TMPL.format(date=state["target_date"], data=data)},
    ])
    # content가 문자열/블록 리스트 어느 쪽이든 텍스트만 안전하게 추출
    text = res.content if isinstance(res.content, str) else "".join(
        b.get("text", "") for b in res.content if isinstance(b, dict)
    )
    return {"briefing_md": text.strip()}

# 5) 전송 노드
def _kakao_digest(briefing_md: str, date: str) -> str:
    """브리핑에서 '한 줄 요약' 섹션만 뽑아 카카오용 단문(≤200자)으로 만듭니다."""
    log.info("main._kakao_digest:")
    summary, capture = [], False
    for ln in briefing_md.splitlines():
        if ln.strip().startswith("## 한 줄 요약"):
            capture = True
            continue
        if capture:
            if ln.strip().startswith("##"):      # 다음 섹션 시작 → 종료
                break
            if ln.strip():
                summary.append(ln.strip())
    if summary:
        return f"[모닝브리핑] {date}\n{' '.join(summary)}"[:200]
    return f"[모닝브리핑] {date} 브리핑 도착 — 전체는 슬랙에서 확인하세요."[:200]
 
 
def send_briefing(state: BriefingState) -> dict:
    log.info("main.send_briefing: 전송 시작")
    body = state["briefing_md"]
    # 수집 단계에서 누적된 경고가 있으면 본문 끝에 투명하게 덧붙입니다.
    if state.get("errors"):
        body += "\n\n---\n_데이터 수집 경고_\n" + "\n".join(f"- {e}" for e in state["errors"])
 
    status = {}
    # 한 채널이 실패해도 다른 채널은 계속 시도합니다.
    # 슬랙에는 전체 브리핑을, 카카오톡에는 한 줄 요약(≤200자)을 보냅니다.
    try:
        send_slack(body, SLACK_WEBHOOK_URL)
        status["slack"] = "ok"
    except Exception as e:
        status["slack"] = f"fail: {e}"
        log.error("슬랙 전송 실패: %s", e)
 
    try:

        send_kakao(_kakao_digest(body, state["target_date"]),
                   KAKAO_REST_API_KEY, KAKAO_CLIENT_SECRET, KAKAO_REFRESH_TOKEN)
        status["kakao"] = "ok"
    except Exception as e:
        status["kakao"] = f"fail: {e}"
        log.error("카카오 전송 실패: %s", e)
 
    return {"delivery": status}

# 그래프 조립 — 5단계 순차(선형) 워크플로우
def build_graph():
    wf = StateGraph(BriefingState)
    wf.add_node("collect_indicators", collect_indicators)
    wf.add_node("check_watchlist", check_watchlist)
    wf.add_node("collect_news", collect_news)
    wf.add_node("write_briefing", write_briefing)
    wf.add_node("send_briefing", send_briefing)
 
    wf.add_edge(START, "collect_indicators")
    wf.add_edge("collect_indicators", "check_watchlist")
    wf.add_edge("check_watchlist", "collect_news")
    wf.add_edge("collect_news", "write_briefing")
    wf.add_edge("write_briefing", "send_briefing")
    wf.add_edge("send_briefing", END)
    return wf.compile()
 
 
def run(target_date: str | None = None) -> dict:
    graph = build_graph()
    today = target_date or datetime.now().strftime("%Y-%m-%d")
    return graph.invoke({
        "target_date": today,
        "indicators": {}, "stocks": [], "news": [],
        "briefing_md": "", "errors": [], "delivery": {},
    })
 
 
if __name__ == "__main__":
    result = run()
    print("\n===== 생성된 브리핑 =====\n")
    print(result["briefing_md"])
    print("\n전송 상태:", result["delivery"])
    if result["errors"]:
        print("\n경고:")
        for e in result["errors"]:
            print(" -", e)
