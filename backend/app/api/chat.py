
"""Chat API backed by reviewed scheme retrieval."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.chatbot.service import chat
from app.database.session import get_db

router = APIRouter(prefix="/api/chat", tags=["Chat"])


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    language: str | None = Field(default=None, min_length=2, max_length=20)


class ChatSource(BaseModel):
    id: int
    scheme_title: str
    source_url: str
    publisher: str | None = None
    version_number: int | None = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    generated_by: str
    sources: list[ChatSource]


@router.post("", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Answer a message using retrieved scheme evidence."""
    if not request.message.strip():
        raise HTTPException(
            status_code=422,
            detail="Message must not be blank.",
        )

    result = chat(
        db=db,
        question=request.message,
        history=[turn.model_dump() for turn in request.history],
        language=request.language,
    )
    return ChatResponse(**result)
