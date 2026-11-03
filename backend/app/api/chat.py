"""Chat API backed by reviewed scheme retrieval with persistent conversation support."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.auth import CurrentUser, get_current_user
from app.api.profiles import get_or_create_profile
from app.chatbot.service import chat
from app.database.models import ChatMessage, Conversation, utc_now
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


# --- Persistent Conversation Schemas ---


class CreateConversationRequest(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    language: str = Field(default="en", min_length=2, max_length=12)


class SendMessageRequest(BaseModel):
    message: str | None = Field(default=None, max_length=1000)
    content: str | None = Field(default=None, max_length=1000)
    language: str | None = Field(default=None, max_length=12)


class ChatMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: Literal["user", "assistant"]
    content: str
    sources: list[ChatSource] | None = None
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    id: UUID
    title: str
    language: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationDetailResponse(BaseModel):
    id: UUID
    title: str
    language: str
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse]


# --- Helper Functions ---


def _get_verified_conversation(
    db: Session,
    conversation_id: UUID,
    user_uid: str,
    *,
    for_update: bool = False,
) -> Conversation:
    """Retrieve conversation and verify citizen ownership with optional row locking."""
    profile = get_or_create_profile(db, user_uid)

    stmt = select(Conversation).where(Conversation.id == conversation_id)
    if for_update:
        stmt = stmt.with_for_update()

    conversation = db.scalar(stmt)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    if conversation.profile_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this conversation",
        )

    return conversation


# --- Stateless Chat Endpoint (Preserved) ---


@router.post("", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Answer a message statelessly using retrieved scheme evidence."""
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


# --- Persistent Conversation Endpoints ---


@router.post(
    "/conversations",
    response_model=ConversationSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    request: CreateConversationRequest | None = None,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationSummaryResponse:
    """Create a new persistent conversation for the authenticated citizen."""
    profile = get_or_create_profile(db, user.uid)

    title = (
        request.title.strip()
        if request and request.title and request.title.strip()
        else "New Conversation"
    )
    language = (
        request.language.strip()
        if request and request.language and request.language.strip()
        else profile.preferred_language or "en"
    )

    conversation = Conversation(
        profile_id=profile.id,
        title=title,
        language=language,
    )
    try:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    except Exception:
        db.rollback()
        raise

    return ConversationSummaryResponse(
        id=conversation.id,
        title=conversation.title,
        language=conversation.language,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=0,
    )


@router.get(
    "/conversations",
    response_model=list[ConversationSummaryResponse],
)
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationSummaryResponse]:
    """List the current citizen's conversations, ordered by most recently updated."""
    profile = get_or_create_profile(db, user.uid)

    # Subquery for message count
    msg_count_subq = (
        select(func.count(ChatMessage.id))
        .where(ChatMessage.conversation_id == Conversation.id)
        .scalar_subquery()
    )

    stmt = (
        select(Conversation, msg_count_subq.label("message_count"))
        .where(Conversation.profile_id == profile.id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )

    rows = db.execute(stmt).all()

    return [
        ConversationSummaryResponse(
            id=conv.id,
            title=conv.title,
            language=conv.language,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=count or 0,
        )
        for conv, count in rows
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation_detail(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    """Retrieve full details and chronological messages for a conversation."""
    conversation = _get_verified_conversation(db, conversation_id, user.uid)

    prior_messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
    ).all()

    messages = [
        ChatMessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            sources=[ChatSource(**s) for s in msg.sources] if msg.sources else None,
            created_at=msg.created_at,
        )
        for msg in prior_messages
    ]

    return ConversationDetailResponse(
        id=conversation.id,
        title=conversation.title,
        language=conversation.language,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
)
def send_conversation_message(
    conversation_id: UUID,
    request: SendMessageRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    """Send a message to an existing conversation, persist turns, and return grounded response."""
    user_text = (request.message or request.content or "").strip()
    if not user_text:
        raise HTTPException(
            status_code=422,
            detail="Message must not be blank.",
        )

    # 1. Retrieve verified conversation without blocking table locks across RAG
    conversation = _get_verified_conversation(
        db, conversation_id, user.uid, for_update=False
    )

    # If client supplied an explicit language, update conversation language
    if request.language and request.language.strip():
        conversation.language = request.language.strip()

    # 2. Build history turns strictly after acquiring lock
    prior_messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.asc())
    ).all()

    history = [
        {"role": m.role, "content": m.content}
        for m in prior_messages
    ]

    try:
        # 3. Record citizen's message
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            role="user",
            content=user_text,
        )
        db.add(user_msg)

        # 4. Call RAG chat service with conversation context & language
        chat_result = chat(
            db=db,
            question=user_text,
            history=history,
            language=conversation.language,
        )

        # 5. Record assistant's response with sources
        assistant_msg = ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=chat_result["answer"],
            sources=chat_result.get("sources") or None,
        )
        db.add(assistant_msg)

        # 6. Update conversation timestamp and set title if first turn
        if conversation.title == "New Conversation" and not prior_messages:
            conversation.title = user_text[:50].strip()

        conversation.updated_at = utc_now()
        db.commit()
        db.refresh(assistant_msg)

        return ChatMessageResponse(
            id=assistant_msg.id,
            conversation_id=assistant_msg.conversation_id,
            role="assistant",
            content=assistant_msg.content,
            sources=[ChatSource(**s) for s in assistant_msg.sources] if assistant_msg.sources else None,
            created_at=assistant_msg.created_at,
        )
    except Exception:
        db.rollback()
        raise


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
)
def delete_conversation(
    conversation_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a conversation and all its messages."""
    conversation = _get_verified_conversation(
        db, conversation_id, user.uid, for_update=True
    )

    try:
        db.delete(conversation)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Conversation deleted",
        "id": str(conversation_id),
    }
