from langgraph.checkpoint.sqlite import SqliteSaver
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
 
# SQLite 파일에 상태 저장
with SqliteSaver.from_conn_string("agent_state.db") as checkpointer:
    llm = ChatOpenAI(model="gpt-5.4-mini")
    agent = create_agent(llm, tools=[], checkpointer=checkpointer)
 
    config = {"configurable": {"thread_id": "session_001"}}
 
    # 첫 번째 대화
    result = agent.invoke(
        {"messages": [("user", "내 이름은 민수야. 기억해줘.")]},
        config=config
    )
    print(result["messages"][-1].content)
 
# ... 프로세스 재시작 후에도 ...
 
with SqliteSaver.from_conn_string("agent_state.db") as checkpointer:
    llm = ChatOpenAI(model="gpt-5.4-mini")
    agent = create_agent(llm, tools=[], checkpointer=checkpointer)
 
    config = {"configurable": {"thread_id": "session_001"}}
 
    # 이전 대화 이어가기
    result = agent.invoke(
        {"messages": [("user", "내 이름이 뭐였지?")]},
        config=config
    )
    print(result["messages"][-1].content)
