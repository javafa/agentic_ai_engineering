import chromadb
# 1. 임베딩 함수 모듈 추가
from chromadb.utils import embedding_functions
# Open AI Key 로드용
from dotenv import load_dotenv
load_dotenv()

client = chromadb.PersistentClient(path="./chroma_db")

# 2. OpenAI 임베딩 함수 설정 (모델명 지정)
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    model_name="text-embedding-3-small"
)

# 3. 컬렉션 생성 시 embedding_function 지정
# 기존에 "my_memory"가 이미 존재한다면 get_or_create_collection을 사용하는 것이 안전하다
collection = client.get_or_create_collection(
    name="my_memory",
    embedding_function=openai_ef
)

 
# 문서 저장 - 임베딩 값은 자동으로 생성된다
collection.add(
    documents=[
        "user는 개발할 때 파이썬을 주로 사용하는 AI엔지니어입니다.",
        "user는 매주 화요일에 팀 미팅이 있습니다.",
        "user가 좋아하는 카페는 삼청동 ‘서울서 둘째로 잘하는집’입니다.",
        "프로젝트 마감일은 2026년 5월 15일입니다.",
    ],
    ids=["fact_1", "fact_2", "fact_3", "fact_4"]
)
 
# 유사도 검색
results = collection.query(
    query_texts=["사용하는 언어"],
    n_results=2  # 상위 2개 결과
)
 
print("검색 결과:")
for doc, dist in zip(results["documents"][0], results["distances"][0]):
    print(f"  [{dist:.4f}] {doc}")
