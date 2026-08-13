import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.log_stream import subscribe

router = APIRouter(tags=["logs"])


async def _stream() -> AsyncIterator[str]:
    async for entry in subscribe():
        yield f"data: {json.dumps(entry, ensure_ascii=False)}\n\n"


@router.get("/logs/stream")
async def stream_logs() -> StreamingResponse:
    return StreamingResponse(_stream(), media_type="text/event-stream")
