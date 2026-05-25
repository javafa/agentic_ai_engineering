import chromadb

# 대화 내용을 파일로 저장
# client = chromadb.PersistentClient(path="./chroma_db")
client = chromadb.Client() # 인메모리 클라이언트로 사용가능 (종료 시 데이터 사라짐)
 
# 컬렉션 생성 : 일반 DB에서 테이블과 비슷한 개념
collection = client.create_collection(name="my_memory")
 
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
    query_texts=["user의 미팅 스케쥴은?"],
    n_results=4  # 상위 4개 결과
)
 
print("검색 결과:")
for doc, dist in zip(results["documents"][0], results["distances"][0]):
    print(f"  [{dist:.4f}] {doc}")
