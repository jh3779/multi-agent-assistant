# 파일 네비게이션

레포 안의 모든 파일이 어디 있고 무엇을 하는 자리인지 한눈에 보기 위한 지도. 설계 배경은 [prd.md](prd.md), 라우팅·작업분할 상세는 [architecture.md](architecture.md) 참고.

## 문서

| 경로 | 내용 |
|---|---|
| `README.md` | 프로젝트 개요, 빠른 시작, 폴더 구조, 필수요건 6종 체크리스트 |
| `docs/prd.md` | 한 문장 정의, 문제/목표, MVP 범위(MoSCoW), 기능·비기능 요구사항, 로드맵, 리스크 |
| `docs/architecture.md` | 카테고리 라우팅 설계(도구 선택+개별 분기, mermaid), 작업 분할 전략, 역할분담표 |
| `docs/presentation.md` | 미니프로젝트 발표 준비 — 주제 선정 배경/6요소 설계/진행 내용/구현 방식(소통·역할분담) |
| `docs/navigation.md` | 이 문서 |

## 코드 (`app/`)

| 경로 | 이 파일이 하는 일 | 담당 |
|---|---|---|
| `app/main.py` | FastAPI 진입점 — dotenv 로드, 라우터 등록 | 구현 리드 |
| `app/routers/news.py` | 엔드포인트(HTTP 계층) — `GET /news/{category}`, `POST /news/search`, `GET /news/{category}/stream` | 구현 리드 |
| `app/tools/category_tools.py` | 카테고리 라우팅 도구 — LLM 도구 선택(Function Calling)용 `@tool` 4개(정치/경제/IT/스포츠) | 구현 리드 |
| `app/services/naver_news.py` | 네이버 뉴스 API 호출(공통) — 오늘자 기사 조회 | 구현 리드 |
| `app/services/dedup.py` | 중복 기사 제거(공통) — 제목 유사도 기준 | 구현 리드 |
| `app/services/summarize.py` | AI 요약(공통) — RCIF 프롬프트 템플릿 + Pydantic 구조화 출력 | 프롬프트·기획 |
| `app/schemas/news.py` | Pydantic 스키마 — `NewsItem`(title/press/summary/url), `NewsResponse`(category/items[]) | 프롬프트·기획 |
| `app/services/categories.py` | 카테고리별 개별 처리 — `handle_정치`/`handle_경제`/`handle_it`/`handle_스포츠`(담당자 자율 선택) | 팀원 4명 |
| `tests/` | 엣지케이스 테스트(기사 0건·중복 과다·모호한 카테고리), 데모 스크립트 | 테스트·QA·발표 |

## 설정

| 경로 | 내용 |
|---|---|
| `requirements.txt` | 의존 패키지 목록 |
| `.env.example` | 필요한 환경변수 목록(`OPENAI_API_KEY`, `NAVER_CLIENT_ID/SECRET`, `LANGCHAIN_*`) — 복사해서 `.env`로 채울 것 |
| `.gitignore` | `.venv/`, `__pycache__/`, `.env` 등 커밋 제외 목록 |

## 아직 없는 것 (필요해지면 추가)

- `app/schemas/news.py` 외 추가 ERD/DB 모델 — MVP는 무상태(in-memory)라 당장은 불필요(prd.md 12번 참고)
- 프론트엔드 — 스코프 가드레일상 이번 블록은 터미널/curl/`/docs`로 대체
