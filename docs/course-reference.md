# 교육 과정 기술 배경 (2주차: 비동기 · FastAPI · Pydantic/Depends · SSE)

> 2026-08-10~08-13에 배운 4일치 강의 내용을 이 미니 프로젝트 관점으로 정리한 참고 문서. "왜 우리 코드가 지금 이 구조인가"를 팀원이 빠르게 파악할 수 있도록, 개념 요약과 이 저장소의 실제 적용 위치를 함께 묶었다. 실습 원본은 작성자 개인 학습 노트(이 저장소에는 포함되지 않음)에 더 상세히 있음.

## 1. 비동기 프로그래밍 (Day 6, 08-10)

**핵심 규칙**: `async def` 함수 안에서는 동기(sync) 함수를 호출하면 안 된다. 동기 호출 하나가 이벤트 루프 전체를 점유해, 그 요청이 끝날 때까지 서버의 다른 모든 요청이 멈춘다.

| 하지 말 것 | 대신 이렇게 |
|---|---|
| `llm.invoke(...)` | `await llm.ainvoke(...)` |
| `time.sleep(n)` | `await asyncio.sleep(n)` |
| `requests.get(...)` | `await httpx.AsyncClient().get(...)` |

- `asyncio.gather(*coros)`로 여러 비동기 작업을 동시에 실행 — 입력 순서대로 결과가 반환되고, 완료 순서와는 무관.
- 동시 요청이 많아지면 Rate Limit(429)에 걸릴 수 있음 — `asyncio.Semaphore(n)`로 동시 실행 개수를 제한해 완화.
- **이 저장소 적용 예시**: `app/llms/file_converter_agent.py`의 `astream()` — `await self.create_workflow().ainvoke(...)`, `await file_converter.ainvoke(call)`처럼 전부 비동기 호출로 구성됨. 새 에이전트/도구를 추가할 때도 이 규칙을 그대로 지켜야 서버가 다른 요청과 동시에 여러 LLM 호출을 처리할 수 있다.

## 2. FastAPI 표준 구조 (Day 7, 08-11)

FastAPI 앱은 보통 3계층으로 나눈다 — 회사 조직도에 비유하면 이해하기 쉽다.

| 계층 | 역할 | 비유 |
|---|---|---|
| `main.py` | URL을 보고 어느 라우터에 넘길지만 결정 | 안내 데스크 |
| `routers/` | 요청을 받아 서비스를 호출하고 응답을 반환 | 부서 담당자 |
| `services/` (또는 `llms/`) | 실제 로직(LLM 호출, 도구 실행 등) 수행 | 실무 부서 |

- 계층을 나누는 이유: 하나의 파일에 다 넣으면 특정 기능에 버그가 생겼을 때 원인을 찾기 어렵다. 계층이 분리돼 있으면 "라우팅 문제인가, 로직 문제인가"를 빠르게 좁힐 수 있다.
- 파라미터 3종: **경로 파라미터**(`/items/{id}`, 필수, 자동으로 함수 인자에 매핑) / **쿼리 파라미터**(`?keyword=AI&limit=10`, `?` 뒤 key=value, default 있으면 생략 가능) / **바디 파라미터**(JSON, 방대한 데이터를 주고받을 때, 주로 `POST`에서 사용).
- 각 폴더(`app/`, `app/routers/` 등)에 `__init__.py`가 없으면 파이썬이 해당 폴더를 패키지로 인식하지 못해 `ModuleNotFoundError`가 발생한다 — 새 하위 폴더를 만들 때마다 챙길 것.
- **이 저장소 적용 예시**: `app/main.py`(앱 조립+라우터 등록) → `app/routers/*.py`(chat, file_converter, kbo 등 도메인별 라우터) → `app/services/*.py`/`app/llms/*.py`(실제 로직)로 이미 이 구조를 따르고 있다. 새 기능(에이전트·도구)을 추가할 때도 이 3계층 분리를 유지하는 게 팀 컨벤션에 맞다.

## 3. Pydantic v2 스키마 + `Depends` 의존성 주입 (Day 8, 08-12)

### 스키마 = 입출력 검증

- Pydantic `BaseModel` + `Field(...)`로 요청/응답 형식을 강제하면, FastAPI가 자동으로 검증하고 어긋난 요청에는 코드 한 줄 없이 422를 반환한다.
- 지난주(1주차) LLM 출력 구조화에 쓰던 것과 **같은 문법, 다른 용도** — 그때는 "LLM 출력"을 검증했다면 지금은 "HTTP 입력"을 검증한다.
- 422 응답의 `detail[]`에는 `loc`(어느 필드), `type`(예: `string_too_short`), `msg`(사람이 읽는 설명)가 담긴다.
- **이 저장소 적용 예시**: `app/schemas/*.py`(chat.py, file_converter.py, kbo.py, finance.py, tech.py 등)에 도메인별 요청/응답 스키마가 분리돼 있음. 새 에이전트를 추가할 때는 전용 스키마 파일을 `app/schemas/`에 만드는 게 컨벤션.

