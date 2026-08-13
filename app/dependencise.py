from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from langchain_openai import ChatOpenAI

from app.llms.tech import TechAgent
from app.services.tech import TechService
from app.setting import settings


@lru_cache
def get_tech_agent() -> TechAgent:
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        api_key=settings.openai_api_key,
    )
    return TechAgent(model)


def get_tech_service(
    agent: Annotated[TechAgent, Depends(get_tech_agent)],
) -> TechService:
    return TechService(
        agent,
        chunk_delay=0.1,
    )
