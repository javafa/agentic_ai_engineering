from pydantic import BaseModel, Field
from typing import Literal
from langchain_anthropic import ChatAnthropic
from config import MODEL
 
planner_llm = ChatAnthropic(model=MODEL)

# 로봇이 수행할 수 있는 행동의 종류를 명확히 제한
class PlanStep(BaseModel):
    action: Literal["navigate_to", "pick", "place", "look_around", "done"]
    target: str = Field(description="대상 객체/장소 이름. done·look_around이면 빈 문자열")
    reason: str = Field(description="이 행동을 고른 이유(한 줄)")

# 로봇의 행동 규칙과 예외 처리 가이드라인 정의
PLAN_SYS = """당신은 가정용 로봇의 계획 모듈입니다.
사용자 명령을 한 번에 하나의 행동으로 분해해 수행합니다(ReAct).
매 단계 '지금 보이는 것'과 '지금까지 한 일'을 보고 다음 행동 1개만 고르세요.

사용할 수 있는 행동:
- navigate_to(target): 객체나 장소(table, basket, shelf) 근처로 이동
- pick(target): 가까이 있는 객체를 집기 (집기 전 navigate_to로 다가가야 함)
- place(target): 들고 있는 물체를 장소에 놓기
- look_around(): 찾는 물체가 안 보이면 시점을 돌려 더 둘러보기
- done(): 명령을 모두 완수했으면 종료
 
규칙:
1. 보이지 않는 물체는 집을 수 없다. 안 보이면 look_around로 먼저 찾아라.
2. 집기 전에는 반드시 그 물체로 navigate_to 한다.
3. 직전 행동이 실패했다면 그 이유를 보고 다른 방법을 선택하라(같은 실패 반복 금지).
4. 명령이 모호하면(예: '치워줘') 보이는 물체를 합리적 장소(basket)로 옮기는 것으로 해석하라.
5. target 이름은 반드시 정해진 것만 쓴다: 장소는 table·basket·shelf 중 하나, 물체는 [보이는 물체]에 나온 이름 그대로. (desk·red figure 같은 임의 변형 금지)"""

# 모델이 상황을 완벽히 파악할 수 있도록 컨텍스트 주입
PLAN_USER = """[사용자 명령] {instruction}
[지금 보이는 장면] {scene}
[보이는 물체] {objects}
[들고 있는 것] {holding}
[지금까지 한 행동] {log}
[직전 행동 결과] {last}
 
다음 행동 1개를 고르세요."""
 
def plan_next(state) -> PlanStep:
    model = planner_llm.with_structured_output(PlanStep)
    # 현재 상태에서 인지된 물체 목록을 문자열로 파싱
    obs = state["observation"]
    objs = ", ".join(f"{o.name}({o.where})" for o in obs.objects) or "없음"
    # 템플릿에 데이터 매핑
    user = PLAN_USER.format(
        instruction=state["instruction"], scene=obs.scene, objects=objs,
        holding=state["holding"] or "없음",
        # 최근 6개의 행동 이력만 참조 (컨텍스트 관리)
        log="; ".join(state["action_log"][-6:]) or "없음",
        last=state["last_result"] or "없음")
    return model.invoke([{"role": "system", "content": PLAN_SYS},
                         {"role": "user", "content": user}])
