import time
from graph import ask
from state import MEMORY
from config import MAX_RETRIES

GOLD = [
    {"q": "전체 운행 건수는?",                         "must": "6000"},
    {"q": "결제수단(payment)별 평균 팁 비율을 알려줘",  "must": "credit"},
    {"q": "거리와 요금의 상관계수는?",                 "must": "0.9"},
    {"q": "지역(pickup_borough)별 평균 요금은?",        "must": "Queens"},
]

def classify_failure(state) -> str:
    if not state.get("error"):
        return "none"
    e = state["error"].lower()
    if "binder" in e or "keyerror" in e or "not found" in e:
        return "wrong_column"          # 컬럼명 착오 (가장 흔함)
    if "syntax" in e:    return "syntax"
    if "timeout" in e:   return "timeout"
    return "other"

def run_eval(tag: str):
    rows = []
    for i, c in enumerate(GOLD):
        t0 = time.time()
        st = ask(c["q"], thread_id=f"{tag}-{i}")
        hit = c["must"].lower() in (st.get("answer", "") + st.get("stdout", "")).lower()
        rows.append({"q": c["q"], "correct": hit,
                     "code_attempts": st.get("code_attempts", 0),
                     "first_try": st.get("code_attempts", 0) == 1 and hit,
                     "failure": classify_failure(st)})
    acc = sum(r["correct"] for r in rows) / len(rows)
    first = sum(r["first_try"] for r in rows) / len(rows)
    avg = sum(r["code_attempts"] for r in rows) / len(rows)
    print(f"[{tag}] 정확도 {acc:.0%},  첫시도성공 {first:.0%},  평균 생성 {avg:.1f}회")
    return rows

if __name__ == "__main__":
    run_eval("cold")     # 메모리가 빈 상태
    run_eval("warm")     # 같은 질문을 다시 — 외부 메모리가 채워져 첫 시도 성공률↑ (계층 1)
