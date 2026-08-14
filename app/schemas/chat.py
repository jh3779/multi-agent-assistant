from pydantic import BaseModel


class ChatRequest(BaseModel):
    """POST /chat(app/routers/chat.py)의 요청 스키마."""

    message: str
