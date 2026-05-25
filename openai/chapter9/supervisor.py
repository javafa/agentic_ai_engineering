from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from dotenv import load_dotenv
 
load_dotenv()
 
# 1) 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str       # 다음에 실행할 에이전트
    round_count: int      # 무한 루프 방지용
 
# 2) Tool 정의
@tool
def web_search(query: str) -> str:
    """웹에서 정보를 검색합니다."""
    # 더미 데이터
    results = {
        "AI 에이전트 트렌드": "2026년에는 Agentic RAG와 멀티 에이전트 시스템이 주류입니다.",
        "Python 3.14 변경점": "JIT 컴파일러 개선, 새로운 타입 힌트 문법 등이 포함.",
    }
    for key, val in results.items():
        if any(word in query for word in key.split()):
            return val
    return f"'{query}'에 대한 검색 결과입니다: 관련 정보를 찾았습니다."
 
@tool
def write_code(description: str, language: str = "python") -> str:
    """요구사항에 따라 코드를 작성합니다."""
    return f"{language}\n# {description}에 대한 코드\nprint('Hello from generated code')\n"

# 3) 모델 및 상수 초기화
llm = ChatOpenAI(model="gpt-5.4-mini")
MAX_ROUNDS = 8

# 4) 슈퍼바이저 노드
def supervisor(state: State) -> Command:
    """작업을 분석하고 적절한 에이전트에게 위임합니다."""
    count = state.get("round_count", 0) + 1
 
    # 핑퐁 루프 방지
    if count >= MAX_ROUNDS:
        return Command(goto=END, update={
            "messages": [{"role": "assistant",
                          "content": "최대 라운드에 도달했습니다. 결과를 정리합니다."}],
            "round_count": count
        })
 
    response = llm.invoke([
        {"role": "system", "content": """당신은 팀을 관리하는 슈퍼바이저입니다.
주어진 작업을 분석하여 적절한 팀원에게 위임하세요.
가용 팀원:
- researcher: 정보 검색, 조사, 분석 담당
- coder: 코드 작성, 프로그래밍 담당
- FINISH: 모든 작업이 완료되었을 때
반드시 다음 중 하나만 답하세요: researcher, coder, FINISH"""},
        *state["messages"]
    ])

    next_agent = response.content.strip().lower()
    if next_agent not in ("researcher", "coder", "finish"):
        next_agent = "finish"
 
    if next_agent == "finish":
        return Command(goto=END, update={
            "next_agent": "finish", "round_count": count
        })
 
    return Command(
        goto=next_agent,
        update={"next_agent": next_agent, "round_count": count}
    )

# 5) 전문가 노드 정의
def researcher(state: State) -> Command:
    """검색 전문가 에이전트"""
    research_llm = llm.bind_tools([web_search])
    response = research_llm.invoke([
        {"role": "system", "content": "당신은 리서치 전문가입니다. 웹 검색 도구를 활용해 정보를 찾으세요."},
        *state["messages"]
    ])
 
    # 도구 호출이 있으면 실행
    if response.tool_calls:
        new_messages = [response] # LLM의 도구 호출 메시지를 먼저 추가
        for tc in response.tool_calls:
            print(f"[researcher tc] {tc['args']}")
            result = web_search.invoke(tc["args"])
            # 모든 도구 실행 결과를 리스트에 담음
            new_messages.append({
                "role": "tool", 
                "tool_call_id": tc["id"], 
                "content": str(result)
            })
        return Command(
            goto="supervisor",
            update={"messages": new_messages}
        )
        # return Command(
        #   goto="supervisor",  # 결과를 슈퍼바이저에게 보고
        #   update={"messages": [
        #     response,
        #     {"role": "tool", "tool_call_id": tc["id"],
        #     "content": result}
        #   ]}
        # )
 
    return Command(goto="supervisor", update={"messages": [response]})
 
def coder(state: State) -> Command:
    """코드 작성 전문가 에이전트"""
    code_llm = llm.bind_tools([write_code])
    response = code_llm.invoke([
        {"role": "system", "content": "당신은 코드 작성 전문가입니다. write_code 도구를 활용하세요."},
        *state["messages"]
    ])
 
    if response.tool_calls:
        new_messages = [response] # LLM의 도구 호출 메시지를 먼저 추가
        for tc in response.tool_calls:
            result = write_code.invoke(tc["args"])
            # 모든 도구 실행 결과를 리스트에 담음
            new_messages.append({
                "role": "tool", 
                "tool_call_id": tc["id"], 
                "content": str(result)
            })
        return Command(
            goto="supervisor",
            update={"messages": new_messages}
        )
 
    return Command(goto="supervisor", update={"messages": [response]})
 
# 6) 그래프 연결
work_flow = StateGraph(State)
work_flow.add_node("supervisor", supervisor)
work_flow.add_node("researcher", researcher)
work_flow.add_node("coder", coder)
work_flow.add_edge(START, "supervisor")
 
graph = work_flow.compile()

# 7) 실행
result = graph.invoke({
    "messages": [("user", "AI 에이전트의 최신 트렌드를 조사하고, 간단하게 스켈레톤으로 예제 코드를 작성해줘")],
    "next_agent": "",
    "round_count": 0
})


# 8) 흐름 추적하기
print("=== 최종 결과 ===")
for msg in result["messages"]:
    if hasattr(msg, "content") and msg.content:
        role = getattr(msg, "role",
                       msg.type if hasattr(msg, "type") else "unknown")
        print(f"[{role}] {msg.content}")
