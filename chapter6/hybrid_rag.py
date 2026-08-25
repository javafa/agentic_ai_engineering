from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers.bm25 import BM25Retriever # 키워드기반 검색
from langchain_classic.retrievers.ensemble import EnsembleRetriever       # 복수 Retriever의 순위 통합
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_voyageai import VoyageAIEmbeddings
from dotenv import load_dotenv
 
load_dotenv()


# kiwi 를 활용해 한국어를 토큰화한다.
# 차이 
# 1. query.lower().split() 사용시 - 띄어쓰기 단위. 영어에 최적화
# [ "voyage", "ai의", "voyage-4", "모델의", "벡터", "차원은?" ]
# 2. kiwi tokenizer 사용 시 - 조사까지 분해 해준다
# [ "Voyage", "AI", "의", "voyage-4", "모델", "의", "벡터", "차원", "은", "?" ]
# 한국어 토크나이저
from kiwipiepy import Kiwi
kiwi = Kiwi()
def tokenize(text):
    return [token.form for token in kiwi.tokenize(text)]

# 6.2 에서 작성한 코드의 앞부분 사용 > raw_documents, text_splitter, chunks
# 문서 준비 (실 프로젝트에서는 TextLoader, PyPDFLoader 등 사용)
raw_documents = [
    Document(page_content="""AI 에이전트 개발 가이드
    
    에이전트는 LLM, 도구, 메모리, 하네스의 네 가지 요소로 구성됩니다.
    LLM은 에이전트의 두뇌 역할을 하며, 도구는 외부 세계와 상호작용하는 수단입니다.
    메모리는 대화 히스토리와 학습한 사실을 저장하고, 하네스는 전체 실행을
    코드 레벨에서 제어합니다.
    
    ReAct 패턴은 Thought-Action-Observation의 루프로 동작합니다.
    에이전트는 먼저 생각하고, 도구를 실행하고, 결과를 관찰한 뒤 다음 행동을 결정합니다.
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
    chunk_size=500,      # 청크당 최대 500자
    chunk_overlap=50,    # 청크 간 50자 겹침 (문맥 유지)
    separators=["\n\n", "\n", " ", ""]  # 단락 > 줄 > 단어 순으로 분할
)
 
chunks = text_splitter.split_documents(raw_documents)


# 문서 조각(chunks) 객체를 바탕으로 BM25 인덱스 생성
bm25_retriever = BM25Retriever.from_documents(chunks, preprocess_func=tokenize)

# 키워드 검색 시 반환할 결과 문서의 개수 지정
bm25_retriever.k = 3

# 임베딩 모델 설정 (기존에 사용한 모델과 동일해야 함)
embeddings = VoyageAIEmbeddings(model="voyage-4")

# 로컬에 저장된 Chroma DB 로드
vector_store = Chroma(
    collection_name="tutorial_docs",
    embedding_function=embeddings,
    persist_directory="./chroma_rag_db"
)

# 벡터 DB를 검색기로 로드
vector_retriever = vector_store.as_retriever(search_kwargs={"k": 3}) # 상위 3개

# 내부적으로 RRF 알고리즘이 사용됨
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.4, 0.6]
)

# 사용자의 질문 정의
query = "Voyage AI의 voyage-4 모델의 벡터 차원은?"

# 통합 검색기를 호출하여 최종 문서 리스트 추출
docs = ensemble_retriever.invoke(query)

# 콘솔 창에 결과 출력
print(f"--- '{query}' 검색 결과 ---")
for i, doc in enumerate(docs):
    print(f"\n[순위 {i+1}]")
    print(doc.page_content)
