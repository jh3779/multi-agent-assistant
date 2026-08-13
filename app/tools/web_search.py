import logging
from typing import Any

from langchain_tavily import TavilySearch
from pydantic import Field

from app.tools.base import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for information from external sources."

    max_results: int = 5
    search_depth: str = "advanced"

    def _run(
        self,
        query: str,
        **kwargs: Any,
    ) -> Any:
        logger.info(f"\n[TOOL] Searching web: {query}")
        tavily = TavilySearch(
            tavily_api_key=self.settings.tavily_api_key,
            max_results=self.max_results,
            search_depth=self.search_depth,
        )

        return tavily.invoke({"query": query})

    async def _arun(
        self,
        query: str,
        **kwargs: Any,
    ) -> Any:
        logger.info(f"\n[TOOL] Searching web: {query}")
        tavily = TavilySearch(
            tavily_api_key=self.settings.tavily_api_key,
            max_results=self.max_results,
            search_depth=self.search_depth,
        )

        return await tavily.ainvoke({"query": query})


class CachedWebSearchTool(WebSearchTool):
    """검색 결과를 query 기준으로 캐싱하는 WebSearchTool."""

    cache: Any = Field(default_factory=dict)

    async def _arun(
        self,
        query: str,
    ) -> Any:
        if query in self.cache:
            logger.info("검색 캐시 사용: %s", query)
            return self.cache[query]

        self.cache[query] = await super()._arun(query)
        return self.cache[query]

    def _run(
        self,
        query: str,
    ) -> Any:
        if query in self.cache:
            logger.info("검색 캐시 사용: %s", query)
            return self.cache[query]

        self.cache[query] = super()._run(query)
        return self.cache[query]
