from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.documents import Document
from dotenv import load_dotenv
 
load_dotenv()
 
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
    OpenAI의 text-embedding-3-small은 1536차원 벡터를 생성하며,
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
print(f"원본 문서 {len(raw_documents)}개 → 청크 {len(chunks)}개")
for i, chunk in enumerate(chunks):
    print(f"  청크 {i}: {len(chunk.page_content)}자 (출처: {chunk.metadata['source']})")
