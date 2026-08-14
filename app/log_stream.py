import asyncio
import logging
import time
from collections import deque
from collections.abc import AsyncIterator
from typing import Any

_HISTORY_MAXLEN = 300
_history: deque[dict[str, Any]] = deque(maxlen=_HISTORY_MAXLEN)
_subscribers: set[asyncio.Queue] = set()


class _BroadcastHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "time": time.strftime("%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        _history.append(entry)
        for queue in list(_subscribers):
            queue.put_nowait(entry)


def setup_log_capture() -> None:
    """app.* 로거들의 실행 로그를 /logs/stream으로 내보낼 수 있도록 캡처를 시작한다."""

    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(_BroadcastHandler())


async def subscribe() -> AsyncIterator[dict[str, Any]]:
    """연결 시점까지 쌓인 로그 이력을 먼저 흘려보낸 뒤, 새 로그를 실시간으로 이어서 전달한다."""

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _subscribers.add(queue)
    try:
        for entry in list(_history):
            yield entry
        while True:
            yield await queue.get()
    finally:
        _subscribers.discard(queue)