### `Depends` — "회사 공용 커피머신"

- `Depends`는 요청마다 자원(LLM 클라이언트 등)을 새로 만들지 않고 재사용하게 해주는 FastAPI의 의존성 주입 기능이다.
- `@lru_cache()`를 붙인 팩토리 함수와 함께 쓰면, 앱이 켜져 있는 동안 인스턴스가 딱 1번만 만들어지고 이후 모든 요청이 그 인스턴스를 공유(싱글턴)한다. 이게 없으면 동시 요청 100개마다 `ChatOpenAI()`가 100번 새로 생성돼 메모리·연결이 낭비된다.
- **이 저장소 적용 예시**: `app/dependencies.py`의 `get_tech_agent()`, `get_finance_model()` 등이 `@lru_cache` 패턴을 그대로 쓰고 있다. 단, `get_file_converter_agent()`는 의도적으로 `@lru_cache`를 안 쓰는데(코드 주석 참고), 매 요청 독립 인스턴스가 필요한 경우도 있다는 걸 보여주는 사례 — 무조건 캐시하는 게 정답은 아니라는 점도 함께 참고할 것.

### 전역 예외 핸들러

- `@app.exception_handler(Exception)`으로 예상 못한 서버 오류를 잡아 안전한 메시지로 통일하면, Python 스택 트레이스(내부 파일 경로 등)가 클라이언트에 그대로 노출되는 걸 막을 수 있다. 보안상 필수에 가까운 습관.

## 4. SSE 스트리밍 (Day 9, 08-13)

**왜 필요한가**: LLM 응답은 도구 호출이 늘어날수록 몇 초~몇십 초까지 걸릴 수 있다. 완성된 답변을 한 번에 반환하면 그동안 사용자는 빈 화면만 보게 되는데, 토큰이 생성되는 대로 실시간으로 흘려보내면(스트리밍) 체감 속도가 크게 개선된다 — 실제 총 소요 시간은 동일해도 첫 글자가 훨씬 빨리 나타난다(TTFT, Time To First Token).

**스트리밍 구현 방식 3종 비교**:

| 방식 | 방향 | LLM 적합성 |
|---|---|---|
| **SSE** | 서버→클라이언트(단방향) | ✅ 최적 — 구현 간단, LLM 토큰 전달엔 양방향이 필요 없음 |
| WebSocket | 양방향 | LLM엔 오버스펙 |
| 폴링 | 주기적 재요청 | 비효율(불필요한 반복 요청) |

**구현 핵심**:
- `async generator`(`async def` 함수 안에서 `yield`)가 "비동기"+"여러 번 반환" 두 조건을 동시에 만족하는 유일한 파이썬 구조 — LLM 토큰 스트리밍에 정확히 대응한다.
- SSE 프로토콜은 텍스트 기반: `data: {JSON}\n\n` (이벤트 타입을 별도 `event:` 줄로 보낼 수도 있고, JSON 안에 타입 필드를 넣는 방식도 가능 — 아래 참고).
- FastAPI에서는 `StreamingResponse(generator, media_type="text/event-stream")`로 응답해야 스트리밍이 동작한다. 이 클래스를 빼먹으면 코드는 그대로인데 스트리밍이 안 되는 흔한 실수.
- 종료 신호(`done` 이벤트 등)를 명시적으로 보내야 클라이언트가 "언제 끝났는지" 알 수 있다.
- **이 저장소 적용 예시**: `app/services/chat.py`의 `_sse()` 헬퍼 —

  ```python
  def _sse(event: dict) -> str:
      return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
  ```

  강의에서 배운 `event: [타입]\ndata: [JSON]\n\n` 형식의 변형으로, 별도 `event:` 줄 대신 JSON `data` 안에 `"type"` 필드(`tool_start`/`tool_end`/`answer_chunk`/`done`)를 넣는 방식이다. `astream_sse()`가 이 헬퍼로 이벤트를 만들어 `yield`하고, `app/routers/chat.py`가 `StreamingResponse(service.astream_sse(...), media_type="text/event-stream")`로 감싸 응답한다 — 강의 패턴과 동일한 원리, 다른 이벤트 포맷 표현.
  - 참고로 `app/log_stream.py`는 채팅 응답과는 별개로, 서버 실행 로그를 실시간으로 클라이언트에 흘려보내는 **또 다른 SSE 스트림**(`/logs/stream`)이다 — 같은 SSE 원리를 채팅이 아닌 관측(observability) 목적으로 응용한 사례.

## 참고

- 원본 학습 기록은 작성자의 개인 노트에 있으며 이 저장소에는 포함되지 않는다.
- 이 문서는 2026-08-13(Day 9, SSE) 시점까지의 내용을 반영함. 다음 날(8/14)은 신규 강의 없이 팀 프로젝트 마무리 + 발표.
