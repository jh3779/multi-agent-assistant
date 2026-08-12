# 07. 사용 설명 — file-converter 도구 & 채팅 UI

> 설계 배경·근거는 [architecture.md](architecture.md), [presentation.md](presentation.md) 참고 — 이 문서는 "어떻게 쓰는지"만 다룬다.

## 로컬 실행

```bash
uv sync --dev
cp .env.example .env   # OPENAI_API_KEY 등 채우기
uv run uvicorn app.main:app --reload
```

브라우저에서 http://127.0.0.1:8000 열면 채팅 UI가 뜬다.

## 1. 채팅 UI에서 쓰기

- 화면 하단 입력창에 텍스트를 치면 `/chat`(현재는 목 응답)으로 전송됨
- 파일을 채팅창 위로 드래그하면 지원 포맷인지 즉시 확인 → 변환할 포맷 선택 → "변환" 클릭 → 완료되면 다운로드 링크 표시

## 2. file-converter를 HTTP API로 직접 호출하기

### 지원 포맷 목록 조회

```bash
curl http://127.0.0.1:8000/tools/file-converter/formats
```

```json
{"supported_formats": ["docx", "epub", "htm", "html", "markdown", "md", "odt", "pptx", "rst", "rtf", "txt"]}
```

**PDF는 지원하지 않음** — pandoc이 PDF를 입력으로 읽지 못하고, 출력하려면 별도 엔진(LaTeX 등)이 필요해서 스코프에서 제외했다.

### 파일 변환

```bash
curl -X POST http://127.0.0.1:8000/tools/file-converter/convert \
  -F "file=@문서.docx" \
  -F "target_format=html" \
  -o 변환결과.html
```

- `file`: 변환할 원본 파일(멀티파트 업로드)
- `target_format`: 대상 확장자(위 목록 중 하나, 원본과 같은 포맷도 가능은 하지만 의미 없음)
- 응답: 변환된 파일이 그대로 바이너리로 내려옴(`Content-Disposition: attachment`) — 위 예시처럼 `-o`로 저장

**에러 응답**

| 상황 | 상태 코드 |
|---|---|
| 확장자로 원본 포맷을 못 알아냄(파일명에 `.` 없음) | 400 |
| 지원하지 않는 포맷 조합(예: `pdf` 입력) | 400 |
| 업로드 파일이 20MB 초과 | 413 |
| pandoc 변환이 30초 안에 안 끝남 | 504 |

## 3. Python 코드에서 직접 호출하기 (LangChain 도구로)

LLM이 아니라 그냥 코드에서 변환 로직만 쓰고 싶으면:

```python
from app.tools.file_converter.converter import convert

converted_bytes = await convert(원본_bytes, "docx", "html")
```

LLM이 Function Calling으로 이 도구를 호출하게 하려면 `FileConverterTool`을 다른 LangChain 도구처럼 `bind_tools()`에 넘기면 된다. 단, `file_path` 인자는 **`app/tools/file_converter/tool.py`의 `ALLOWED_DIR`(시스템 임시 디렉터리 하위) 안에 있는 파일만 허용**한다 — 그 밖의 경로는 보안상 거부된다.

```python
from app.tools.file_converter.tool import FileConverterTool, ALLOWED_DIR

tool = FileConverterTool()
# 변환할 파일을 먼저 ALLOWED_DIR 안에 둬야 함
target_path = ALLOWED_DIR / "example.md"
target_path.write_bytes(원본_bytes)

content, artifact_bytes = await tool._arun(str(target_path), "html")
```

## 4. 실제 LLM 에이전트로 호출하기 (데모/실험용)

`app/llms/file_converter_agent.py`의 `ask()`가 실제 OpenAI 모델이 스스로 도구 호출 여부를 판단하는 최소 에이전트다. 아직 HTTP 엔드포인트로는 안 열려있어서 코드에서 직접 호출해야 한다.

```python
from app.llms.file_converter_agent import ask

answer, artifacts = await ask(
    "이 파일을 html로 바꿔줘",
    file_path="/path/to/allowed/dir/example.md",
)
print(answer.summary)       # LLM이 정리한 결과 요약
print(len(artifacts))       # 실제 변환된 파일 바이트 목록
```

`OPENAI_API_KEY`가 `.env`에 실제 값으로 채워져 있어야 동작한다.
