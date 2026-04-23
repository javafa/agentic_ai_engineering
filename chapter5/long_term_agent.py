import json
from openai import OpenAI
from dotenv import load_dotenv
import chromadb
 
load_dotenv()
client = OpenAI()
chroma_client = chromadb.PersistentClient(path="./agent_memory")
collection = chroma_client.get_or_create_collection(name="user_info")

SYSTEM_PROMPT = """당신은 장기 기억을 가진 AI 비서입니다.
 
대화 규칙:
1. 사용자가 자신에 대한 새로운 정보를 말하면, save_memory로 저장합니다.
2. 사용자 질문에 답하기 전, 관련 기억이 있는지 search_memory로 확인합니다.
3. 기억을 활용해 개인화된 응답을 제공합니다.
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
        return "관련 기억이 없습니다."
    facts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        facts.append(f"[{meta['category']}] {doc}")
    return "\n".join(facts)
 
tool_map = {"save_memory": save_memory, "search_memory": search_memory}

# 에이전트가 사용할 Tool 정의
tools = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "사용자에 대해 새로 알게 된 정보를 장기 메모리에 저장합니다.",
            "parameters": {
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
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": "장기 메모리에서 관련 정보를 검색합니다.",
            "parameters": {
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
    }
]
 
def run_agent(user_input: str, messages: list[dict]) -> str:
    """에이전트를 실행한다. (max_iterations로 무한 루프 방지)"""
    messages.append({"role": "user", "content": user_input})
 
    max_iterations = 5
    for i in range(max_iterations):
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=messages,
            tools=tools
        )
 
        choice = response.choices[0]
 
        if choice.finish_reason == "stop":
            assistant_msg = choice.message.content
            messages.append({"role": "assistant", "content": assistant_msg})
            return assistant_msg
 
        if choice.message.tool_calls:
            messages.append(choice.message)
            for tc in choice.message.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                result = tool_map[fn_name](**fn_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result
                })
 
    return "처리 한도에 도달했습니다."

# --- 실행부 추가 ---
if __name__ == "__main__":
    print("🤖 에이전트와 대화를 시작합니다! (종료하려면 'exit' 또는 'quit' 입력)")
    
    # 세션 메시지 초기화
    chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    while True:
        user_msg = input("\n[User]: ").strip()
        
        if user_msg.lower() in ["exit", "quit", "종료"]:
            print("대화를 종료합니다.")
            break

        if not user_msg:
            continue
            
        answer = run_agent(user_msg, chat_history)
        print(f"\n[AI]: {answer}")