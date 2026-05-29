import os
from langchain_anthropic import ChatAnthropic
from langchain_voyageai import VoyageAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
 
load_dotenv()
 
# 벡터 DB 로드 (7.2에서 생성한 DB 재사용)
embeddings = VoyageAIEmbeddings(model="voyage-4")
vector_store = Chroma(
    collection_name="tutorial_docs",
    embedding_function=embeddings,
    persist_directory="./chroma_rag_db"
)
 
# 검색 도구 정의
@tool
def search_docs(query: str) -> str:
    """기술 문서에서 관련 내용을 검색한다.
    질문을 검색에 적합한 키워드로 변환해서 사용한다."""
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
    """특정 챕터의 문서만 검색한다.
    chapter: 검색할 챕터 번호"""
    results = vector_store.similarity_search(
        query, k=3,
        filter={"chapter": chapter}
    )
    if not results:
        return f"{chapter}장에서 관련 문서를 찾을 수 없습니다."
    return "\n\n".join(doc.page_content for doc in results)

# Agentic RAG 에이전트 생성
llm = ChatAnthropic(model="claude-sonnet-4-5")
memory = MemorySaver()

SYSTEM_PROMPT = """당신은 기술 문서 기반 질의응답 에이전트입니다.
규칙:
1. 질문을 분석하여 필요한 검색을 계획합니다.
2. 복잡한 질문은 여러 번 검색합니다.
3. 검색 결과가 부족하면 다른 키워드로 재검색합니다.
4. 반드시 검색된 문서에 기반해서만 답변합니다.
5. 문서에 없는 내용은 "문서에서 확인할 수 없습니다"라고 답합니다."""

agent = create_agent(
    llm,
    [search_docs, search_with_filter],
    checkpointer=memory,
    system_prompt=SYSTEM_PROMPT
)

# 실행
config = {"configurable": {"thread_id": "rag_session_1"}}

result = agent.invoke(
    {"messages": [("user", "에이전트의 구성 요소를 설명하고, 각 요소가 어떤 역할을 하는지 알려줘")]},
    config=config
)

print(result["messages"][-1].content)
