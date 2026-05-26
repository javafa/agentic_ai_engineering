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

### 커뮤니티 탐지 ------------------------------

# Louvain은 무방향 그래프에서 동작하므로 방향을 제거한다
undirected = graph.to_undirected()

# 커뮤니티 탐지: 밀집 연결된 노드들을 군집으로 묶는다
communities = nx.community.louvain_communities(undirected, seed=42)

print(f"커뮤니티 {len(communities)}개 발견")
for i, comm in enumerate(communities):
    print(f"  커뮤니티 {i}: {sorted(comm)}")

### 커뮤니티 요약 ------------------------------

llm = ChatAnthropic(model="claude-sonnet-4-5")

def summarize_community(community: set) -> str:
    """커뮤니티에 속한 엔티티와 관계를 LLM으로 요약한다."""
    # 군집 내부의 관계(엣지)만 수집한다
    facts = []
    for src, tgt, data in graph.edges(data=True):
        if src in community and tgt in community:
            facts.append(f"{src} --[{data['type']}]--> {tgt}")

    if not facts:                       # 관계가 없으면 엔티티 목록만 사용
        facts = [f"엔티티: {', '.join(sorted(community))}"]

    prompt = f"""다음은 지식 그래프의 한 군집에 속한 엔티티와 관계입니다.
이 군집이 다루는 핵심 주제를 2~3문장으로 요약하세요.

{chr(10).join(facts)}

요약:"""
    return llm.invoke(prompt).content.strip()

# 모든 커뮤니티에 대해 요약 보고서를 미리 생성해 둔다
community_reports = [summarize_community(c) for c in communities]
for i, report in enumerate(community_reports):
    print(f"[커뮤니티 {i} 요약] {report}")

### 글로벌 검색 ------------------------------

def global_search(question: str) -> str:
    """커뮤니티 요약들을 종합해 전역적 질문에 답한다."""
    # 1. 모든 커뮤니티 요약을 하나의 컨텍스트로 모은다
    context = "\n\n".join(
        f"[커뮤니티 {i}] {report}"
        for i, report in enumerate(community_reports)
    )

    # 2. 요약 전체를 근거로 최종 답변을 생성한다
    prompt = f"""아래는 문서 전체를 군집별로 요약한 보고서입니다.
이 보고서들을 종합하여 질문에 답하세요.

{context}

질문: {question}"""
    return llm.invoke(prompt).content.strip()

print(global_search("이 문서들이 다루는 핵심 주제는 무엇인가?"))
