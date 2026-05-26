import json
import networkx as nx
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

load_dotenv()
llm = ChatAnthropic(model="claude-sonnet-4-5")

# 온톨로지: 추출할 엔티티와 관계의 타입을 미리 정의한다
ONTOLOGY = {
    "entity_types": ["Person", "Organization", "Technology", "Concept"],
    "relation_types": ["DEVELOPS", "DEPENDS_ON", "PART_OF", "USES"],
}

def extract_graph(text: str) -> dict:
    """청크에서 온톨로지에 맞는 엔티티와 관계를 추출한다."""
    prompt = f"""다음 텍스트에서 엔티티와 관계를 추출하세요.
정의된 타입만 사용하세요.

엔티티 타입: {ONTOLOGY['entity_types']}
관계 타입: {ONTOLOGY['relation_types']}

텍스트:
{text}

아래 JSON 형식으로만 응답하세요:
{{"entities": [{{"name": "이름", "type": "타입"}}],
  "relations": [{{"source": "출발", "target": "도착", "type": "관계"}}]}}"""

    response = llm.invoke(prompt)
    raw = response.content.strip()
    if raw.startswith("```"):              # 마크다운 코드블록 제거
        raw = raw.split("```")[1].lstrip("json").strip()
    return json.loads(raw)

# 구조화된 청크 (실제로는 섹션 단위로 분할한 결과를 사용)
chunks = [
    "Anthropic은 Claude라는 LLM을 개발한다. Claude는 에이전트의 두뇌 역할을 한다.",
    "RAG 파이프라인은 벡터 DB에 의존한다. 벡터 DB는 임베딩 모델을 사용한다.",
]

# 1. 모든 청크에서 엔티티와 관계를 추출해 그래프를 만든다
graph = nx.DiGraph()
for chunk in chunks:
    result = extract_graph(chunk)
    for ent in result["entities"]:
        graph.add_node(ent["name"], type=ent["type"])
    for rel in result["relations"]:
        graph.add_edge(rel["source"], rel["target"], type=rel["type"])

print(f"노드 {graph.number_of_nodes()}개, 엣지 {graph.number_of_edges()}개 생성")

# 2. Local 검색: 특정 엔티티의 이웃 관계를 따라간다
def local_search(entity: str) -> str:
    if entity not in graph:
        return f"'{entity}' 엔티티를 찾을 수 없습니다."
    facts = []
    for _, target, data in graph.out_edges(entity, data=True):
        facts.append(f"{entity} --[{data['type']}]--> {target}")
    for source, _, data in graph.in_edges(entity, data=True):
        facts.append(f"{source} --[{data['type']}]--> {entity}")
    return "\n".join(facts) if facts else f"'{entity}'의 관계가 없습니다."

print(local_search("Claude"))
