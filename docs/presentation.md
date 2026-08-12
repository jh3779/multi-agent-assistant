# 발표 준비 — AI 어시스턴트 미니프로젝트 (담당: 도구호출 + 웹 디자인)

관련 문서: [00_project_brief.md](00_project_brief.md), [01_requirements.md](01_requirements.md), [06_open_questions.md](06_open_questions.md)

> 8/14 발표 전까지 진행 내용에 맞춰 계속 갱신 필요. 이 문서는 팀 전체 발표 대본이 아니라 **내가 맡은 부분(file-converter 도구 + 채팅 UI)** 기준으로 작성 — 다른 담당자 파트는 각자 채워 넣어야 함.

## 1. 주제 선정 배경 (문제 상황 해결)

**원래 주제 → 방향 전환**

처음엔 "뉴스봇"(카테고리별 뉴스 요약)으로 시작했지만, 진행 중 팀이 방향을 바꿨다. 배경을 있는 그대로 말하는 게 낫다 — 숨기지 말고 "왜 바뀌었는지"를 설계 판단으로 설명한다.

1. 팀원(421079a)이 `Agent`/`SubLLM`/`MainLLM` → 통합 `Agent` 베이스 클래스를 만들면서, 카테고리 라우팅(정치/경제/IT/스포츠)보다 범용적인 **"Main LLM이 여러 Tool을 호출하는" 구조**로 자연스럽게 방향이 넓어짐
2. 팀 논의 끝에 **"각자 자기 도구(API)를 만들어서 FastAPI로 연결"**하는 방식으로 확정 — 한 사람이 전체 파이프라인을 다 만드는 대신, 담당자별로 독립된 도구를 붙이는 구조
3. Main LLM(중앙 오케스트레이터)은 이후 팀이 **폐기 결정** — 지금은 각 Tool이 독립적으로 동작하고, 라우팅은 필요해지면 나중에 얹기로 함(근거는 아래 "왜 Main LLM이 꼭 필요하진 않은가" 참고)

**왜 이 문제인가 (내 담당 기준)**
- 팀원들이 각자 만들 Tool(문서 변환, 코드 분석, 웹 검색 등)을 사용자가 실제로 써볼 수 있는 **통일된 창구**가 필요함 — curl이나 Swagger UI(`/docs`)로 하나씩 테스트하는 건 발표 시연에 안 맞음
- 문서 포맷 변환(docx↔html↔md 등)은 실무에서 자주 필요한데, 매번 다른 프로그램을 켜야 하는 번거로움이 있음

**핵심 가치**
1. 어떤 Tool이 호출됐는지 화면에서 바로 확인 가능 (도구 호출 과정 표시)
2. 파일 업로드→변환→다운로드를 채팅 흐름 안에서 끊김 없이 처리
3. 프레임워크 없는 순수 HTML/CSS/JS라 데모 환경 어디서든 바로 실행 가능

## 2. 프로젝트 설계 (6요소 기반)

내 담당(file-converter + 채팅 UI)은 **LLM을 직접 호출하지 않는 부분**이라, 6요소 중 일부는 "우리 팀 다른 파트가 채워야 할 것"으로 솔직하게 구분해서 발표한다. 무작위 지목 대비, 이 구분을 명확히 알고 있어야 함.

| 요소 | 상태 | 설명 |
|---|:---:|---|
| ① 프롬프트 전략 | ⚠️ 미착수 | file-converter는 pandoc만 쓰는 순수 변환 도구라 프롬프트가 없음. 채팅 API(`/chat`)도 지금은 목(mock)이라 실제 프롬프트 없음 — **팀 전체에서 아직 아무도 안 채운 항목** |
| ② 체인 구조 | ⚠️ 목(mock)만 존재 | `POST /chat`이 키워드 매칭으로 tech/code/general 중 하나를 "호출한 척"하고 정해진 문장을 스트리밍 — 진짜 LLM 체인 아님, 프론트 개발용 자리표시자 |
| ③ 도구 목록 | ✅ 완료 | `file_converter`를 두 형태로 노출 — HTTP API(`POST /tools/file-converter/convert`)와 LangChain `@tool` 데코레이터 함수(`file_converter`, 나중에 진짜 Main LLM이 생기면 그대로 `bind_tools()`에 넘기면 됨) |
| ④ 상태 관리 | ✅ 완료(의도적으로 무상태) | 멀티턴 대화 **미지원으로 확정**(DEC-001) — 매 요청이 이전 맥락과 무관한 독립 처리. 세션/로그인도 없음 |
| ⑤ 스트리밍 | ✅ 완료(목 기준) | `/chat`이 SSE로 `tool_start`/`tool_end`/`answer_chunk`/`done` 이벤트를 스트리밍 — 프론트(`chat.js`)가 실시간으로 받아 도구 상태·답변을 렌더링. 진짜 LLM 연결되면 엔드포인트 계약 그대로 재사용 가능 |
| ⑥ 비용·지연 | N/A | pandoc은 로컬 바이너리 변환이라 OpenAI 비용 없음. LLM 붙는 부분은 다른 담당자가 실측 필요 |

