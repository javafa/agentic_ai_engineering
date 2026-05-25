import tiktoken

class ContextBuilder:
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self.enc = tiktoken.get_encoding("o200k_base")

    def count_msg_token(self, text: str) -> int:
        """텍스트의 토크 + 메타데이터 오버헤드 (4)"""
        return len(self.enc.encode(str(text))) + 4

    def build(self, system: str, profile: str | None, docs: list[str], history: list[dict], current: str) -> list[dict]:
        
        # 1. 시스템 프롬프트 (최우선)
        sys_content = f"{system}\n사용자: {profile}" if profile else system
        budget = self.max_tokens - self.count_msg_token(sys_content)
        
        # 2. 현재 대화
        current_tk = self.count_msg_token(current)
        budget -= current_tk
        
        # 3. 검색 문서
        valid_docs = []
        for doc in docs:
            if (tk := self.count_msg_token(doc)) > budget - 500: break
            valid_docs.append(doc)
            budget -= tk
            
        # 4. 과거 대화 히스토리 (남은 예산 최신순)
        valid_history = []
        for msg in reversed(history):
            if (tk := self.count_msg_token(msg["content"])) > budget: break
            valid_history.insert(0, msg)
            budget -= tk

        # 메시지 조립 순서 1, 3, 4, 2 
        messages = [{"role": "system", "content": sys_content}]
        
        if valid_docs:
            messages.append({"role": "system", "content": "참고:\n" + "\n".join(valid_docs)})
        
        return messages + valid_history + [{"role": "user", "content": current}]