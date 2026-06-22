# Agentic AI Engineering

> Example code for the book ***Agentic AI Engineering*** — built around **Claude (Anthropic) + LangGraph**.
> 도서 **『Agentic AI Engineering』**의 장별 실습 코드입니다. **Claude(Anthropic) + LangGraph** 중심.

Code folder `chapterN/` maps 1:1 to **Chapter N** of the book.
코드 폴더 `chapterN/`은 책의 **N장**과 1:1로 대응합니다.

---

## Quick Start / 빠른 시작

```bash
git clone <this-repo>
cd agentic-ai-engineering

# Virtual env (venv or conda) / 가상환경 (venv 또는 conda)
python -m venv .venv && source .venv/bin/activate
#   conda create -n agentic python=3.11 && conda activate agentic

pip install -r requirements.txt          # common deps / 공통 의존성
```

Create a `.env` file in the repo root with the keys you use (it is git-ignored).
저장소 루트에 `.env` 파일을 만들고 사용하는 키를 채웁니다(이 파일은 git에서 제외됨).

```dotenv
ANTHROPIC_API_KEY=sk-ant-...   # Claude — used by most chapters (required) / 대부분의 장에서 사용 (필수)
VOYAGE_API_KEY=...             # Ch.6 RAG embeddings (VoyageAI) / 6장 RAG 임베딩
WEATHER_API_KEY=...            # Ch.2 weather tool, Ch.10 weather augmentation / 2장 날씨 도구, 10장 날씨 보강
```

Most examples are **standalone scripts** — run them from the repo root.
대부분의 예제는 **단독 실행 스크립트**입니다. 저장소 루트에서 바로 실행하세요.

```bash
python chapter2/weather.py
python chapter11/graph.py
```

