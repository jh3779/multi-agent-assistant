# PRD — LG CNS AI 캠퍼스 팀 프로젝트 (도구 모음)

작성일: 2026-08-07 / 개정: 2026-08-12
상태: Draft v0.2 — "뉴스봇" 단일 제품 컨셉과 Main Agent 오케스트레이션을 모두 폐기하고, 팀원 각자가 독립 도구/에이전트를 만들어 FastAPI로 연결하는 구조로 전면 재작성
범위: 팀원별 독립 LLM 도구/에이전트를 하나의 FastAPI 앱에 라우터로 모아 제공

> 이 문서는 v0.1(뉴스봇 PRD)을 대체한다. 라우팅 설계 문서([architecture.md](architecture.md))는 아직 v0.1 시절 "카테고리 라우팅" 설계를 담고 있어 이 버전과 맞지 않음 — 참고 시 주의.

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
| PR 리뷰·병합 | 8/14 발표 전 열려 있는 PR(현재 #6, #7) 최소 1회 리뷰 후 병합 |
| file-converter 변환 정확도 | 지원 포맷 9종 왕복 테스트에서 한글/다국어 문자 깨짐 없음(회귀 방지, [07_usage.md](07_usage.md) 참고) |
| KBO 에이전트 응답 신뢰도 | 검증(validation) 단계에서 근거 없는 주장 발견 시 자동 재작성(correction) 경로 통과 |

## 7. MVP 범위

**완료**
- file-converter 도구 — HTTP API(`POST /tools/file-converter/convert`, `GET /tools/file-converter/formats`) + LangChain `@tool` 함수(`file_converter`) 두 형태로 제공. PR #6 OPEN.
- 채팅 UI(`app/static/`) — 다크모드, 파일 드래그·업로드·변환, 도구 호출 상태 표시. PR #6 OPEN.
- 공통 베이스 클래스 — `Agent(ABC)`(`app/llms/agent.py`), `BaseTool`(`app/tools/base.py`). main 병합됨.
- KBO 에이전트 — 웹 검색(Tavily) + 날짜 도구, 답변 생성→검증→(필요 시) 수정 루프, `POST /kbo/query`. PR #7 OPEN.

**진행 중 / 미정**
- business-agent — 베이스 클래스를 상속할 준비만 된 스캐폴딩 상태, 실제 기능 미착수(담당자·범위 미정).
- 채팅 UI ↔ 실제 LLM 백엔드 연결 — 프론트 검증용이던 목(mock, `chat_mock.py`)을 폐기해 현재 `POST /chat`은 404. 어떤 백엔드(KBO 에이전트? 다른 도구? 라우팅 계층?)를 연결할지 담당·방식 모두 미정.

**Won't (스코프 제외, 팀 결정으로 폐기)**
- Main LLM이 하위 Tool을 라우팅하는 오케스트레이션 계층.
- 뉴스봇 관련 기능 전체(네이버 뉴스 API 연동, 카테고리별 TOP5 요약 등) — 주제 자체가 폐기됨.

## 8. 기능 요구사항

| ID | 요구사항 |
|---|---|
| FR-CONV-001 | `file_converter`가 docx/html/md/odt/rtf/pptx/epub/rst/txt 간 변환을 지원한다(PDF 미지원 — pandoc이 PDF를 입력으로 읽지 못함) |
| FR-CONV-002 | 변환 기능을 HTTP API(`POST /tools/file-converter/convert`)와 LangChain `@tool` 함수(`file_converter`, `bind_tools()`로 LLM에 노출 가능) 두 경로로 제공한다 |
| FR-CONV-003 | 업로드 파일 경로는 허용 디렉터리(`ALLOWED_DIR`) 밖을 벗어날 수 없다(경로 탈출 방지), 업로드 크기 상한(20MB)을 둔다 |
| FR-KBO-001 | `POST /kbo/query`가 자연어 질문을 받아 KBO 관련 답변을 반환한다 |
| FR-KBO-002 | 시의성 정보(순위/일정/결과 등)가 필요하면 에이전트가 자율적으로 웹 검색(Tavily) 도구를 호출해 근거를 수집한다 |
| FR-KBO-003 | 초안 답변을 별도 검증(validation) LLM 호출로 사실관계·날짜 일관성을 점검하고, 불합격 시 근거에 기반해 자동으로 다시 작성(correction)한다 |
| FR-BASE-001 | 팀 공용 `Agent(ABC)`가 `create_system_prompt`/`create_human_prompt`/`create_workflow`/`validate_tool_result`/`answer_validation`/`astream` 추상 메서드를 정의해, 각 도구가 최소한의 동일한 인터페이스를 따르도록 한다. `FileConverterAgent`가 첫 실제 구현체(`app/llms/file_converter_agent.py`) — `astream`이 `AsyncIterator[str]`만 반환할 수 있어 변환된 파일 바이트(artifact)는 반환값이 아니라 `self.memory["artifacts"]`에 담아 호출자가 실행 후 꺼내 쓰게 함. KBO 에이전트는 아직 이 베이스를 상속하지 않고 독립 클래스로 구현되어 있음 — 통일 여부는 Open Question |
| FR-BASE-002 | 팀 공용 `BaseTool`이 `settings`(API 키 등)를 공유해, 각 도구가 설정 로딩을 중복 구현하지 않게 한다 |
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
사용자 질문(POST /kbo/query)
→ 모델이 필요 시 web_search/date_time 도구를 자율 호출(최대 5회 반복)
→ 도구 결과를 근거(evidence)로 모아 초안 답변 생성
→ 검증 LLM이 사실관계·날짜 일관성 점검(Pydantic ValidationResult)
→ 불합격 시 근거 기반으로 답변 재작성 → 합격 시 그대로 반환
→ 최종 답변 응답
```

## 11. 진행 경과

과거 버전(v0.1)의 "커리큘럼 로드맵"은 뉴스봇 전제라 더 이상 맞지 않아 제거하고, 실제 진행 경과로 대체한다.

| 일자 | 내용 |
|---|---|
| 2026-08-07 | "뉴스봇" 주제로 PRD v0.1 작성(Draft) |
| 2026-08-10 | 브랜치 규칙(PR #1), 최소 CI(PR #2), 멀티 에이전트 설계 노트(PR #3), uv 세팅 정리(PR #4) 병합 |
| 2026-08-11 | Main Agent 초안 PR #5 CLOSED(오케스트레이션 방향 폐기 확정), file-converter + 채팅 UI PR #6 OPEN |
| 2026-08-12 | KBO 에이전트 PR #7 OPEN, 본 PRD v0.2로 재작성 |

## 12. 데이터 모델

ERD 없음(DB 연동 없이 무상태 처리). 도구별 Pydantic 스키마:

- `app/schemas/file_converter.py` — `FileConverterArgs`(file_path, target_format), `FileConversionAnswer`(used_tool, tool_name, summary)
- `app/schemas/kbo.py` — `KBORequest`(query), `KBOResponse`(answer), `ValidationResult`(is_valid, reason, correction)

## 13. 제약과 정책

- DB 연동·사용자 인증·클라우드 배포는 이번 블록 범위 밖(스코프 가드레일) — 각각 in-memory, 인증 없음, 로컬 uvicorn으로 대체한다.
- 각 도구는 독립 브랜치에서 개발하고 PR로 병합한다([branching.md](branching.md) 참고). main 브랜치는 현재 보호 규칙이 해제된 상태(팀 판단으로 계속 열어두기로 함).
- Main LLM 오케스트레이션은 채택하지 않는다 — 도구 간 라우팅이 필요해지면 그때 별도로 재검토한다.

## 14. 리스크와 완화책

| 리스크 | 완화책 |
|---|---|
| business-agent가 아직 스캐폴딩 단계라 발표 전 미완성일 위험 | 담당·범위를 조속히 확정 필요(Open Question), 최악의 경우 팀 전체 필수요건 6종은 file-converter+KBO 두 도구만으로도 채울 수 있는지 사전 점검 |
| 채팅 UI(`/chat`)가 어떤 백엔드에도 연결되지 않은 상태로 발표를 맞을 위험 | KBO 에이전트든 다른 도구든 최소 하나를 `/chat`에 연결하는 담당을 정해야 함 |
| PR #6, #7이 리뷰 없이 오래 열려 있을 위험 | 셀프 머지 금지 규칙 유지, 발표 전 최소 1회 상호 리뷰 후 병합 |
| main 브랜치 보호 규칙이 해제돼 있어 실수로 깨진 코드가 바로 반영될 위험 | 각자 로컬에서 pre-commit(ruff/pyrefly) 통과 후 푸시하는 관행 유지 |
| KBO 에이전트가 `Agent(ABC)` 공통 베이스를 상속하지 않아, 다른 도구와 인터페이스가 갈라질 위험 | 팀 논의로 통일할지, 도구별 자율성을 유지할지 결정 필요(Open Question) |

## 15. Open Questions

- business-agent의 실제 주제·범위·담당자는? (현재 스캐폴딩만 존재)
- 채팅 UI의 `/chat`을 어떤 백엔드(KBO 에이전트/다른 도구/신규 라우팅 계층)에 연결할지, 담당은 누구인지?
- "뉴스봇" 대체 프로젝트명을 새로 정할지, 아니면 "도구 모음" 형태로 계속 갈지?
- `architecture.md`(v0.1 카테고리 라우팅 설계)를 이 버전에 맞게 다시 쓸지, 폐기할지?
- KBO 에이전트를 공통 `Agent(ABC)` 베이스로 리팩터링할지, 독립 구현을 유지할지?
- PR #6(file-converter), #7(KBO 에이전트)의 리뷰·병합 일정은?

## 16. 향후 확장 후보

- 도구가 여러 개로 늘어나 사용자가 직접 고르기 번거로워지면, 그때 가벼운 라우팅 계층 재검토(현재는 폐기 상태).
- KBO 에이전트에 통계·일정 전용 API(공식 KBO API 등) 연동으로 웹 검색 의존도 낮추기.
- file-converter의 pandoc 서브프로세스를 스레드 대신 `asyncio.create_subprocess_exec`로 바꿔 타임아웃 시 실제 프로세스 강제 종료 지원(현재는 `asyncio.wait_for`가 대기만 포기하고 스레드는 못 죽임).

## 17. 완료 기준 (MVP)

- [ ] file-converter, KBO 에이전트가 실제 데이터로 동작하는 것을 시연한다(둘 다 실제 API 키 기준 검증 완료 — 배포/발표 환경에서 재확인 필요)
- [ ] business-agent의 범위가 확정되고 최소 기능이 구현된다
- [ ] 채팅 UI가 최소 하나의 실제 백엔드에 연결된다
- [ ] 필수요건 6종(엔드포인트 2개↑·프롬프트템플릿·Pydantic구조화·SSE스트리밍·LangSmith·`.env`)이 팀 전체 기준으로 모두 반영된다
- [ ] PR #6, #7이 리뷰를 거쳐 main에 병합된다
- [ ] 본 PRD와 팀 문서([navigation.md](navigation.md), [architecture.md](architecture.md), [presentation.md](presentation.md))가 실제 코드와 일치하는 상태로 정리된다(현재 architecture.md/navigation.md는 v0.1 기준으로 남아있어 갱신 필요)
