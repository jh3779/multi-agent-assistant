# Multi-Agent Assistant

LG CNS AI 캠퍼스 과정 2주차(8/10~8/14)에 4인 팀이 진행한 프로젝트입니다. 팀원이 각자 독립적으로 만든 LLM 에이전트(문서 변환 · KBO 야구 · 기술 Q&A · 금융)를 하나의 FastAPI 앱에 라우터로 모으고, 웹 채팅 UI에서 에이전트를 골라 쓰면서 도구 호출 과정을 실시간으로 볼 수 있게 한 프로젝트입니다.

> 처음엔 "뉴스봇"으로 시작했다가 팀 논의로 방향을 바꿨습니다. 변경 배경은 [docs/prd.md](docs/prd.md)와 [docs/presentation.md](docs/presentation.md)에 있습니다.

## 에이전트

| 에이전트 | 하는 일 | 엔드포인트 | 코드 |
|---|---|---|---|
| 파일 변환 | pandoc 기반 문서 포맷 변환(docx·html·md·odt·rtf·pptx·epub·rst·txt) | `POST /chat`, `POST /tools/file-converter/convert`, `GET /tools/file-converter/formats` | [app/llms/file_converter_agent.py](app/llms/file_converter_agent.py) |
| KBO | 웹 검색·날짜 도구로 근거를 모아 답변 → 검증 → 필요 시 수정 | `POST /kbo/invoke`, `POST /kbo/stream` | [app/llms/kbo.py](app/llms/kbo.py) |
| Tech | 웹 검색 기반 기술 질문 답변(출처 포함, 답변 품질 검증) | `POST /tech/stream` (SSE) | [app/llms/tech.py](app/llms/tech.py) |
| 금융 | 주가·환율·금리 조회 도구 + 웹 검색, 답변 작성 → 평가 → 재작성 루프 | `POST /finance/ask`, `GET /finance/stream` (SSE) | [app/llms/business_agent.py](app/llms/business_agent.py) |

공통으로 `/`(채팅 UI), `/health`, `/logs/stream`(서버 로그 SSE)을 제공합니다. 모든 에이전트는 공용 추상 클래스 `Agent(ABC)`([app/llms/agent.py](app/llms/agent.py))를 상속합니다. 자세한 구조는 [docs/architecture.md](docs/architecture.md)를 참고하세요.

## 빠른 시작

