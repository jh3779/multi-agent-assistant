import json
from collections.abc import AsyncIterator

from app.llms.file_converter_agent import FileConverterAgent


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


class ChatService:
    """FileConverterAgent의 실행 결과를 /chat이 쓰는 SSE 이벤트로 바꾼다."""

    def __init__(self, agent: FileConverterAgent):
        self.agent = agent

    async def astream_sse(self, message: str) -> AsyncIterator[str]:
        try:
            chunks = [chunk async for chunk in self.agent.astream(message)]
        except Exception as exc:  # noqa: BLE001
            # 스트리밍 응답은 이미 200 헤더가 나간 뒤라 HTTPException으로 바꿀 수
            # 없다 — OpenAI API 오류든 뭐든 여기서 다 잡아 answer_chunk로 흘려보내고
            # done으로 마무리해야 chat.js가 스트림이 끊긴 것처럼 멈추지 않는다.
            yield _sse(
                {"type": "answer_chunk", "content": f"오류가 발생했습니다: {exc}"}
            )
            yield _sse({"type": "done"})
            return

        # FileConverterAgent.astream()은 with_structured_output 특성상 완성된 답변을
        # 한 번에 반환한다(app/llms/file_converter_agent.py 참고) — 그래서 도구를
        # 실제로 실행한 "동안"이 아니라 실행이 끝난 뒤에야 tool_start/tool_end를
        # 보여줄 수 있다. 실시간 진행 표시는 아니지만, 도구를 실제로 썼는지는 정확하다.
        answer = self.agent.memory.get("answer")
        if answer is not None and answer.used_tool:
            yield _sse(
                {"type": "tool_start", "tool": answer.tool_name or "file_converter"}
            )
            yield _sse({"type": "tool_end"})

        for chunk in chunks:
            yield _sse({"type": "answer_chunk", "content": chunk})

        yield _sse({"type": "done"})
