# 파일 네비게이션

레포 안의 파일이 어디 있고 무엇을 하는 자리인지 한눈에 보기 위한 지도입니다. 설계 배경은 [prd.md](prd.md), 구조 상세는 [architecture.md](architecture.md)를 참고하세요.

## 문서

| 경로 | 내용 |
|---|---|
| `README.md` | 프로젝트 소개, 에이전트 목록, 빠른 시작, 필수요건 6종 체크리스트 |
| `docs/prd.md` | 한 문장 정의, 범위, 기능·비기능 요구사항, 진행 경과, 리스크 |
| `docs/architecture.md` | 계층 구조, 에이전트별 파이프라인, 스트리밍 형식, 설계 결정 |
| `docs/navigation.md` | 이 문서 |
| `docs/07_usage.md` | 채팅 UI·file-converter 사용법(curl, Python) |
| `docs/branching.md` | 브랜치 규칙, PR 흐름, `main` 보호 설정 |
| `docs/presentation.md` | 발표 준비 자료(파일 변환 + 채팅 UI 담당 파트 기준) |
| `docs/00_project_brief.md` ~ `docs/03_screen_contract.md`, `docs/06_open_questions.md` | 채팅 UI 요구사항 인터뷰 정본(브리프·요구사항·UI 플로우·화면 계약·미결 질문·결정 로그) |
| `docs/multi-agent.md` | 채택하지 않은 메인/서브 에이전트 오케스트레이션 설계 메모 |
| `docs/course-reference.md` | 교육 내용(비동기·FastAPI·Pydantic·SSE)과 코드 구조 연결 |
| `docs/superpowers/specs/` | YouTube 도구 설계서 2건 — **현재 코드에는 구현되어 있지 않음**(각 문서 상단 참고) |

## 앱 진입점·설정 (`app/`)

| 경로 | 하는 일 |
|---|---|
| `app/main.py` | FastAPI 진입점 — 라우터 6개 등록, `/static` 마운트, `/`(채팅 UI), `/health` |
| `app/setting.py` | `.env` 기반 설정(`pydantic-settings`) |
| `app/dependencies.py` | `Depends`로 주입하는 에이전트·서비스 생성 함수 |
| `app/log_stream.py` | 서버 로그를 캡처해 `/logs/stream`으로 흘려보내는 SSE 소스 |

## 라우터 → 서비스 → 에이전트

| 에이전트 | 라우터 | 서비스 | 에이전트 구현 | 스키마 |
|---|---|---|---|---|
| 파일 변환 | `app/routers/chat.py`, `app/routers/file_converter.py` | `app/services/chat.py` | `app/llms/file_converter_agent.py` | `app/schemas/chat.py`, `app/schemas/file_converter.py` |
| KBO | `app/routers/kbo.py` | `app/services/kbo.py` | `app/llms/kbo.py` | `app/schemas/kbo.py` |
| Tech | `app/routers/tech.py` | `app/services/tech.py` | `app/llms/tech.py` | `app/schemas/tech.py` |
| 금융 | `app/routers/finance.py` | `app/services/finance.py` | `app/llms/business_agent.py` | `app/schemas/finance.py`, `app/schemas/evaluation.py` |
| 로그 | `app/routers/logs.py` | — | — | — |

공용 베이스는 `app/llms/agent.py`(`Agent(ABC)`)입니다. `app/schemas/search.py`는 웹 검색 도구의 입력 스키마입니다.

## 도구 (`app/tools/`)

| 경로 | 내용 |
|---|---|
| `base.py` | 공용 `BaseTool`(LangChain `BaseTool` + 공용 설정) |
| `web_search.py` | Tavily 웹 검색 — `WebSearchTool`, 결과를 캐시하는 `CachedWebSearchTool` |
| `date_time.py` | 현재 날짜·시각 도구(KBO가 사용) |
| `finance.py` | 주가·환율·금리 조회 도구 3종(금융 에이전트가 사용) |
| `file_converter/` | pandoc 기반 변환 — `converter.py`(로직), `exceptions.py`, `tool.py`(LangChain `@tool`) |

## 리소스·정적 파일

| 경로 | 내용 |
|---|---|
| `app/resources/kbo.yaml` | KBO 에이전트의 생성·검증 프롬프트(코드 밖으로 외부화) |
| `app/memory/` | 금융 에이전트용 정적 데이터 — `tickers.json`(전체 종목), `featured.json`(프롬프트용 대표 종목), `aliases.json`(통칭→정식 명칭) |
| `app/static/index.html`, `styles.css`, `chat.js` | 채팅 UI(순수 HTML/CSS/JS, 에이전트 선택·SSE 파서·진행 로그 패널) |
| `app/static/vendor/` | 마크다운 렌더링용 `marked`, 정제용 `DOMPurify`(번들된 서드파티 파일) |

## 루트 설정

| 경로 | 내용 |
|---|---|
| `pyproject.toml`, `uv.lock` | 의존성(uv), ruff·pyrefly 설정 |
| `.env.example` | 필요한 환경변수 목록 — 복사해서 `.env`로 채울 것([README.md](../README.md) 환경변수 표 참고) |
| `.gitignore` | `.venv/`, `__pycache__/`, `.env` 등 커밋 제외 |
| `.pre-commit-config.yaml` | ruff, pyrefly, 개인 키 탐지(`detect-private-key`) 등 커밋 전 검사 |
| `.github/workflows/ci.yml` | PR·`main` push 시 import 확인 + pyrefly 타입 체크 |
| `src/lg_cns_aicampus/` | `uv` 패키지 스캐폴드(빈 `__init__.py`, 앱 코드는 `app/`에 있음) |
| `tests/` | 비어 있음 — 자동 테스트 없음 |
