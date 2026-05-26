from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
load_dotenv()


RERANK_SCHEMA = {
    "title": "RerankResult",
    "description": "질문과 관련도가 높은 순서대로 정렬된 문서 인덱스 목록.",
    "type": "object",
    "properties": {
        "relevant_indices": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "관련도 높은 순서로 정렬된 문서 인덱스. 관련 없는 문서는 제외.",
        }
    },
    "required": ["relevant_indices"],
}

llm = ChatAnthropic(model="claude-sonnet-4-5")
structured_llm = llm.with_structured_output(RERANK_SCHEMA)


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
{doc_list}"""

    result = structured_llm.invoke(prompt)
    print("result =>", result)
    indices = result["relevant_indices"][:top_k]
    return [documents[i] for i in indices if 0 <= i < len(documents)]
 

# 예제 문서
documents = [
    "포도는 당분이 많아 피로 회복에 효과적입니다.", # [0] 관련 낮음
    "사과는 비타민 C와 식이섬유가 풍부하여 면역력 강화에 도움을 줍니다.", # [1] 관련 높음
    "운동은 근육량을 늘리고 신진대사를 활발하게 합니다.", # [2] 관련 낮음
    "아침에 먹는 사과는 유기산 성분이 소화를 도와 '금사과'라고 불립니다." # [3] 관련 높음
]

# 리랭킹 함수 실행
print("--- [Reranking 시작] ---")
question = "사과가 몸에 좋은 이유를 알려줘."
reranked_docs = rerank_documents(question, documents, top_k=2)

# 결과 출력
print(f"\n질문: {question}")
print("-" * 30)
for i, doc in enumerate(reranked_docs):
    print(f"순위 {i+1}: {doc}")
