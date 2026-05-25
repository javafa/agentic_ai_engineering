from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
 
load_dotenv()
 
# 상태 정의
class State(TypedDict):
    messages: Annotated[list, add_messages]

# LLM 모델 정의
llm = ChatOpenAI(model="gpt-5.4-mini")

# 1) 노드 함수 생성
def chatbot(state: State) -> dict:
    """LLM을 호출하는 노드"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}
 
# 2) 그래프 초기화
work_flow = StateGraph(State)
 
# 3) 생성한 노드 그래프에 추가
work_flow.add_node("chatbot", chatbot)
 
# 4) 엣지 연결
work_flow.add_edge(START, "chatbot")  # 1. 시작 → chatbot
work_flow.add_edge("chatbot", END)    # 2. chatbot → 종료
 
# 5) 그래프 컴파일 - 실제 가능한 객체로 변환
graph = work_flow.compile()
 
# 6) 실행
result = graph.invoke({"messages": [("user", "안녕! LangGraph가 뭐야?")]})
print(result["messages"][-1].content)