요구 사항: Python 3.14 이상, [uv](https://docs.astral.sh/uv/), 시스템 바이너리 `pandoc`(파일 변환용, macOS는 `brew install pandoc`).

```bash
uv sync --dev
pre-commit install
cp .env.example .env   # 아래 환경변수 채우기
uv run uvicorn app.main:app --reload
```

브라우저에서 http://127.0.0.1:8000 을 열면 채팅 UI가 뜹니다. API 문서는 `/docs`입니다.

### 환경변수

`.env`는 `.gitignore`로 제외되어 있으니 절대 커밋하지 마세요.

| 변수 | 용도 | 필요 여부 |
|---|---|---|
| `OPENAI_API_KEY` | 모든 에이전트의 LLM 호출(`gpt-4o-mini`) | 에이전트 사용 시 필수 |
| `TAVILY_API_KEY` | KBO·Tech·금융의 웹 검색 | KBO·Tech·금융 사용 시 필수 |
| `ECOS_API_KEY` | 금융 에이전트의 한국 기준금리 조회 | 선택 |
| `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` | LangSmith 트레이싱 | 선택 |

파일 변환 API(`/tools/file-converter/*`)는 API 키 없이도 동작합니다.

## 폴더 구조

```
app/
├── main.py              # FastAPI 진입점, 라우터 등록, 정적 파일 서빙
├── setting.py           # .env 기반 설정(pydantic-settings)
├── dependencies.py      # 의존성 주입(에이전트·서비스 생성)
├── routers/             # HTTP 계층 — 요청 검증 + 서비스 호출만
├── services/            # 에이전트 호출과 응답(SSE 등) 조립
├── llms/                # 에이전트 구현(Agent 추상 클래스 + 4개 에이전트)
├── tools/               # LLM 도구(웹 검색·날짜·금융·file_converter)
├── schemas/             # Pydantic 요청/응답·구조화 출력 스키마
├── resources/           # 외부화한 프롬프트(kbo.yaml)
├── memory/              # 금융 에이전트용 정적 데이터(티커·별칭)
└── static/              # 채팅 UI(순수 HTML/CSS/JS)
docs/                    # 설계·요구사항·사용 문서(아래 목록)
```

파일별 역할은 [docs/navigation.md](docs/navigation.md)에 있습니다.

## 문서

| 문서 | 내용 |
|---|---|
| [docs/prd.md](docs/prd.md) | 한 문장 정의, 범위, 요구사항, 진행 경과, 리스크 |
| [docs/architecture.md](docs/architecture.md) | 계층 구조, 에이전트별 파이프라인, SSE 이벤트 형식 |
| [docs/navigation.md](docs/navigation.md) | 파일별 역할 지도 |
| [docs/07_usage.md](docs/07_usage.md) | 채팅 UI·file-converter 사용법(curl, Python) |
| [docs/branching.md](docs/branching.md) | 브랜치 규칙, PR 흐름, `main` 보호 설정 |
| [docs/presentation.md](docs/presentation.md) | 발표 준비 자료(파일 변환 + 채팅 UI 담당 파트) |
| [docs/00_project_brief.md](docs/00_project_brief.md) ~ [docs/06_open_questions.md](docs/06_open_questions.md) | 채팅 UI 요구사항 인터뷰 정본(브리프·요구사항·UI 플로우·화면 계약·미결 질문) |
| [docs/multi-agent.md](docs/multi-agent.md) | (채택하지 않은) 메인/서브 에이전트 오케스트레이션 설계 메모 |

## 필수요건 체크리스트 (Day5 교안 기준)

팀 전체 기준으로 코드에서 확인한 결과입니다.

- [x] **FastAPI 엔드포인트 2개 이상** — 라우터 6개의 엔드포인트 9개 + `/`·`/health`([app/main.py](app/main.py)에서 등록)
- [x] **프롬프트 템플릿(하드코딩 금지)** — 에이전트별 `ChatPromptTemplate`/`SystemMessagePromptTemplate` 사용, KBO는 프롬프트를 [app/resources/kbo.yaml](app/resources/kbo.yaml)로 외부화
- [x] **Pydantic 구조화 출력 1곳 이상** — [app/llms/kbo.py](app/llms/kbo.py)(`ValidationResult`), [app/llms/tech.py](app/llms/tech.py)(`TechAgentResponse`), [app/llms/file_converter_agent.py](app/llms/file_converter_agent.py)(`FileConversionAnswer`), [app/llms/business_agent.py](app/llms/business_agent.py)(`AnswerEvaluation`)
- [x] **SSE 스트리밍 엔드포인트** — `POST /chat`, `POST /tech/stream`, `GET /finance/stream`, `GET /logs/stream`이 `text/event-stream`으로 응답(`/kbo/stream`은 `text/plain` 스트리밍)
- [x] **`.env` 기반 키 관리** — [app/setting.py](app/setting.py)가 `.env`를 읽고, `.env`는 [.gitignore](.gitignore)로 제외

## 알려진 한계

- 멀티턴 대화를 지원하지 않습니다. 요청마다 독립적으로 처리합니다(설계 결정, [docs/06_open_questions.md](docs/06_open_questions.md) DEC-001).
- PDF 변환은 지원하지 않습니다. pandoc이 PDF를 입력으로 읽지 못하고, 출력에는 별도 LaTeX 엔진이 필요해 범위에서 제외했습니다.
- 채팅 입력창은 파일 경로를 보내지 않습니다. 파일 변환은 채팅창으로 파일을 끌어다 놓는 별도 흐름으로 동작합니다.
- 자동 테스트가 없습니다(`tests/`는 비어 있음). CI는 import 확인과 타입 체크(pyrefly)만 수행합니다([.github/workflows/ci.yml](.github/workflows/ci.yml)).
- 로그인·인증이 없는 단일 사용자 로컬 실행을 전제로 합니다. 외부에 그대로 배포하는 용도가 아닙니다.

## 라이선스

[MIT](LICENSE)
