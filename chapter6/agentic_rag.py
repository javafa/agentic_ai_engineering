import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
 
load_dotenv()
 
# 벡터 DB 로드 (7.2에서 생성한 DB 재사용)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = Chroma(
    collection_name="tutorial_docs",
    embedding_function=embeddings,
    persist_directory="./chroma_rag_db"
)
 
# 검색 도구 정의
@tool
def search_docs(query: str) -> str:
    """기술 문서에서 관련 내용을 검색합니다.
    질문을 검색에 적합한 키워드로 변환해서 사용하세요."""
    results = vector_store.similarity_search(query, k=3)
    if not results:
        return "관련 문서를 찾을 수 없습니다."
    output = []
    for i, doc in enumerate(results):
        source = doc.metadata.get("source", "unknown")
        output.append(f"[문서 {i+1}] (출처: {source})\n{doc.page_content}")
    return "\n\n".join(output)
 
@tool
def search_with_filter(query: str, chapter: int) -> str:
    """특정 챕터의 문서만 검색합니다.
    chapter: 검색할 챕터 번호"""
    results = vector_store.similarity_search(
        query, k=3,
        filter={"chapter": chapter}
    )
    if not results:
        return f"{chapter}장에서 관련 문서를 찾을 수 없습니다."
    return "\n\n".join(doc.page_content for doc in results)
 
# Agentic RAG 에이전트 생성
llm = ChatOpenAI(model="gpt-5.4-mini")
memory = MemorySaver()
 
SYSTEM_PROMPT = """당신은 기술 문서 기반 질의응답 에이전트입니다.
 
작동 규칙:
1. 질문을 분석하여 필요한 검색을 계획하세요.
2. 복잡한 질문은 여러 번 검색하세요.
3. 검색 결과가 부족하면 다른 키워드로 재검색하세요.
4. 반드시 검색된 문서에 기반해서만 답변하세요.
5. 문서에 없는 내용은 "문서에서 확인할 수 없습니다"라고 답하세요."""
 
agent = create_react_agent(
    llm,
    [search_docs, search_with_filter],
    checkpointer=memory,
    prompt=SYSTEM_PROMPT
)
 
# 실행
config = {"configurable": {"thread_id": "rag_session_1"}}
 
result = agent.invoke(
    {"messages": [("user", "에이전트의 구성 요소를 설명하고, 각 요소가 어떤 역할을 하는지 알려줘")]},
    config=config
)
print(result["messages"][-1].content)
