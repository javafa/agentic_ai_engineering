import json
import os
from difflib import SequenceMatcher
from config import MEMORY_PATH
 
def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()
 
class ExperienceMemory:
    def __init__(self, path: str = MEMORY_PATH):
        self.path = path
        self.items = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.items = [json.loads(l) for l in f if l.strip()]

    def retrieve(self, question: str, k: int = 2) -> list:
        """질문과 가장 비슷한 과거 성공 사례 k개를 돌려준다(few-shot용)."""
        ranked = sorted(self.items, key=lambda it: _similar(question, it["question"]),
                        reverse=True)
        return [it for it in ranked if _similar(question, it["question"]) > 0.3][:k]

    def remember(self, question: str, code: str) -> None:
        """성공 사례를 파일에 한 줄(JSONL)로 누적한다."""
        rec = {"question": question, "code": code}
        self.items.append(rec)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

