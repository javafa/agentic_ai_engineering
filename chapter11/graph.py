from typing import Annotated, Optional
from typing_extensions import TypedDict
from operator import add
from langgraph.graph import StateGraph, START, END
from config import MAX_STEPS, MAX_RECOVERY
from sim import RobotAPI
from perception import perceive, Observation
from planner import plan_next

# 하나의 시뮬레이터 인스턴스를 메모리에 계속 유지한다
ROBOT = RobotAPI(gui=False)
 
class RoomAgentState(TypedDict):
    instruction: str                      # 사용자 자연어 명령
    observation: Optional[Observation]    # 최신 인지 결과
    plan: Optional[dict]                  # 다음 행동(PlanStep)
    holding: Optional[str]                # 로봇이 들고 있는 물체 이름
    last_result: str                      # 직전 액션 실행 결과 메시지
    last_ok: bool                         # 직전 액션 성공 여부
    action_log: Annotated[list, add]      # 전체 행동 기록(누적)
    step_count: int                       # 행동 스텝 수(무한루프 방지)
    recovery_count: int                   # 행동 실패 후 복구(재계획) 시도 횟수
    status: str                           # in_progress | success | failed

# [인지] 로봇 시점에서 카메라를 찍어 VLM으로 사물을 식별한다
def perceive_node(state):
    _, img_b64 = ROBOT.capture()
    return {"observation": perceive(img_b64)}
 
# [계획] 컨텍스트를 종합하여 다음 하나의 행동을 결정한다
def plan_node(state):
    return {"plan": plan_next(state).model_dump()}
 
# [행동] 계획된 스킬을 로봇 하드웨어로 실행한다
def act_node(state):
    a, t = state["plan"]["action"], state["plan"]["target"]
    # 명령을 실제 로봇 API 함수로 매핑 및 실행
    if a == "navigate_to":   r = ROBOT.navigate_to(t)
    elif a == "pick":        r = ROBOT.pick(t)
    elif a == "place":       r = ROBOT.place(t)
    elif a == "look_around": r = ROBOT.look_around()
    else:                    r = {"ok": True, "reason": "완료 선언"}
    holding = ROBOT.held[2] if ROBOT.held else None
    line = f"{a}({t}) -> {'OK' if r['ok'] else 'FAIL'}: {r['reason']}"
    return {"last_result": line, "last_ok": r["ok"], "holding": holding,
            "action_log": [line], "step_count": state["step_count"] + 1}
 
# [복구] 실패횟수를 카운트하고 다시 인지단계로 돌려보낸다
# 실패 원인이 last_result에 기록되므로, 다음 계획 시 LLM이 스스로 우회 경로를 찾는다
def recover_node(state):
    return {"recovery_count": state["recovery_count"] + 1}

# [종료 및 포기 노드] 최종 상태를 기록하고 루프를 마친다
def finish_node(state):
    return {"status": "success"}
 
def give_up_node(state):
    return {"status": "failed",
            "last_result": state["last_result"] + " (한도 초과로 중단)"}

# 계획 직후: done이면 성공 종료, 스텝 한도를 넘으면 실패 종료, 그 외엔 실행
def route_after_plan(state):
    if state["plan"]["action"] == "done":
        return "finish"
    if state["step_count"] >= MAX_STEPS:      # 무한 루프 방지
        return "give_up"
    return "act"
 
# 행동 직후: 성공하면 다시 보고 다음 진행, 실패하면 복구 한도 확인
def route_after_act(state):
    if state["last_ok"]:
        return "perceive"
    return "recover" if state["recovery_count"] < MAX_RECOVERY else "give_up"
 
def build_graph():
    wf = StateGraph(RoomAgentState)
    wf.add_node("perceive", perceive_node)
    wf.add_node("plan", plan_node)
    wf.add_node("act", act_node)
    wf.add_node("recover", recover_node)
    wf.add_node("finish", finish_node)
    wf.add_node("give_up", give_up_node)

    wf.add_edge(START, "perceive")
    wf.add_edge("perceive", "plan")

    wf.add_conditional_edges("plan", route_after_plan,
                             {"act": "act", "finish": "finish", "give_up": "give_up"})
    wf.add_conditional_edges("act", route_after_act,
                             {"perceive": "perceive", "recover": "recover", "give_up": "give_up"})
    wf.add_edge("recover", "perceive")        # 복구 후 다시 보고 다시 계획
    wf.add_edge("finish", END)
    wf.add_edge("give_up", END)
    return wf.compile()
 
def run(instruction: str) -> dict:
    graph = build_graph()
    init = {"instruction": instruction, "observation": None, "plan": None,
            "holding": None, "last_result": "", "last_ok": True,
            "action_log": [], "step_count": 0, "recovery_count": 0,
            "status": "in_progress"}
    # 한 스텝마다 최소 3개의 노드를 통과하므로 무한 루프 차단 limit을 충분히 잡는다
    return graph.invoke(init, {"recursion_limit": 100})
 
if __name__ == "__main__":
    out = run("책상 위 곰인형을 바구니에 넣어줘")
    print("\n상태:", out["status"], "| 스텝:", out["step_count"],
          "| 복구:", out["recovery_count"])
    for line in out["action_log"]:
        print(" -", line)
