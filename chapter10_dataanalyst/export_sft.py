# 확장(계층 3) - 외부 메모리의 성공 사례를 SFT 데이터셋(JSONL)으로 내보낸다.
import json, os
from memory import ExperienceMemory   # state 우회: 커널/다운로드/API키 불필요
from config import SCHEMA_HINT

def export_sft(path: str = "train/sft.jsonl"):
    mem = ExperienceMemory()  # memory/experience.jsonl 읽기
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)   # dir 없는 경로 방어
    with open(path, "w", encoding="utf-8") as f:
        for it in mem.items:
            sample = {"messages": [
                {"role": "system", "content": "데이터 분석 코드를 작성한다.\n" + SCHEMA_HINT},
                {"role": "user", "content": it["question"]},
                {"role": "assistant", "content": it["code"]},
            ]}
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"SFT 데이터 {len(mem.items)}건 > {path}")