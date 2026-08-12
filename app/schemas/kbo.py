from pydantic import BaseModel


class KBORequest(BaseModel):
    query: str


class KBOResponse(BaseModel):
    answer: str
