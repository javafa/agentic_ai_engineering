from graph import ask
from state import MEMORY
from config import MEMORY_PATH

GOLD = [
    {"must": "6000", "q": "전체 운행 건수는?",
        "q2": "데이터에 트립이 총 몇 건 있어?"}, 
    {"must": "credit", "q": "결제수단(payment)별 평균 팁 비율을 알려줘", 
        "q2": "카드 결제와 현금 결제 중 팁 비율이 높은 쪽은?"}, 
    {"must": "0.9", "q": "거리와 요금의 상관계수는?", 
        "q2": "trip_distance와 fare_amount는 얼마나 연관돼 있어?"}, 
    {"must": "Queens", "q": "지역(pickup_borough)별 평균 요금은?", 
        "q2": "승차 지역별로 요금 평균을 내줘"}, ]

def reset_memory() -> None:
    """외부 메모리(계층 1)를 비운다 — cold 조건을 진짜 cold로 만든다."""
    open(MEMORY_PATH, "w", encoding="utf-8").close()   # 파일 비우기
    MEMORY.items.clear()                               # 로드된 사본도 비우기

def classify_failure(state) -> str:
    if not state.get("error"):
        return "none"
    e = state["error"].lower()
    if "binder" in e or "keyerror" in e or "not found" in e:
        return "wrong_column"          # 컬럼명 착오 (가장 흔함)
    if "syntax" in e:    return "syntax"
    if "timeout" in e:   return "timeout"
    return "other"

def run_eval(tag: str, key: str = "q", repeat: int = 1):
    rows = []
    for r in range(repeat):
        for i, c in enumerate(GOLD):
            st = ask(c[key], thread_id=f"{tag}-{r}-{i}")
            hit = c["must"].lower() in (st.get("answer", "") 
                                        + st.get("stdout", "")).lower()
            rows.append({"q": c[key], "correct": hit,
                        "code_attempts": st.get("code_attempts", 0),
                        "first_try": st.get("code_attempts", 0) == 1 and hit,
                        "failure": classify_failure(st)})
    acc = sum(r["correct"] for r in rows) / len(rows)
    first = sum(r["first_try"] for r in rows) / len(rows)
    avg = sum(r["code_attempts"] for r in rows) / len(rows)
    print(f"[{tag}] 정확도 {acc:.0%}, " + 
          f"첫시도성공 {first:.0%},  평균 생성 {avg:.1f}회")
    return rows

if __name__ == "__main__":
    reset_memory()
    cold = run_eval("cold", "q",  repeat=1)
    warm = run_eval("warm", "q2", repeat=1)