> Chapters 10 / 11 / 13 have extra dependencies — see [Per-chapter setup](#per-chapter-setup--장별-추가-설치).
> 10 · 11 · 13장은 추가 의존성이 있습니다 — [장별 추가 설치](#per-chapter-setup--장별-추가-설치) 참고.

---

## Table of Contents / 목차

Columns: Chapter · Topic (EN — 한국어) · Code folder.
열: 장 · 주제(영문 — 한국어) · 코드 폴더.

### Part 1 · Foundations / 기초 다지기
| Ch / 장 | Topic / 주제 | Code |
|:--:|------|------|
| 1 | Age of AI Agents — 챗봇/RAG/에이전트 비교, ReAct, 하네스 개관 | — |

### Part 2 · Core Concept Tutorials / 핵심 개념 튜토리얼
| Ch / 장 | Topic / 주제 | Code |
|:--:|------|------|
| 2 | Tool Use — 도구 호출 원리·멀티 툴·스키마 설계 | [`chapter2/`](chapter2) |
| 3 | ReAct Pattern — Reasoning+Acting 루프, LangGraph ReAct | [`chapter3/`](chapter3) |
| 4 | Memory Systems — 단기/요약/장기(ChromaDB), Checkpointer | [`chapter4/`](chapter4) |
| 5 | Context & Harness Engineering — 입력검증·구조화 출력·가드레일 | [`chapter5/`](chapter5) |
| 6 | RAG + Agents — Agentic / Graph / Hybrid RAG | [`chapter6/`](chapter6) |

### Part 3 · Frameworks / 프레임워크
| Ch / 장 | Topic / 주제 | Code |
|:--:|------|------|
| 7 | Working with LangGraph — StateGraph·라우팅·HITL·스트리밍 | [`chapter7/`](chapter7) |
| 8 | Multi-Agent Orchestration — 슈퍼바이저/워커, 핸드오프 | [`chapter8/`](chapter8) |

### Part 4 · Hands-on Projects / 실전 프로젝트
| Ch / 장 | Topic / 주제 | Code |
|:--:|------|------|
| 9 | The Commuting Stock Trader — 정보 워크플로우 에이전트(지표·뉴스·브리핑·발송) | [`chapter9/`](chapter9) |
| 10 | The Persistent Junior Analyst — 자기교정 코드 실행 루프 | [`chapter10/`](chapter10) |
| 11 | The Butler Robot — 멀티모달 인지·계획·행동(PyBullet) | [`chapter11/`](chapter11) |

### Part 5 · Production Deployment / 프로덕션 배포
| Ch / 장 | Topic / 주제 | Code |
|:--:|------|------|
| 12 | Harness Security — Prompt Injection 방어, 샌드박스 격리 | — |
| 13 | Open-Source LLM Serving — vLLM으로 Qwen/Llama 구동, base_url 전환 | [`chapter13/`](chapter13) |
| 14 | Deployment & Operations — FastAPI 서버, Docker, Observability | — |

---

## Code Directories / 코드 디렉터리

| Folder | Key files / 핵심 파일 |
|------|-----------|
| [`chapter2/`](chapter2)  | `weather.py`, `multi_tool_agent.py` |
| [`chapter3/`](chapter3)  | `react_agent.py`, `react_json_agent.py`, `langgraph_react.py`, `state_graph.py` |
| [`chapter4/`](chapter4)  | `basic_memory.py`, `sliding_window.py`, `summary_memory.py`, `entity_memory.py`, `hybrid_memory.py`, `long_term_agent.py`, `chroma_basic.py`, `checkpointer_sqlite.py` |
| [`chapter5/`](chapter5)  | `agent_harness.py`, `structured_output.py`, `pydantic_output.py`, `injection_guard.py`, `pii_filter.py`, `cost_guard.py`, `auto_recovery.py` |
| [`chapter6/`](chapter6)  | `naive_rag.py`, `query_rewrite.py`, `reranking.py`, `agentic_rag.py`, `graph_rag.py`, `hybrid_rag.py` |
| [`chapter7/`](chapter7)  | `tool_graph.py`, `custom_routing.py`, `human_approval.py`, `streaming_basic.py`, `streaming_tool.py`, `extended_state.py` |
| [`chapter8/`](chapter8)  | `supervisor.py`, `handoff.py`, `hierarchical.py` |
| [`chapter9/`](chapter9)  | `main.py`, `market.py`, `news.py`, `formatter.py`, `notify.py`, `scheduler.py`, `eval_metrics.py` |
| [`chapter10/`](chapter10) | `graph.py`, `executor.py`, `nodes.py`, `state.py`, `safety.py`, `memory.py`, `eval.py`, `train/` |
| [`chapter11/`](chapter11) | `sim.py`, `perception.py`, `planner.py`, `graph.py`, `eval.py`, `room.urdf`, `smoke_test.py` |
| [`chapter13/`](chapter13) | `run_vllm.sh`, `run_vllm_llama.sh`, `chat_anthropic.py`, `request_test_anthropic.py` |

---

## Per-chapter Setup / 장별 추가 설치

Most chapters run with the root `requirements.txt`. These need extra installs:
대부분의 장은 루트 `requirements.txt`로 충분하지만, 다음 장은 추가 설치가 필요합니다.

- **Ch.11 — The Butler Robot / 집사 로봇**
  Needs the PyBullet physics simulator (macOS Apple Silicon build notes included).
  PyBullet 물리 시뮬레이터가 필요합니다(macOS Apple Silicon 빌드 안내 포함).
  ```bash
  pip install -r chapter11/requirements.txt
  ```
  See [`chapter11/README.md`](chapter11/README.md) for install/viewer details — run the live 3D viewer with `ROBOT_GUI=1 python graph.py`.
  설치/뷰어 안내는 [`chapter11/README.md`](chapter11/README.md) 참고 — `ROBOT_GUI=1 python graph.py`로 실시간 3D 뷰어 실행.

- **Ch.10 — The Persistent Junior Analyst / 데이터 분석가**
  DuckDB and a persistent execution kernel, etc.
  DuckDB·실행 커널 등.
  ```bash
  pip install -r chapter10/requirements.txt
  ```

- **Ch.13 — Open-Source LLM Serving / 오픈소스 LLM 서빙**
  Requires vLLM and an **NVIDIA GPU** (e.g. RTX 3090). After the server starts, switch the agent's `base_url` to the local model.
  vLLM과 **NVIDIA GPU**가 필요합니다(예: RTX 3090). 서버 기동 후 에이전트의 `base_url`만 로컬 모델로 바꿉니다.
  ```bash
  pip install -r chapter13/requirements.txt
  bash chapter13/run_vllm.sh        # or run_vllm_llama.sh
  ```

---

## Requirements / 요구사항

- Python 3.11 recommended / Python 3.11 권장
- API keys: `ANTHROPIC_API_KEY` (required); plus `VOYAGE_API_KEY` / `WEATHER_API_KEY` depending on the chapter.
  API 키: `ANTHROPIC_API_KEY`(필수), 사용 장에 따라 `VOYAGE_API_KEY` / `WEATHER_API_KEY`.
- Some features need external services/hardware (Ch.9 Kakao/Slack notifications, Ch.13 GPU serving).
  일부 기능은 외부 서비스/하드웨어가 필요합니다(9장 카카오·슬랙 알림, 13장 GPU 서빙).
