# 프론트(app/static/chat.js)를 검증하기 위한 목(mock, app/chat_mock.py)을 폐기한 뒤
# 비어있던 POST /chat 자리 — FileConverterAgent(app/llms/file_converter_agent.py)를
# 실제 백엔드로 연결한다. 이벤트 계약(tool_start/tool_end/answer_chunk/done)은 목이
# 쓰던 것과 동일하게 맞춰서, chat.js를 고칠 필요 없이 그대로 재사용한다.
#
# 채팅 텍스트 입력창은 파일 경로를 같이 보내지 않는다(파일 변환은 여전히 별도
# 드래그앤드롭 플로우 → POST /tools/file-converter/convert 로 처리됨) — 그래서 지금
# 이 경로는 실질적으로 "file_converter가 뭘 하는 도구인지 설명하는 질문"에 실제
# LLM(gpt-4o-mini)이 답하는 데 쓰인다. 파일 경로까지 채팅으로 넘기는 건 범위 밖.
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.llms.file_converter_agent import FileConverterAgent
from app.schemas.chat import ChatRequest

router = APIRouter(tags=["chat"])


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


async def _stream_answer(message: str) -> AsyncIterator[str]:
    agent = FileConverterAgent()
    try:
        chunks = [chunk async for chunk in agent.astream(message)]
    except Exception as exc:  # noqa: BLE001
        # 스트리밍 응답은 이미 200 헤더가 나간 뒤라 HTTPException으로 바꿀 수
        # 없다 — OpenAI API 오류든 뭐든 여기서 다 잡아 answer_chunk로 흘려보내고
        # done으로 마무리해야 chat.js가 스트림이 끊긴 것처럼 멈추지 않는다.
        yield _sse({"type": "answer_chunk", "content": f"오류가 발생했습니다: {exc}"})
        yield _sse({"type": "done"})
        return

    # FileConverterAgent.astream()은 with_structured_output 특성상 완성된 답변을
    # 한 번에 반환한다(app/llms/file_converter_agent.py 참고) — 그래서 도구를
    # 실제로 실행한 "동안"이 아니라 실행이 끝난 뒤에야 tool_start/tool_end를
    # 보여줄 수 있다. 실시간 진행 표시는 아니지만, 도구를 실제로 썼는지는 정확하다.
    answer = agent.memory.get("answer")
    if answer is not None and answer.used_tool:
        yield _sse({"type": "tool_start", "tool": answer.tool_name or "file_converter"})
        yield _sse({"type": "tool_end"})

    for chunk in chunks:
        yield _sse({"type": "answer_chunk", "content": chunk})

    yield _sse({"type": "done"})


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_answer(request.message), media_type="text/event-stream"
    )
