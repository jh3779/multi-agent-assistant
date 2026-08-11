from typing import Any

from langchain_tavily import TavilySearch

from app.tools.base import BaseTool


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web for information from external sources."
    )

    max_results: int = 5
    search_depth: str = "advanced"

    def _run(
        self,
        query: str,
        **kwargs: Any,
    ) -> Any:
        tavily = TavilySearch(
            max_results=self.max_results,
            search_depth=self.search_depth,
        )

        return tavily.invoke(
            {"query": query}
        )

    async def _arun(
        self,
        query: str,
        **kwargs: Any,
    ) -> Any:
        tavily = TavilySearch(
            max_results=self.max_results,
            search_depth=self.search_depth,
        )

        return await tavily.ainvoke(
            {"query": query}
        )