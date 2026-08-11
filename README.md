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

메인 에이전트가 카테고리별 서브 에이전트를 도구로 동시 호출하는 멀티 에이전트 구조로 전환됨(설계는 [docs/multi-agent.md](docs/multi-agent.md), 상세는 [docs/architecture.md](docs/architecture.md) 참고):

```
app/
├── main.py                 # FastAPI 진입점 (예정)
├── setting.py               # 환경변수(.env) 로드 — pydantic-settings
├── llms/
│   ├── agent.py              # Agent/SubLLM/MainLLM 베이스 클래스
│   ├── main_agent.py          # MainAgent — 서브 에이전트 동시 호출·히스토리(메모리)·스트리밍 오케스트레이터
│   └── sub_agents.py           # 카테고리별 서브 에이전트: 경제/개발 + 야구·건강(택1, 한 명 담당)
└── schemas/                  # Pydantic 스키마 (예정)
```

역할별로 건드리는 파일이 자연스럽게 나뉘도록 구성:
- **메인 에이전트 담당**: `app/llms/agent.py`, `app/llms/main_agent.py`
- **서브 에이전트(카테고리별) 담당**: `app/llms/sub_agents.py`의 `BusinessAgent`(경제)/`DevelopmentAgent`(개발) 각 1개씩 + `BaseballAgent`(야구) 또는 `HealthAgent`(건강) 중 택1을 한 명이 담당
- **설정·환경변수**: `app/setting.py`
- **테스트·QA·발표**: 엣지케이스 테스트 + 데모 스크립트

## 설계 문서

- [docs/prd.md](docs/prd.md) — 한 문장 정의, MVP 범위, 기능/비기능 요구사항, 데이터 흐름(mermaid), 리스크
- [docs/architecture.md](docs/architecture.md) — 메인/서브 에이전트 오케스트레이션 설계, 작업 분할 전략
- [docs/multi-agent.md](docs/multi-agent.md) — 메인/서브 에이전트 오케스트레이션 패턴 원안(금리/부동산 예시로 정리) — 실제 채택된 방향
- [docs/navigation.md](docs/navigation.md) — 파일별 담당자·역할 한눈에 보기
- [docs/presentation.md](docs/presentation.md) — 미니프로젝트 발표 준비 자료
- [docs/branching.md](docs/branching.md) — 브랜치 규칙, PR·리뷰 흐름, AI 협업 시 유의사항

## 필수요건 6종 체크리스트 (Day5 교안 기준)

- [ ] FastAPI 엔드포인트 2개 이상
- [ ] 프롬프트 템플릿(하드코딩 금지)
- [ ] Pydantic 구조화 출력 1곳 이상
- [ ] SSE 스트리밍 엔드포인트
- [ ] LangSmith 트레이스 링크
- [ ] `.env` 기반 키 관리
