import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class DateTimeTool(BaseTool):
    name: str = "date_time"
    description: str = "Get the current date and time in the specified timezone."

    timezone: str = "Asia/Seoul"

    def _run(
        self,
        **kwargs: Any,
    ) -> str:
        logger.info(
            "[TOOL] Getting current date and time for timezone: %s",
            self.timezone,
        )
        now = datetime.now(ZoneInfo(self.timezone))

        return now.isoformat()

    async def _arun(
        self,
        **kwargs: Any,
    ) -> str:
        return self._run()
