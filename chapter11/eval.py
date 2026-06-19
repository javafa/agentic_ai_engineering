import math
from graph import run, ROBOT
from config import LOCATIONS
 
# 데이터셋: (테스트 명령, 대상 객체, 목적지)
GOLD = [
    {"q": "곰인형을 바구니에 넣어줘",       "obj": "teddy bear",  "to": "basket"},
    {"q": "빨간 블록을 선반에 올려줘",       "obj": "red cube",    "to": "shelf"},
    {"q": "오리를 테이블에서 치워줘",        "obj": "rubber duck", "to": "basket"},
]
 
def near(a, b, tol=0.45):
    """두 지점 사이의 유클리드 거리가 오차 한계(tol) 이내인지 계산한다."""
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol
 
def run_eval():
    rows = []
    print("=== 에이전트 벤치마크 평가 시작 ===")

    for c in GOLD:
        ROBOT.reset()                         # 매 태스크마다 환경을 초기화
        out = run(c["q"])
        # 작업 완료 후 물체의 실제 물리 좌표 측정
        final_pos = ROBOT.position_of(c["obj"])
        # 에이전트의 완료 상태 선언과 실제 물리 좌표의 도달 여부를 교차 검증
        is_success = out["status"] == "success" and near(final_pos, LOCATIONS[c["to"]])
        rows.append({"q": c["q"],
                     "success": is_success,
                     "steps": out["step_count"], 
                     "recoveries": out["recovery_count"]})
        status_char = 'O' if is_success else 'X'
        print(f"[{status_char}] {c['q']}  (스텝 {out['step_count']}, 복구 {out['recovery_count']})")

    # 최종 통계 지표 산출
    success_rate = sum(r["success"] for r in rows) / len(rows)
    avg_steps = sum(r["steps"] for r in rows) / len(rows)
    avg_recoveries = sum(r["recoveries"] for r in rows) / len(rows)
    print(f"\n작업 성공률 {success_rate:.0%} · 평균 스텝 {avg_steps:.1f} · 평균 복구 {avg_recoveries:.1f}")
    return rows
 
if __name__ == "__main__":
    run_eval()
    ROBOT.hold_view()       # GUI일 때 마지막 결과 창을 열어둔다 (헤드리스면 무시)
