from langgraph.graph import END
from langgraph.types import interrupt, Command
from config import SCHEMA_HINT, EXEC_TIMEOUT, MAX_RETRIES, MAX_REVIEW
from state import llm, KERNEL, MEMORY, AnalystState
from safety import find_risky
from pydantic import BaseModel, Field
from typing import Literal
from config import ANALYSIS_CONSTITUTION

# [생성] 코드 생성 노드 — 세 가지 모드로 자기수정을 구현한다.
#   (a) 최초: 질문 + 과거 성공 사례(few-shot)  > 계층 1(외부 메모리)
#   (b) 에러 수정: 직전 코드 + 트레이스백        > 계층 2(코드, 실행)
#   (c) 검토 반영: 리뷰 피드백                   > 계층 1, 4(자기검토, 원칙)

SYSTEM = """당신은 시니어 데이터 분석가입니다. DuckDB 연결 'con'과 동일 데이터의 pandas 'df'가 이미 메모리에 있습니다. 집계는 가급적 con.sql(\"...\").df() 로, 가공, 시각화는 pandas/matplotlib로 하세요.
규칙:
1. con, df는 이미 존재하므로 다시 만들지 마세요.
2. 답이 되는 값은 반드시 print()로 출력하세요.
3. 차트가 필요하면 matplotlib로 그리세요(plt.show(), savefig 없이도 자동 표시됨).
4. 코드 외의 설명, 마크다운 코드펜스는 쓰지 마세요.
5. 파일 쓰기, 외부 네트워크, 시스템 명령은 사용자가 명시적으로 요청할 때만 쓰세요.
{schema}"""

FEWSHOT_TMPL = "\n\n[참고: 과거 비슷한 질문의 성공 코드]\n질문: {q}\n코드:\n{code}"
RETRY_TMPL = """직전 코드가 에러로 실패했습니다. 에러를 보고 고친 코드를 다시 쓰세요.
[직전 코드]\n{code}\n\n[에러]\n{error}\n{traceback}"""
REVISE_TMPL = """직전 분석이 검토에서 보완 요청을 받았습니다. 아래 피드백을 반영해 코드를 다시 쓰세요.
[직전 코드]\n{code}\n\n[검토 피드백]\n{feedback}"""

def _extract_code(content) -> str:
    t = content if isinstance(content, str) else "".join(
        b.get("text", "") for b in content if isinstance(b, dict))
    t = t.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("python"):
            t = t[len("python"):]
    return t.strip()

def codegen(state: AnalystState) -> dict:
    system = SYSTEM.format(schema=SCHEMA_HINT)
    if state.get("error"):                      # (b) 에러 수정
        user = RETRY_TMPL.format(code=state["code"], error=state["error"],
                                 traceback=state["traceback"][:1500])
    elif state.get("review_feedback"):          # (c) 검토 반영
        user = REVISE_TMPL.format(code=state["code"], feedback=state["review_feedback"])
    else:                                       # (a) 최초 + 과거 사례 few-shot
        user = state["question"]
        for ex in state.get("few_shots", []):
            system += FEWSHOT_TMPL.format(q=ex["question"], code=ex["code"])
    res = llm.invoke([{"role": "system", "content": system},
                      {"role": "user", "content": user}])
    code = _extract_code(res.content)
    return {"code": code, "risky": find_risky(code),
            "code_attempts": state.get("code_attempts", 0) + 1,
            "review_feedback": ""}              # 피드백은 1회 소비 후 비운다

# [실행] 코드 실행 노드 - 실행중인 커널에서 실행하고 결과, 에러, 차트를 수집한다. (계층 2)
def execute(state: AnalystState) -> dict:
    out = KERNEL.run(state["code"], timeout=EXEC_TIMEOUT)
    paths = KERNEL.save_images(out["images"], prefix=f"chart_{state['code_attempts']}") \
        if out["images"] else []
    entry = {"phase": "execute", "attempt": state["code_attempts"],
             "code": state["code"], "error": out["error"]}
    return {"stdout": out["stdout"], "result": out["result"], "images": paths,
            "error": out["error"], "traceback": out["traceback"], "history": [entry]}
 
# [포기] 자기수정 한도까지 실패하면 정직하게 보고하고 끝낸다.
def give_up(state: AnalystState) -> dict:
    return {"answer": f"{MAX_RETRIES}번 시도했지만 코드를 성공시키지 못했습니다. "
                      f"마지막 에러: {state['error']}"} 

# 생성 직후: 위험하면 승인 게이트(계층 4 하드)로, 아니면 실행으로
def route_after_codegen(state: AnalystState) -> str:
    return "human_gate" if state["risky"] else "execute"
 
