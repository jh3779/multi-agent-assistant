# PRD — LG CNS AI 캠퍼스 팀 프로젝트 (도구 모음)

작성일: 2026-08-07 / 개정: 2026-11-26
상태: v0.3 — v0.2(2026-08-12)의 방향(독립 에이전트를 하나의 FastAPI 앱으로 연결)은 그대로 두고, 이후 병합된 Tech·금융 에이전트와 채팅 UI 에이전트 선택을 반영해 현재 `main` 코드와 맞췄다
범위: 팀원별 독립 LLM 도구/에이전트를 하나의 FastAPI 앱에 라우터로 모아 제공

> 이 문서는 v0.1(뉴스봇 PRD)을 대체한다. 현재 구조는 [architecture.md](architecture.md), 파일별 역할은 [navigation.md](navigation.md)에 있다. 아래 3·6절의 목표·지표와 11절 진행 경과는 당시 계획(8/14 발표 기준)을 보존한 기록이다.

## 1. 한 문장 정의

팀원 각자가 독립적으로 만든 LLM 도구/에이전트(문서 변환, KBO 야구 Q&A 등)를 하나의 FastAPI 앱에 라우터로 모아 제공하는 팀 프로젝트다.

## 2. 배경

- LG CNS AI 캠퍼스 과정 2주차(8/10~8/14) 5일간 4인 팀으로 진행하는 팀 프로젝트.
- **v0.1(2026-08-07)**: "뉴스봇" — 카테고리 기반 네이버 뉴스 수집 + 중복 제거 + AI 요약 TOP5. 이후 팀 논의로 폐기됨.
- **중간 검토안**: Main LLM이 Tech/Code/General 등 여러 하위 LLM Tool을 라우팅하는 멀티 에이전트 오케스트레이션 구조(설계 노트: [multi-agent.md](multi-agent.md)). PR #5("WIP 예고: 메인 에이전트 초안")로 시도됐으나 최종 채택되지 않고 CLOSED됨.
- **현재(v0.2) 확정 방향**: 중앙 오케스트레이터 없이, 팀원 각자가 독립된 도구/에이전트를 자기 브랜치에서 만들어 PR로 병합하고, `app/main.py`에 라우터로 등록해 하나의 FastAPI 앱으로 합친다("각자 API 만들어서 FastAPI로 연결").
- 공통 베이스 클래스(`app/llms/agent.py`의 `Agent(ABC)`, `app/tools/base.py`의 `BaseTool`)만 팀 공용으로 유지하고, 그 위에서 각자 자기 담당 도구를 독립 구현한다.

## 3. 문제와 목표

### 문제

도구별로 해결하는 문제가 다르다 — 더 이상 하나의 문제 정의로 묶이지 않는다.

- **file-converter**: 문서 포맷을 바꾸려면 매번 별도 프로그램/웹사이트를 거쳐야 해 번거롭다.
- **KBO 에이전트**: 최신 KBO 순위·경기 결과·일정처럼 시의성이 중요한 정보를 LLM이 사전 지식만으로 답하면 오래된 정보이거나 환각(hallucination)일 위험이 크다.
- **Tech 에이전트**: 기술 질문에 출처 없는 답변이 나오면 신뢰하기 어렵다 — 웹 검색 근거와 출처를 붙이고 답변 품질을 검증한다.
- **금융 에이전트**: 주가·환율·금리는 실시간 값이 필요해 LLM 사전 지식으로는 답할 수 없다 — 조회 도구로 값을 가져와 답변하고 평가한다.
- **팀 공통**: 5일 스프린트에서 4인이 각자 실제로 동작하는 LLM 도구를 만들어, 과정에서 요구하는 필수요건 6종을 팀 전체로 채워야 한다.

### 목표

- 팀원 각자 최소 1개 이상의 실제 동작하는 LLM 도구/에이전트를 완성해 FastAPI 앱에 라우터로 연결한다.
- 필수요건 6종(엔드포인트 2개 이상·프롬프트 템플릿·Pydantic 구조화 출력·SSE 스트리밍·LangSmith 트레이스·`.env` 키 관리)을 팀 전체 관점에서 모두 충족한다.
- 8/14 발표에서 각자 담당 도구를 실제로 시연 가능한 상태로 만든다.

## 4. 사용자와 사용 맥락

