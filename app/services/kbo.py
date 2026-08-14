from collections.abc import AsyncIterator

from app.llms.kbo import KBOAgent


class KBOService:
    def __init__(self, agent: KBOAgent):
        self.agent = agent

    async def ainvoke(
        self,
        question: str,
    ) -> str:
        return await self.agent.ainvoke(question)

    async def astream(
        self,
        question: str,
    ) -> AsyncIterator[str]:
        async for chunk in self.agent.astream(question):
            yield chunk
