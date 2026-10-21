<h1><small><small><small><small>하네스 엔지니어링으로 완성하는</small></small></small></small> 에이전틱 AI</h1>

> 도서 **『하네스 엔지니어링으로 완성하는 에이전틱 AI』**의 장별 실습 코드입니다. **Claude(Anthropic) + LangGraph** 중심.

코드 폴더 `chapterN/`은 책의 **N장**과 1:1로 대응합니다.

---

## 빠른 시작

```bash
git clone <this-repo>
cd agentic-ai-engineering

# 가상환경 (venv 또는 conda)
python -m venv .venv && source .venv/bin/activate
#   conda create -n agentic python=3.11 && conda activate agentic

pip install -r requirements.txt          # 공통 의존성
```

저장소 루트에 `.env` 파일을 만들고 사용하는 키를 채웁니다(이 파일은 git에서 제외됨).

```dotenv
ANTHROPIC_API_KEY=sk-ant-...   # Claude — 대부분의 장에서 사용 (필수)
VOYAGE_API_KEY=...             # 6장 RAG 임베딩 (VoyageAI)
WEATHER_API_KEY=...            # 2장 날씨 도구, 10장 날씨 보강
```

대부분의 예제는 **단독 실행 스크립트**입니다. 저장소 루트에서 바로 실행하세요.

```bash
python chapter2/weather.py
python chapter11/graph.py
```

> 10 · 11 · 13장은 추가 의존성이 있습니다 — [장별 추가 설치](#장별-추가-설치) 참고.

---

## 목차

### 1부 · 에이전트의 핵심 원리
| 장 | 제목 | 주요 내용 | 코드 |
|:--:|------|------|------|
| 1 | AI 에이전트의 시대 | 챗봇·RAG·에이전트 비교, ReAct, LLM·메모리·툴, 하네스 엔지니어링, 개발환경 구성 | — |
| 2 | 툴 사용 | 툴 호출 흐름, 날씨 API 에이전트, 멀티 툴, 스키마 설계, MCP vs CLI | [`chapter2/`](chapter2) |
| 3 | ReAct 패턴 구현 | 툴 사용·JSON 기반 ReAct, LangGraph ReAct, 무한 루프 방지 | [`chapter3/`](chapter3) |
| 4 | 메모리 시스템 구축 | 단기·요약 메모리, 벡터 DB 장기 메모리, 메모리 압축, 체크포인터 | [`chapter4/`](chapter4) |
| 5 | 컨텍스트와 하네스 엔지니어링 | 컨텍스트 관리, 입력 검증, 구조화된 출력, 가드레일 | [`chapter5/`](chapter5) |

### 2부 · 에이전트 확장하기
| 장 | 제목 | 주요 내용 | 코드 |
|:--:|------|------|------|
| 6 | RAG + 에이전트 결합 | RAG 파이프라인, Agentic RAG, GraphRAG, 하이브리드 RAG | [`chapter6/`](chapter6) |
| 7 | LangGraph 기반 에이전트 워크플로우 | StateGraph, 조건부 라우팅, Human-in-the-Loop, 스트리밍 | [`chapter7/`](chapter7) |
| 8 | 멀티 에이전트 오케스트레이션 | 슈퍼바이저·핸드오프·계층형 패턴, 안전한 상태 관리 | [`chapter8/`](chapter8) |

### 3부 · 실전 프로젝트
| 장 | 제목 | 주요 내용 | 코드 |
|:--:|------|------|------|
| 9 | 프로젝트: 출근하는 증권맨(정보 워크플로우 에이전트) | 지표 수집 → 종목 점검 → 뉴스 수집 → 브리핑 → 카카오톡/슬랙 전송 | [`chapter9/`](chapter9) |
| 10 | 프로젝트: 끈질긴 주니어 데이터 분석가(자기수정 에이전트) | 생성 → 실행 → 해석 → 자기수정 루프, DuckDB·영속 커널 | [`chapter10/`](chapter10) |
| 11 | 프로젝트: 부탁을 듣는 집사 로봇(멀티모달 에이전트) | 비전 인지 → 계획 → 행동 → 재인지 루프(PyBullet) | [`chapter11/`](chapter11) |

### 4부 · 프로덕션과 운영
| 장 | 제목 | 주요 내용 | 코드 |
|:--:|------|------|------|
| 12 | 하네스 보안: 안전성과 가드레일 | 프롬프트 인젝션 방어, 입출력 검증, 실행 차단, 샌드박스 격리 | — |
| 13 | 비용과 보안을 위한 오픈소스 LLM 서빙 | vLLM·PagedAttention, Qwen2.5·Llama 3.1 서빙, 로컬 에이전트 전환, Prefix Caching | [`chapter13/`](chapter13) |
| 14 | 배포와 운영 | FastAPI 에이전트 서버, AWS Lambda 서버리스 배포, 관측성·비용 모니터링 | — |

---

## 장별 추가 설치

대부분의 장은 루트 `requirements.txt`로 충분하지만, 다음 장은 추가 설치가 필요합니다.

- **10장 — 끈질긴 주니어 데이터 분석가**
  DuckDB·실행 커널 등.
  ```bash
  pip install -r chapter10/requirements.txt
  ```

- **11장 — 부탁을 듣는 집사 로봇**
  PyBullet 물리 시뮬레이터가 필요합니다(macOS Apple Silicon 빌드 안내 포함).
  ```bash
  pip install -r chapter11/requirements.txt
  ```
  설치/뷰어 안내는 [`chapter11/README.md`](chapter11/README.md) 참고 — `ROBOT_GUI=1 python graph.py`로 실시간 3D 뷰어 실행.

- **13장 — 비용과 보안을 위한 오픈소스 LLM 서빙**
  vLLM과 **NVIDIA GPU**가 필요합니다(예: RTX 3090). 서버 기동 후 에이전트의 `base_url`만 로컬 모델로 바꿉니다.
  ```bash
  pip install -r chapter13/requirements.txt
  bash chapter13/run_vllm.sh        # 또는 run_vllm_llama.sh
  ```

---

## 요구사항

- Python 3.12 권장
- API 키: `ANTHROPIC_API_KEY`(필수), 사용 장에 따라 `VOYAGE_API_KEY` / `WEATHER_API_KEY`.
- 일부 기능은 외부 서비스·하드웨어가 필요합니다(9장 카카오·슬랙 알림, 13장 GPU 서빙).
