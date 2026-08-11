# 파일 네비게이션

레포 안의 모든 파일이 어디 있고 무엇을 하는 자리인지 한눈에 보기 위한 지도. 설계 배경은 [prd.md](prd.md), 라우팅·작업분할 상세는 [architecture.md](architecture.md) 참고.

## 문서

| 경로 | 내용 |
|---|---|
| `README.md` | 프로젝트 개요, 빠른 시작, 폴더 구조, 필수요건 6종 체크리스트 |
| `docs/prd.md` | 한 문장 정의, 문제/목표, MVP 범위(MoSCoW), 기능·비기능 요구사항, 로드맵, 리스크 |
| `docs/architecture.md` | 메인/서브 에이전트 오케스트레이션 설계(mermaid), 작업 분할 전략, 역할분담표 |
| `docs/multi-agent.md` | 메인/서브 에이전트 패턴 원안(채택됨) |
| `docs/presentation.md` | 미니프로젝트 발표 준비 — 주제 선정 배경/6요소 설계/진행 내용/구현 방식(소통·역할분담) |
| `docs/navigation.md` | 이 문서 |

## 코드 (`app/`)

| 경로 | 이 파일이 하는 일 | 담당 |
|---|---|---|
| `app/main.py` | FastAPI 진입점 — dotenv 로드, 라우터 등록 (예정) | 메인 에이전트 담당 |
| `app/setting.py` | 환경변수(.env) 로드 — pydantic-settings `Settings` | 메인 에이전트 담당 |
| `app/llms/agent.py` | `Agent`/`SubLLM`/`MainLLM` 베이스 클래스 | 메인 에이전트 담당 |
| `app/llms/main_agent.py` | `MainAgent` — 서브 에이전트 동시 호출·히스토리(메모리)·스트리밍 오케스트레이터 | 메인 에이전트 담당 |
| `app/llms/sub_agents.py` | 카테고리별 서브 에이전트 — `BusinessAgent`(경제), `BaseballAgent`(야구)/`HealthAgent`(건강) 중 택1, `DevelopmentAgent`(개발), 담당자 자율 선택 | 서브 에이전트 담당 3명 |
| `app/schemas/` | Pydantic 스키마 (예정) | 서브 에이전트 담당 |
| `tests/` | 엣지케이스 테스트, 데모 스크립트 | 테스트·QA·발표 |

## 설정

| 경로 | 내용 |
|---|---|
| `pyproject.toml` / `uv.lock` | 의존 패키지 목록 (uv 관리) |
| `.env.example` | 필요한 환경변수 목록(`OPENAI_API_KEY`, `NAVER_CLIENT_ID/SECRET`, `LANGCHAIN_*`) — 복사해서 `.env`로 채울 것 |
| `.gitignore` | `.venv/`, `__pycache__/`, `.env` 등 커밋 제외 목록 |
| `.pre-commit-config.yaml` | ruff·pyrefly pre-commit 훅 |

## 아직 없는 것 (필요해지면 추가)

- 추가 ERD/DB 모델 — MVP는 무상태(in-memory `self.memory`)라 당장은 불필요(prd.md 12번 참고)
- 프론트엔드 — 스코프 가드레일상 이번 블록은 터미널/curl/`/docs`로 대체
- `app/main.py`의 FastAPI 라우팅 — 메인 에이전트 연동 전까지는 비어있음
