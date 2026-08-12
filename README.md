# 뉴스봇 (LG CNS AI 캠퍼스 팀 프로젝트, 가제)

특정 카테고리 뉴스를 추출해 중복 없이 AI로 요약한 TOP5를 보여주는 서비스. 2주차(8/10~8/14) 5일간 4인 팀으로 진행.

> ⚠️ 주제·구조는 모두 초안(Draft v0.1) — 팀 논의로 계속 바뀔 수 있음. 설계 배경·근거는 [docs/prd.md](docs/prd.md) 참고.

## 빠른 시작

```bash
uv sync --dev
pre-commit install
cp .env.example .env   # OPENAI_API_KEY, NAVER_CLIENT_ID/SECRET, LANGCHAIN_API_KEY 채우기
uv run uvicorn app.main:app --reload
```

`.env`는 `.gitignore`로 이미 막혀 있음 — 절대 커밋하지 말 것.

## 폴더 구조

```
app/
├── main.py              # FastAPI 진입점, 라우터 등록
├── routers/              # 엔드포인트(HTTP 계층) — 요청 검증 + 서비스 호출만
│   └── news.py           # GET /news/{category}, POST /news/search, GET /news/{category}/stream
├── services/              # 비즈니스 로직 — 카테고리별 개별 처리 + 공통 파이프라인
│   ├── categories.py      # handle_정치/handle_경제/handle_it/handle_스포츠 (개별 구현)
│   ├── naver_news.py      # 네이버 뉴스 API 호출
│   ├── dedup.py           # 중복 기사 제거(공통)
│   └── summarize.py       # AI 요약(공통, Pydantic 구조화 출력)
├── tools/                 # LLM 도구 정의(Function Calling 기반 카테고리 라우팅)
│   └── category_tools.py
└── schemas/                # Pydantic 스키마
    └── news.py             # NewsItem / NewsResponse
```

역할별로 건드리는 폴더가 자연스럽게 나뉘도록 구성:
- **구현 리드**: `app/main.py`, `app/routers/`, `app/services/naver_news.py`, `app/services/dedup.py`, `app/tools/`
- **프롬프트·기획**: `app/services/summarize.py`(RCIF 프롬프트), `app/schemas/news.py`
- **팀원 4명**: `app/services/categories.py`의 `handle_정치()`/`handle_경제()`/`handle_it()`/`handle_스포츠()` 각 1개씩 담당
- **테스트·QA·발표**: 엣지케이스 테스트 + 데모 스크립트

## 도구 (Tools)

- `app/tools/file_converter/` — 문서 포맷 변환 도구(pandoc 기반). `POST /tools/file-converter/convert`(파일 업로드 + `target_format`), `GET /tools/file-converter/formats`(지원 포맷 목록)
  - 지원 포맷: docx, html, md, odt, rtf, pptx, epub, rst, txt
  - **PDF는 지원하지 않음** — pandoc이 PDF를 입력으로 읽지 못하고(리더 없음), 출력하려면 LaTeX 등 별도 엔진이 추가로 필요해 스코프에서 제외
  - 로컬 실행 전 `brew install pandoc` 필요(시스템 바이너리)
  - 사용 예시(curl, Python 호출 등)는 [docs/07_usage.md](docs/07_usage.md) 참고

## 설계 문서

- [docs/prd.md](docs/prd.md) — 한 문장 정의, MVP 범위, 기능/비기능 요구사항, 데이터 흐름(mermaid), 리스크
- [docs/architecture.md](docs/architecture.md) — 라우팅 설계(도구 선택 + 개별 분기 처리) 상세, 작업 분할 전략
- [docs/navigation.md](docs/navigation.md) — 파일별 담당자·역할 한눈에 보기
- [docs/presentation.md](docs/presentation.md) — 미니프로젝트 발표 준비 자료
- [docs/branching.md](docs/branching.md) — 브랜치 규칙, PR·리뷰 흐름, AI 협업 시 유의사항
- [docs/multi-agent.md](docs/multi-agent.md) — (초안, 스프린트 범위 밖) 메인/서브 에이전트 오케스트레이션 패턴 검토 메모
- [docs/07_usage.md](docs/07_usage.md) — file-converter·채팅 UI 사용 설명(curl 예시, Python 호출법)

## 필수요건 6종 체크리스트 (Day5 교안 기준)

- [ ] FastAPI 엔드포인트 2개 이상
- [ ] 프롬프트 템플릿(하드코딩 금지)
- [ ] Pydantic 구조화 출력 1곳 이상
- [ ] SSE 스트리밍 엔드포인트
- [ ] LangSmith 트레이스 링크
- [ ] `.env` 기반 키 관리


                            User Question
                                   ↓
                      ┌────────────────────────┐
                      │        Main LLM        │
                      │                        │
                      │  질문 이해 / 라우팅        │
                      │  Tool 선택 / 결과 취합     │
                      └───────────┬────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ↓                   ↓                   ↓
    ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
    │   Tech LLM Tool  │ │  Code LLM Tool   │ │ General LLM Tool │
    │                  │ │                  │ │                  │
    │ 기술 질문 전문      │  │ 코드 분석/생성      │ │ 일반 질의/요약      │
    └─────────┬────────┘ └──────────────────┘ └──────────────────┘
              │
              │
              │     ※ Tech LLM Tool 상세 구조
              ↓
    ┌──────────────────────────────┐
    │          Tech LLM            │
    │                              │
    │ 기술 질문 분석 / 작업 계획        │
    │ 필요한 정보·Tool 결정            │
    └──────────────┬───────────────┘
                   ↓
          ┌──────────────────┐
          │   Tool Router    │
          └────────┬─────────┘
                   │
        ┌──────────┼───────────┐
        │          │           │
        ↓          ↓           ↓
 ┌────────────┐ ┌────────────┐ ┌────────────┐
 │ Web Search │ │  YouTube   │ │    News    │
 │    Tool    │ │ Search Tool│ │ Search Tool│
 └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
       │              │              │
       └──────────────┼──────────────┘
                      ↓
             ┌──────────────────┐
             │ Retrieval        │
             │ Evaluator LLM    │
             │                  │
             │ 검색 결과 평가      │
             └────────┬─────────┘
                      ↓
                정보가 충분한가?
                  ↙          ↘
                NO            YES
                ↓              ↓
       ┌────────────────┐  ┌────────────────┐
       │ Query Rewriter │  │ Answer LLM     │
       │      LLM       │  │                │
       │                │  │ 검색 결과 기반     │
       │ 검색어 개선       │  │ 답변 생성        │
       └───────┬────────┘  └───────┬────────┘
               │                   │
               └─→ Tool 재호출      ↓
                            ┌────────────────┐
                            │ Answer         │
                            │ Evaluator LLM  │
                            │                │
                            │ 답변 품질 평가    │
                            └───────┬────────┘
                                    ↓
                              답변이 적절한가?
                                ↙         ↘
                              NO           YES
                              ↓             ↓
                       ┌─────────────┐   Tech LLM
                       │ Answer      │      ↓
                       │ Rewriter    │   Main LLM
                       └──────┬──────┘      ↓
                              │         User Response
                              └────→ 재평가