| 사용자 | 맥락 | 필요 |
|---|---|---|
| 문서 변환이 필요한 사용자 | 보고서·자료를 다른 포맷(docx↔html 등)으로 바꿔야 함 | 빠르고 정확한 변환, 다양한 포맷 지원 |
| KBO 야구 소식이 궁금한 사용자 | 최신 순위·경기 결과·일정을 확인하고 싶음 | 최신 정보에 근거한, 신뢰할 수 있는 답변 |
| 팀 프로젝트 발표 청중(강사·동료) | "이게 왜 흥미로운가"를 짧게 이해하고 싶음 | 각 도구의 명확한 스코프 + 실제 동작하는 데모 |

## 5. 핵심 가치

1. **독립성** — 팀원 각자 자기 도구를 독립적으로 설계·구현·배포할 수 있다(Main Agent 의존 없음, 한 사람이 막히면 다른 사람도 막히는 구조를 피함).
2. **최소한의 공통 기반** — `Agent(ABC)`/`BaseTool` 베이스 클래스로 도구 간 최소 일관성만 확보하고, 그 이상은 강제하지 않는다.
3. **실동작 검증** — 각 도구는 목(mock)이 아니라 실제 LLM 호출로 end-to-end 검증한다(예: `FileConverterAgent.astream()`, `KBOAgent.ainvoke()` 모두 실제 API 키로 검증됨).

## 6. 성공 지표

