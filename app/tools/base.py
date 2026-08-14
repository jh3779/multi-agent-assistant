from typing import ClassVar

from langchain_core.tools import BaseTool as LangChainBaseTool

from app.setting import Settings, settings


class BaseTool(LangChainBaseTool):
    settings: ClassVar[Settings] = settings
