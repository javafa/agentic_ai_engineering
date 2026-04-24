import json
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(model="gpt-5.4-mini")
 
def rerank_documents(
    question: str,
    documents: list[str],
    top_k: int = 3
) -> list[str]:
    """검색된 문서를 LLM으로 재평가하여 관련도순으로 정렬합니다."""
    doc_list = "\n".join(f"[{i}] {doc[:200]}" for i, doc in enumerate(documents))
 
    prompt = f"""질문과 관련도가 높은 문서 번호를 순서대로 나열하세요.
관련 없는 문서는 제외하세요.
 
질문: {question}
 
문서 목록:
{doc_list}
 
JSON 형식으로 응답: {{"relevant_indices": [0, 2, ...]}}"""
 
    response = llm.invoke(prompt)
    try:
        result = json.loads(response.content)
        indices = result["relevant_indices"][:top_k]
        return [documents[i] for i in indices if i < len(documents)]
    except (json.JSONDecodeError, KeyError, IndexError):
        return documents[:top_k]  # 실패 시 원래 순서 유지

# 실행 예제
documents = [
    "포도는 당분이 많아 피로 회복에 효과적입니다.", # [0] 관련 낮음
    "사과는 비타민 C와 식이섬유가 풍부하여 면역력 강화에 도움을 줍니다.", # [1] 관련 높음
    "운동은 근육량을 늘리고 신진대사를 활발하게 합니다.", # [2] 관련 낮음
    "아침에 먹는 사과는 유기산 성분이 소화를 도와 '금사과'라고 불립니다." # [3] 관련 높음
]

# 1. 리랭킹 함수 실행
print("--- [Reranking 시작] ---")
question = "사과가 몸에 좋은 이유를 알려줘."
reranked_docs = rerank_documents(question, documents, top_k=2)

# 2. 결과 출력
print(f"\n질문: {question}")
print("-" * 30)
for i, doc in enumerate(reranked_docs):
    print(f"순위 {i+1}: {doc}")