| 지표 | 목표(MVP 기준) |
|---|---|
| 완성된 도구/에이전트 수 | 4인 중 최소 3개 이상 실동작 |
| 필수요건 6종 충족 | 팀 전체 기준으로 6종 모두 최소 한 곳 이상에서 충족 |
| PR 리뷰·병합 | 8/14 발표 전 열려 있던 PR(당시 #6, #7) 최소 1회 리뷰 후 병합 — 결과: 두 PR은 닫히고 통합 브랜치 PR #8로 병합됨(11절) |
| file-converter 변환 정확도 | 지원 포맷 9종 왕복 테스트에서 한글/다국어 문자 깨짐 없음(회귀 방지, [07_usage.md](07_usage.md) 참고) |
| KBO 에이전트 응답 신뢰도 | 검증(validation) 단계에서 근거 없는 주장 발견 시 자동 재작성(correction) 경로 통과 |

## 7. MVP 범위

**완료**
- file-converter 도구 — HTTP API(`POST /tools/file-converter/convert`, `GET /tools/file-converter/formats`) + LangChain `@tool` 함수(`file_converter`) 두 형태로 제공.
- 채팅 UI(`app/static/`) — 다크모드, 에이전트 선택 버튼(파일 변환·KBO·Tech·금융), 파일 드래그·업로드·변환, 도구 호출 상태·에이전트 진행 로그 표시.
- 공통 베이스 클래스 — `Agent(ABC)`(`app/llms/agent.py`), `BaseTool`(`app/tools/base.py`). 4개 에이전트 모두 `Agent`를 상속한다.
- KBO 에이전트 — 웹 검색(Tavily) + 날짜 도구, 답변 생성→검증→(필요 시) 수정 루프, `POST /kbo/invoke`·`POST /kbo/stream`.
- Tech 에이전트 — 웹 검색 기반 답변과 출처, 답변 품질 검증, `POST /tech/stream`(SSE).
- 금융 에이전트(`BusinessAgent`) — 주가·환율·금리 도구 + 웹 검색, 답변 작성→평가→재작성, `POST /finance/ask`·`GET /finance/stream`(SSE).
- 채팅 UI ↔ 실제 LLM 백엔드 연결 — 프론트 검증용이던 목(mock, `chat_mock.py`)을 폐기하고 `POST /chat`이 `FileConverterAgent`를 실제로 호출한다. 단 채팅 텍스트는 파일 경로를 안 보내므로 일반 질문에만 답하고, 실제 파일 변환은 드래그앤드롭 전용.

**미정**
- 자동 테스트 — 현재 `tests/`가 비어 있고 CI는 import 확인과 타입 체크만 수행한다.

**Won't (스코프 제외, 팀 결정으로 폐기)**
- Main LLM이 하위 Tool을 라우팅하는 오케스트레이션 계층.
- 뉴스봇 관련 기능 전체(네이버 뉴스 API 연동, 카테고리별 TOP5 요약 등) — 주제 자체가 폐기됨.

## 8. 기능 요구사항

| ID | 요구사항 |
|---|---|
| FR-CONV-001 | `file_converter`가 docx/html/md/odt/rtf/pptx/epub/rst/txt 간 변환을 지원한다(PDF 미지원 — pandoc이 PDF를 입력으로 읽지 못함) |
| FR-CONV-002 | 변환 기능을 HTTP API(`POST /tools/file-converter/convert`)와 LangChain `@tool` 함수(`file_converter`, `bind_tools()`로 LLM에 노출 가능) 두 경로로 제공한다 |
| FR-CONV-003 | 업로드 파일 경로는 허용 디렉터리(`ALLOWED_DIR`) 밖을 벗어날 수 없다(경로 탈출 방지), 업로드 크기 상한(20MB)을 둔다 |
| FR-KBO-001 | `POST /kbo/invoke`(완성 답변)와 `POST /kbo/stream`(스트리밍)이 자연어 질문을 받아 KBO 관련 답변을 반환한다 |
| FR-KBO-002 | 시의성 정보(순위/일정/결과 등)가 필요하면 에이전트가 자율적으로 웹 검색(Tavily) 도구를 호출해 근거를 수집한다 |
| FR-KBO-003 | 초안 답변을 별도 검증(validation) LLM 호출로 사실관계·날짜 일관성을 점검하고, 불합격 시 근거에 기반해 자동으로 다시 작성(correction)한다 |
| FR-BASE-001 | 팀 공용 `Agent(ABC)`가 `create_system_prompt`/`create_human_prompt`/`create_workflow`/`answer_validation`/`astream` 추상 메서드를 정의해, 각 도구가 최소한의 동일한 인터페이스를 따르도록 한다. `FileConverterAgent`가 첫 실제 구현체(`app/llms/file_converter_agent.py`) — `astream`이 `AsyncIterator[str]`만 반환할 수 있어 변환된 파일 바이트(artifact)는 반환값이 아니라 `self.memory["artifacts"]`에 담아 호출자가 실행 후 꺼내 쓰게 함. KBO·Tech·금융 에이전트도 모두 이 베이스를 상속한다 |
| FR-BASE-002 | 팀 공용 `BaseTool`이 `settings`(API 키 등)를 공유해, 각 도구가 설정 로딩을 중복 구현하지 않게 한다 |
| FR-TECH-001 | `POST /tech/stream`이 기술 질문을 받아 웹 검색 근거와 출처를 포함한 답변을 SSE로 스트리밍하고, 답변 품질 검증을 거친다(`TechAgentResponse.status`: success·unsupported·insufficient_sources·validation_failed) |
| FR-FIN-001 | `POST /finance/ask`(완성 답변)와 `GET /finance/stream`(SSE)이 금융 질문에 주가·환율·금리 조회 도구와 웹 검색으로 답하고, 평가 단계에서 불합격이면 재작성한다 |
| FR-CHAT-002 | 채팅 UI는 에이전트 선택 버튼(파일 변환·KBO·Tech·금융)으로 요청을 해당 에이전트 엔드포인트로 보낸다. 서버 측 라우팅은 없다 |
| FR-CHAT-001 | `POST /chat`(`app/routers/chat.py`)이 `FileConverterAgent.astream()`을 SSE(`text/event-stream`)로 노출한다. 이벤트 계약(`tool_start`/`tool_end`/`answer_chunk`/`done`)은 폐기된 목(mock)과 동일하게 맞춰 프론트(`chat.js`) 수정 없이 재사용한다. 채팅 텍스트는 파일 경로를 같이 보내지 않으므로, 실제 파일 변환 요청이 아니라 일반 질문에 답하는 용도로만 쓰인다 |
| FR-008 | API 키(OpenAI, Tavily 등)는 `.env`로 관리하고 저장소에 커밋하지 않는다 |

## 9. 비기능 요구사항

- **비밀 정보 보호**: OpenAI/Tavily 등 API 키는 `.env`로만 관리, 저장소에 커밋 금지.
- **독립 배포 가능성**: 한 도구의 실패·지연이 다른 도구의 엔드포인트에 영향을 주지 않아야 한다(중앙 오케스트레이터가 없으므로 자연히 만족되지만, 공용 `app/main.py`/`app/setting.py` 변경 시에는 회귀 여부를 확인해야 한다).
- **재현 가능성**: KBO 에이전트처럼 LLM 호출이 있는 도구는 `temperature`를 낮게 유지해 같은 질문에 유사한 결과가 나오게 한다.
- **응답 시간·비용**: 도구별로 특성이 달라(예: file-converter는 로컬 pandoc 실행, KBO 에이전트는 LLM+웹검색 다회 호출) 공통 목표치를 아직 정하지 않음 — 도구별 실측 후 각자 문서([07_usage.md](07_usage.md), [presentation.md](presentation.md))에 기재.

## 10. 주요 플로우

### FLOW-CONV-001 · 문서 변환

```
파일 업로드(HTTP) 또는 LLM tool_call
→ 허용 디렉터리 내 경로인지 검증
→ pandoc 기반 변환(app/tools/file_converter/converter.py)
→ 지원하지 않는 포맷 → 400, 타임아웃(30초) → 504
→ 변환된 파일 반환(다운로드) 또는 ToolMessage(content+artifact)로 LLM에 반환
```

### FLOW-KBO-001 · KBO 질의응답

```
사용자 질문(POST /kbo/invoke 또는 /kbo/stream)
→ 모델이 필요 시 web_search/date_time 도구를 자율 호출(최대 5회 반복)
→ 도구 결과를 근거(evidence)로 모아 초안 답변 생성
→ 검증 LLM이 사실관계·날짜 일관성 점검(Pydantic ValidationResult)
→ 불합격 시 근거 기반으로 답변 재작성 → 합격 시 그대로 반환
→ 최종 답변 응답
```

### FLOW-CHAT-001 · 채팅 UI 텍스트 메시지

```
사용자 텍스트 입력(POST /chat)
→ FileConverterAgent.astream(message) 호출
→ 도구 호출 여부 판단(Function Calling) — file_path가 없으므로 보통 미호출
→ (도구를 썼다면) tool_start/tool_end SSE 이벤트 먼저 전송
→ 완성된 답변을 answer_chunk 이벤트로 전송(현재는 한 번에 통짜로)
→ done 이벤트로 스트림 종료
```

## 11. 진행 경과

과거 버전(v0.1)의 "커리큘럼 로드맵"은 뉴스봇 전제라 더 이상 맞지 않아 제거하고, 실제 진행 경과로 대체한다.

| 일자 | 내용 |
|---|---|
| 2026-08-07 | "뉴스봇" 주제로 PRD v0.1 작성(Draft) |
| 2026-08-10 | 브랜치 규칙(PR #1), 최소 CI(PR #2), 멀티 에이전트 설계 노트(PR #3), uv 세팅 정리(PR #4) 병합 |
| 2026-08-11 | Main Agent 초안 PR #5 CLOSED(오케스트레이션 방향 폐기 확정), file-converter + 채팅 UI PR #6 OPEN |
| 2026-08-12 | KBO 에이전트 PR #7 OPEN, 본 PRD v0.2로 재작성 |
| 2026-08-14 | file-converter·KBO·Tech·금융 에이전트를 모은 통합 브랜치(`integration/file-converter-kbo-agent`)가 PR #8로 `main`에 병합됨. PR #6·#7은 CLOSED(통합 브랜치로 흡수) |
| 2026-11-26 | 문서를 현재 `main` 코드 기준으로 정합(PRD v0.3, README·architecture·navigation 재작성) |

## 12. 데이터 모델

ERD 없음(DB 연동 없이 무상태 처리). 도구별 Pydantic 스키마:

- `app/schemas/file_converter.py` — `FileConverterArgs`(file_path, target_format), `FileConversionAnswer`(used_tool, tool_name, summary)
- `app/schemas/kbo.py` — `KBORequest`(query), `KBOResponse`(answer), `ValidationResult`(is_valid, reason, correction)
- `app/schemas/tech.py` — `TechQuestionRequest`, `TechAnswer`(topic, answer, example, sources), `TechAgentResponse`(status 등), `TechStreamEvent`
- `app/schemas/finance.py` — `FinanceQuestionRequest`, `FinanceAnswerResponse`, `FinanceStreamEvent`(type: answer·done·error)
- `app/schemas/evaluation.py` — `AnswerEvaluation`(금융 에이전트 답변 평가의 구조화 출력)

## 13. 제약과 정책

- DB 연동·사용자 인증·클라우드 배포는 이번 블록 범위 밖(스코프 가드레일) — 각각 in-memory, 인증 없음, 로컬 uvicorn으로 대체한다.
- 각 도구는 독립 브랜치에서 개발하고 PR로 병합한다([branching.md](branching.md) 참고). `main`에는 보호 규칙이 걸려 있다 — CI `test` 통과 필수(브랜치가 최신이어야 함), 관리자에게도 적용, force-push·브랜치 삭제 금지. 리뷰 승인은 필수로 설정되어 있지 않다([branching.md](branching.md) 참고).
- Main LLM 오케스트레이션은 채택하지 않는다 — 도구 간 라우팅이 필요해지면 그때 별도로 재검토한다.

## 14. 리스크와 완화책

| 리스크 | 완화책 |
|---|---|
| 자동 테스트가 없어(`tests/` 비어 있음) 회귀를 사람이 직접 확인해야 한다 | CI의 import 확인·pyrefly와 pre-commit(ruff·pyrefly)이 최소 방어선. 에이전트별 최소 회귀 테스트 추가는 미정 |
| 에이전트마다 SSE 프레임 형식이 달라 프론트(`chat.js`)가 파서를 따로 둔다 | 형식 차이를 [architecture.md](architecture.md) 스트리밍 표에 기록. 새 에이전트를 붙일 때 이 표를 갱신 |
| 상태를 인스턴스에 들고 있는 에이전트(`BusinessAgent`)를 공유하면 요청 간 상태가 섞인다 | `app/dependencies.py`가 요청마다 새 인스턴스를 만든다 |
| LLM 자기검증 단계가 오판할 수 있다(검증 LLM이 근거보다 자기 사전 지식을 우선하는 경우) | KBO·Tech·금융 모두 검증/평가 단계를 두고 있으나, 검증 결과의 정확도는 따로 측정하지 않았다 |
| API 키가 저장소에 들어갈 위험 | `.env`는 `.gitignore`로 제외, pre-commit `detect-private-key` 적용 |

## 15. Open Questions

- "뉴스봇" 대체 프로젝트명을 새로 정할지, 아니면 "도구 모음" 형태로 계속 갈지?
- 에이전트별 최소 회귀 테스트를 추가할지? (현재 자동 테스트 없음)
- `app/setting.py`에 남은 `naver_client_id/secret`, `youtube_api_key`는 현재 코드에서 쓰이지 않는다 — 제거할지?
- `docs/superpowers/specs/`의 YouTube 도구 설계서 2건은 코드에 구현되지 않았다 — 구현할지, 폐기할지?

과거 질문의 처분: business-agent는 금융 에이전트로 구현되었고, KBO 에이전트는 `Agent(ABC)`를 상속하도록 통일되었으며, 채팅 UI는 에이전트 선택 버튼으로 여러 에이전트를 쓴다(서버 측 라우팅 계층은 두지 않음). `architecture.md`는 현재 구조로 다시 썼다.

## 16. 향후 확장 후보

- 도구가 여러 개로 늘어나 사용자가 직접 고르기 번거로워지면, 그때 가벼운 라우팅 계층 재검토(현재는 폐기 상태).
- KBO 에이전트에 통계·일정 전용 API(공식 KBO API 등) 연동으로 웹 검색 의존도 낮추기.
- file-converter의 pandoc 서브프로세스를 스레드 대신 `asyncio.create_subprocess_exec`로 바꿔 타임아웃 시 실제 프로세스 강제 종료 지원(현재는 `asyncio.wait_for`가 대기만 포기하고 스레드는 못 죽임).

## 17. 완료 기준 (MVP)

- [x] file-converter, KBO, Tech, 금융 에이전트가 `main`에 병합되어 있다(PR #8, 2026-08-14)
- [x] 채팅 UI가 실제 백엔드에 연결되어 있고, 에이전트 선택 버튼으로 4개 에이전트를 호출한다(`app/static/chat.js`)
- [x] CI 동등 체크(import 확인, pyrefly, ruff)가 통과한다(2026-11-26 로컬 확인)
- [ ] 필수요건 6종 중 LangSmith 공유 트레이스 링크가 첨부된다([README.md](../README.md) 체크리스트 — 나머지 5종은 코드로 확인됨)
- [x] 본 PRD와 [README.md](../README.md), [architecture.md](architecture.md), [navigation.md](navigation.md)가 현재 코드와 일치한다(2026-11-26 정비)
