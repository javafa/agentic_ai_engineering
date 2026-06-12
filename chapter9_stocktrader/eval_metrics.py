import json, time
from datetime import datetime
from main import build_graph
 
def run_with_metrics() -> dict:
    graph = build_graph()
    today = datetime.now().strftime("%Y-%m-%d")
    t0 = time.time()
    result = graph.invoke({
        "target_date": today, "indicators": {}, "stocks": [],
        "news": [], "briefing_md": "", "errors": [], "delivery": {},
    })
    elapsed = time.time() - t0
 
    ind = result["indicators"]
    record = {
        "date": today,
        "elapsed_sec": round(elapsed, 1),
        # 지표 수집 성공률 = 핵심 데이터 완성도
        "indicator_completeness": round(
            sum(1 for v in ind.values() if v) / max(len(ind), 1), 2),
        "stock_fail": sum(1 for s in result["stocks"] if s.get("error")),
        "news_count": len(result["news"]),
        "briefing_len": len(result["briefing_md"]),
        "delivery": result["delivery"],
        "error_count": len(result["errors"]),
    }
    with open("runs.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
 
if __name__ == "__main__":
    print(run_with_metrics())
