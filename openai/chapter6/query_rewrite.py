from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(model="gpt-5.4-mini")
 
def rewrite_query(original_query: str, chat_history: str = "") -> str:
    """검색에 최적화된 쿼리로 리라이팅합니다."""
    prompt = f"""당신은 검색 쿼리 최적화 전문가입니다.
사용자의 질문을 벡터 DB 검색에 최적화된 형태로 바꿔주세요.
 
규칙:
1. 대명사(그것, 이것)를 구체적 명사로 교체
2. 핵심 키워드를 포함
3. 한 문장으로 작성
 
대화 맥락: {chat_history}
원래 질문: {original_query}
최적화된 검색 쿼리:"""
 
    response = llm.invoke(prompt)
    return response.content.strip()
 
# 실행 예제
original = "그거 어떻게 만들어?"
history = "사용자: ReAct 패턴에 대해 설명해줘\nAI: ReAct는..."
rewritten = rewrite_query(original, history)
print(f"원래: {original}")
print(f"리라이팅: {rewritten}")

