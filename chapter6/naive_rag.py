from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_anthropic import ChatAnthropic
from langchain_voyageai import VoyageAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from dotenv import load_dotenv
 
load_dotenv()
 
# 문서 준비 (실 프로젝트에서는 TextLoader, PyPDFLoader 등 사용)
raw_documents = [
    Document(page_content="""AI 에이전트 개발 가이드
    
    에이전트는 LLM, 툴, 메모리, 하네스의 네 가지 요소로 구성됩니다.
    LLM은 에이전트의 두뇌 역할을 하며, 툴은 외부 세계와 상호작용하는 수단입니다.
    메모리는 대화 히스토리와 학습한 사실을 저장하고, 하네스는 전체 실행을
    코드 레벨에서 제어합니다.
    
    ReAct 패턴은 Thought-Action-Observation의 루프로 동작합니다.
    에이전트는 먼저 생각하고, 툴을 실행하고, 결과를 관찰한 뒤 다음 행동을 결정합니다.
    이 루프에는 반드시 탈출 조건(max_iterations)이 필요합니다.""",
     metadata={"source": "agent_guide.txt", "chapter": 1}),
 
    Document(page_content="""벡터 데이터베이스 활용법
    
    벡터 DB는 텍스트를 숫자 벡터(임베딩)로 변환하여 저장합니다.
    검색 시 코사인 유사도를 사용하여 의미적으로 가까운 문서를 찾습니다.
    ChromaDB, Pinecone, Weaviate 등이 대표적인 벡터 DB입니다.
    
    임베딩 모델은 텍스트를 고차원 벡터로 변환합니다.
    Voyage AI의 voyage-4는 1024차원 벡터를 생성하며,
    비용 효율적이면서도 대부분의 RAG 사용 사례에 충분한 성능을 제공합니다.""",
     metadata={"source": "vector_db.txt", "chapter": 5}),
]
 
# 청킹
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1024,      # 청크당 최대 1024자
    chunk_overlap=128,    # 청크 간 128자 겹침 (문맥 유지)
    separators=["\n\n", "\n", " ", ""]  # 단락 > 줄 > 단어 순으로 분할
)
 
chunks = text_splitter.split_documents(raw_documents)
print(f"원본 문서 {len(raw_documents)}개 → 청크 {len(chunks)}개")
for i, chunk in enumerate(chunks):
    print(f"  청크 {i}: {len(chunk.page_content)}자 (출처: {chunk.metadata['source']})")

# 임베딩 모델 지정
embeddings = VoyageAIEmbeddings(model="voyage-4")
 
# ChromaDB에 생성
vector_store = Chroma(
    collection_name="tutorial_docs",
    embedding_function=embeddings,
    persist_directory="./chroma_rag_db"  # 디스크에 저장
)

# DB에 청크 저장
vector_store.add_documents(documents=chunks)
 
print(f"벡터 DB에 {len(chunks)}개 청크 저장 완료!")


retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}  # 상위 3개 검색
)
 
llm = ChatAnthropic(model="claude-sonnet-4-5")
 
def naive_rag(question: str) -> str:
    """가장 기본적인 RAG 파이프라인"""
    # 1. 관련 문서 검색
    docs = retriever.invoke(question)
 
    # 2. 검색 결과를 컨텍스트로 조합
    context = "\n\n---\n\n".join(doc.page_content for doc in docs)
 
    # 3. LLM에게 컨텍스트와 질문을 함께 전달
    prompt = f"""다음 문서를 참고하여 질문에 답하세요.
답변할 수 없는 내용이면 "문서에서 해당 정보를 찾을 수 없습니다"라고 하세요.
 
참고 문서:
{context}
 
질문: {question}"""
 
    response = llm.invoke(prompt)
    return response.content
 
# 테스트
answer = naive_rag("에이전트의 네 가지 구성 요소는 무엇인가요?")
print(f"답변: {answer}")
 
answer = naive_rag("임베딩 모델의 차원은 몇인가요?")
print(f"답변: {answer}")
