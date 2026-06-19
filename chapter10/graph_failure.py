import nodes
import graph

def inject_kernel_failure(fail_on=(1,), error="ValueError: injected test error"):
    """nodes.KERNEL.run을 감싸, 지정한 '호출 순번'에서만 가짜 에러를 반환한다.
    주의: import graph(=부트스트랩) 이후에 호출해야 데이터 로딩을 깨뜨리지 않는다."""
    orig = nodes.KERNEL.run            # 원본 bound method 보관
    n = {"i": 0}
    def patched(code, timeout=30):
        n["i"] += 1
        if n["i"] in fail_on:
            print(f"  [주입] KERNEL.run 호출 #{n['i']} -> 강제 에러 반환 ({error})")
            return {"stdout": "", "result": "", "images": [],
                    "error": error,
                    "traceback": f"Traceback (most recent call last):\n  ...\n{error}"}
        return orig(code, timeout=timeout)   # 그 외엔 진짜 실행
    nodes.KERNEL.run = patched
    return lambda: setattr(nodes.KERNEL, "run", orig)   # 복구 함수

if __name__ == "__main__":
    print("=== 실행에러 자기수정 테스트 (첫 execute 강제 실패) ===")
    restore = inject_kernel_failure(fail_on=(1,))   # give_up까지 보려면 (1, 2, 3)
    try:
        st = graph.ask("color(yellow/green)별 평균 팁(tip)을 막대그래프로 보여줘",
                       thread_id="t1")
    finally:
        restore()                                   # 항상 원복

    # ---- 결과 리포트 (이게 없으면 '아무 일도 안 일어난 것'처럼 보인다) ----
    execs = [(h["attempt"], bool(h["error"]))
             for h in st.get("history", []) if h.get("phase") == "execute"]
    print("\n--- 결과 ---")
    print("execute 이력 (attempt, 에러여부):", execs)
    print("code_attempts:", st.get("code_attempts"),
          "| review_rounds:", st.get("review_rounds"),
          "| 최종 error:", st.get("error"))
    print("저장된 차트:", st.get("images"))
    if st.get("code_attempts", 0) >= 2 and st.get("error") is None:
        print(">> 첫 실행 실패 후 스스로 코드를 재생성해 복구 성공 (자기수정 OK)")
    elif "시도했지만" in (st.get("answer") or ""):
        print(">> 한도(MAX_RETRIES) 초과로 give_up (정직한 포기)")
    print("\n[답변]\n", st.get("answer"))
