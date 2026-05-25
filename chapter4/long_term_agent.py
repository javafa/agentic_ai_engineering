from anthropic import Anthropic
from dotenv import load_dotenv
import chromadb

load_dotenv()
client = Anthropic()
chroma_client = chromadb.PersistentClient(path="./agent_memory")
collection = chroma_client.get_or_create_collection(name="user_info")

SYSTEM_PROMPT = """당신은 장기 메모리를 가진 AI 비서입니다.

대화 규칙:
1. 사용자가 자신에 대한 새로운 정보를 말하면, save_memory로 저장합니다.
2. 사용자 질문에 답하기 전, 관련 메모리가 있는지 search_memory로 확인합니다.
3. 메모리를 활용해 개인화된 응답을 제공합니다.
4. "기억해"라는 표현이 나오면 반드시 save_memory를 호출합니다."""

def save_memory(fact: str, category: str) -> str:
    """정보를 ChromaDB에 저장한다."""
    import uuid
    doc_id = f"{category}_{uuid.uuid4().hex[:8]}"
    collection.add(
        documents=[fact],
        metadatas=[{"category": category}],
        ids=[doc_id]
    )
    return f"저장 완료: {fact}"

def search_memory(query: str) -> str:
    """ChromaDB에서 유사한 정보를 검색한다."""
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    if not results["documents"][0]:
        return "관련 메모리가 없습니다."
    facts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        facts.append(f"[{meta['category']}] {doc}")
    return "\n".join(facts)

tool_map = {"save_memory": save_memory, "search_memory": search_memory}

# 에이전트가 사용할 Tool 정의 (Anthropic 형식)
tools = [
    {
        "name": "save_memory",
        "description": "사용자에 대해 새로 알게 된 정보를 장기 메모리에 저장합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "저장할 정보 (예: 사용자는 고양이 2마리를 키운다)"
                },
                "category": {
                    "type": "string",
                    "enum": ["personal", "preference", "work", "schedule"],
                    "description": "정보의 카테고리"
                }
            },
            "required": ["fact", "category"]
        }
    },
    {
        "name": "search_memory",
        "description": "장기 메모리에서 관련 정보를 검색합니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색 키워드 또는 질문"
                }
            },
            "required": ["query"]
        }
    }
]

def run_agent(user_input: str, messages: list[dict]) -> str:
    """에이전트를 실행한다. (max_iterations로 무한 루프 방지)"""
    messages.append({"role": "user", "content": user_input})

    max_iterations = 5
    for i in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tools
        )

        # 도구 호출이 필요한 경우
        if response.stop_reason == "tool_use":
            # 모델의 응답(도구 호출 포함)을 그대로 messages에 추가
            messages.append({"role": "assistant", "content": response.content})

            # 응답에 포함된 모든 tool_use 블록을 실행
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = tool_map[block.name](**block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            # 도구 실행 결과는 user 메시지로 전달
            messages.append({"role": "user", "content": tool_results})
            continue # 도구 실행 결과를 들고 다음 루프로 이동

        # 최종 답변을 완료한 경우
        if response.stop_reason == "end_turn":
            assistant_msg = "".join(
                b.text for b in response.content if b.type == "text"
            )
            messages.append({"role": "assistant", "content": assistant_msg})
            return assistant_msg

    return "처리 한도에 도달했습니다."


if __name__ == "__main__":
    print("에이전트와 대화를 시작합니다! (종료하려면 'exit' 또는 'quit' 입력)")

    # 세션 메시지 초기화 (시스템 프롬프트는 system 인자로 전달하므로 제외)
    chat_history = []

    while True:
        user_msg = input("\n[User]: ").strip()

        if user_msg.lower() in ["exit", "quit", "종료"]:
            print("대화를 종료합니다.")
            break

        if not user_msg:
            continue

        answer = run_agent(user_msg, chat_history)
        print(f"\n[AI]: {answer}")