**왜 Main LLM이 꼭 필요하진 않은가** — 팀 내부에서 나온 질문. Main LLM은 여러 Tool 중 뭘 쓸지 **라우팅**하는 역할일 뿐, 프롬프트·구조화출력·LangSmith 트레이스가 실제로 나오는 지점은 각 Tool 안의 LLM이다. 지금처럼 실질적으로 쓸 수 있는 Tool이 하나(또는 소수)뿐이면, 라우팅 없이 그 Tool의 LLM 하나로도 필수요건은 채울 수 있다 — 다만 Tool이 여러 개로 늘면 자동 라우팅이 없어서 사용자가 직접 골라야 하는 게 트레이드오프.

## 3. 진행 내용 (프롬프트 템플릿, 도구 구성 등)

**도구 구성 — file-converter**
- `app/tools/file_converter/converter.py` — pandoc 기반 변환 로직. 지원 포맷: docx, html, md, odt, pptx, epub, rst, rtf, txt (**PDF 미지원** — pandoc이 PDF를 입력으로 못 읽고, 출력엔 별도 LaTeX 엔진 필요해서 스코프 제외)
- `app/tools/file_converter/router.py` — FastAPI HTTP API(`/convert`, `/formats`)
- `app/tools/file_converter/tool.py` — LangChain `@tool` 데코레이터로 선언한 `file_converter` 함수. `response_format="content_and_artifact"`로 LLM에게 줄 텍스트 요약과 실제 변환 바이트를 분리 반환
- **버그 발견·수정 스토리(발표 소재로 좋음)**: docx→html 변환 시 한글이 깨지는 문제 발견 → 원인은 pandoc이 html 출력 시 `<head>` 없는 "조각(fragment)"만 내보내서 `<meta charset="utf-8">` 선언이 아예 없었던 것 → `--standalone` 옵션으로 완전한 문서를 만들게 해서 해결. 전체 9개 포맷을 한글/중국어/일본어/악센트 문자로 왕복 테스트해서 재검증

**프롬프트 템플릿**
- 현재 없음(위 6요소 표 참고) — 다른 담당자의 LLM Tool 파트에서 채워야 함

**채팅 UI 구성**
- `app/static/index.html`·`styles.css`·`chat.js` — 다크모드(Vercel 스타일), 텍스트 질문 + SSE 스트리밍, 파일 드래그·업로드·변환, 도구 호출 상태 실시간 표시
- `app/chat_mock.py` — 진짜 백엔드 나오기 전까지 프론트를 검증할 목 SSE 엔드포인트
- `polish` 디자인 검토로 실결함 6개 수정: 동시 전송 방지, 포맷 로딩 경쟁 상태, 이모지 아이콘→SVG 교체, `<select>` 다크테마 적용, 브라우저 표면(선택 영역·스크롤바) 테마, 전역 포커스 링

**엔드포인트 (필수요건 6종 중 "2개 이상")**
- `POST /tools/file-converter/convert`, `GET /tools/file-converter/formats` — 실제 동작
- `POST /chat` — SSE 스트리밍 (목 상태)
- `GET /` — 채팅 UI 정적 페이지

**현재까지 진행 상태**
- file-converter + 채팅 UI + 관련 문서를 PR #6으로 묶어서 올림, 리뷰 대기 중
- main 브랜치는 현재 보호 규칙 해제 상태(팀 판단으로 계속 열어두기로 함)

## 4. 구현 방식 (소통 방법, 역할 분담)

**소통 방법**
- GitHub 레포(`jh3779/LG-CNS-AICAMPUS`) 단일 소스 — PR로 변경 공유, 이슈/설계 논의는 문서(`docs/`)에 기록
- 각자 독립된 브랜치에서 자기 도구를 만들고 PR로 합류하는 방식("각자 API 만들어서 FastAPI로 연결" 원칙과 동일한 결로 브랜치 전략도 감)

**역할 분담 (현재 기준, 팀 방향 전환 이후)**

| 역할 | 담당 | 비고 |
|---|---|---|
| 도구호출 + 웹 디자인 | 나 | file-converter 도구(HTTP API + LangChain Tool), 채팅 UI(다크모드, SSE, 파일 업로드) |
| Agent 베이스 클래스 | 421079a | `app/llms/agent.py`(`Agent(ABC)`), `app/tools/base.py`(`BaseTool`) — 계속 갱신 중 |
| 나머지 Tool(Tech/Code/General 등) | 미정 | Main LLM 폐기 이후 공백 — README 구조도의 Tool들 중 실제로 구현된 건 file-converter뿐 |

**작업 순서**: 팀원이 공통 베이스 클래스(`Agent`, `BaseTool`)를 만들고, 그 위에서 각자 자기 Tool을 독립적으로 구현 → FastAPI 앱(`app/main.py`)에 라우터/도구로 연결하는 방식. 카테고리별로 서비스를 통째로 나누는 방식(뉴스봇 시절 결정)도, Main LLM이 전부 오케스트레이션하는 방식도 둘 다 기각하고, 지금은 "각자 도구 + 필요하면 나중에 라우팅 계층 추가"로 정리됨.

**남은 리스크(발표 전 팀이 정해야 할 것)**
- 필수요건 6종 중 프롬프트 템플릿·Pydantic 구조화 출력·LangSmith 트레이스, 이 3개는 실제 LLM 호출이 있어야 채워지는데 아직 아무도 안 만들고 있음 — 발표 전까지 누군가 최소 하나의 진짜 LLM Tool을 만들어야 체크리스트 완주 가능
- 채팅 UI가 호출할 진짜 백엔드가 없어서 지금은 목으로 시연 — 실제 LLM Tool이 생기면 `app/chat_mock.py`를 교체해야 함