# 실행 직후: 에러면 자기수정 루프(한도 내), 한도 초과면 포기, 성공이면 해석으로
def route_after_execute(state: AnalystState) -> str:
    if not state["error"]:
        return "interpret"
    return "codegen" if state["code_attempts"] < MAX_RETRIES else "give_up"

# [해석] 실행 결과를 사용자용 자연어 답변으로 정리한다.
ANSWER_SYS = """당신은 데이터 분석가입니다. 아래 질문과 코드 출력만 근거로 한국어로 간결히 답하세요.
출력에 없는 값은 지어내지 말고, 차트가 있으면 무엇을 보여주는지 한 줄로 설명하세요."""

def interpret(state: AnalystState) -> dict:
    body = f"[질문]\n{state['question']}\n\n[출력]\n{state['stdout']}\n{state['result']}"
    if state.get("images"):
        body += f"\n\n[생성된 차트] {', '.join(state['images'])}"
    res = llm.invoke([{"role": "system", "content": ANSWER_SYS},
                      {"role": "user", "content": body}])
    text = res.content if isinstance(res.content, str) else "".join(
        b.get("text", "") for b in res.content if isinstance(b, dict))
    return {"answer": text.strip()}

# [기억 검색] 외부 메모리에서 비슷한 과거 성공 사례를 가져와 few-shot으로 쓴다. (계층 1)
def retrieve(state: AnalystState) -> dict:
    return {"few_shots": MEMORY.retrieve(state["question"], k=2)}

# [기억 저장] 검토를 통과한 성공 사례를 외부 메모리에 누적한다.
# 이 (질문, 코드) 누적분은 훗날 모델을 직접 학습시키는(계층 3) 데이터셋이 되기도 한다.
def remember(state: AnalystState) -> dict:
    if not state.get("error"):
        MEMORY.remember(state["question"], state["code"])
    return {}

# [승인] 사람 승인 게이트 — 위험한 코드는 실행 전에 사람에게 확인받는다. (휴먼인더루프)
def human_gate(state: AnalystState):
    decision = interrupt({            # 그래프를 멈추고 사람의 입력을 기다린다
        "reason": "위험할 수 있는 작업이 감지되었습니다.",
        "issues": state["risky"],
        "code": state["code"],
    })
    if str(decision).lower() in ("approve", "y", "yes"):
        return Command(goto="execute")
    return Command(goto=END, update={                 # 거부 > 실행하지 않고 종료
        "answer": "사용자가 실행을 거부하여 작업을 중단했습니다. 위험 요소: "
                  + ", ".join(state["risky"]),
    })

# [검토] 원칙적 자기정렬(계층 4) + 자가 검토(Self-Refine, 계층 1)를 한 노드에서 수행한다.
class Review(BaseModel):
    verdict: Literal["ok", "revise"] = Field(
        description="원칙 위반이나 명백한 분석 오류가 있으면 revise, 충분하면 ok")
    reason: str = Field(description="판단 근거(어떤 원칙/품질 문제인지)")
    feedback: str = Field(description="revise일 때 코드 작성자에게 줄 구체적 보완 지시")

REVIEW_SYS = """당신은 분석 결과를 검토하는 리뷰어입니다. 아래 '분석 원칙'을 기준으로
질문, 코드, 출력, 답변을 점검하세요. 원칙을 위반하거나(예: 데이터에 없는 수치, 작은 표본을
일반화, 상관을 인과로 단정) 질문에 제대로 답하지 못했으면 verdict='revise'와 구체적 feedback을,
충분하면 verdict='ok'를 주세요.

[분석 원칙]
{constitution}"""

def review(state: AnalystState) -> dict:
    rounds = state.get("review_rounds", 0)
    if rounds >= MAX_REVIEW:                      # 검토 한도 > 더 고치지 않고 통과
        return {"verdict": "ok", "review_rounds": rounds}
    rubric = "\n".join(f"- {c}" for c in ANALYSIS_CONSTITUTION)
    reviewer = llm.with_structured_output(Review)
    r = reviewer.invoke([
        {"role": "system", "content": REVIEW_SYS.format(constitution=rubric)},
        {"role": "user", "content": f"[질문]\n{state['question']}\n\n[코드]\n{state['code']}"
                                    f"\n\n[출력]\n{state['stdout']}{state['result']}"
                                    f"\n\n[답변]\n{state['answer']}"},
    ])
    entry = {"phase": "review", "verdict": r.verdict, "reason": r.reason}
    return {"verdict": r.verdict, "review_feedback": r.feedback if r.verdict == "revise" else "",
            "review_rounds": rounds + 1, "history": [entry]}

# 검토 직후: 보완 필요하면 코드 생성으로 되돌리고(계층 1, 4), 충분하면 기억 단계로
def route_after_review(state: AnalystState) -> str:
    return "codegen" if state["verdict"] == "revise" else "remember"
