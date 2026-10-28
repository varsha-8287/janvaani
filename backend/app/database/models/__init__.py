
"""SQLAlchemy models for Janvaani's initial database schema."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class Profile(Base):
    """User profile linked to a Firebase authentication identity."""

    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    firebase_uid: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    preferred_language: Mapped[str] = mapped_column(
        String(12), nullable=False, default="en"
    )
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="Conversation.updated_at.desc()",
    )


class Scheme(Base):
    """Stable identity and catalogue metadata for a government scheme."""

    __tablename__ = "schemes"
    __table_args__ = (
        CheckConstraint(
            "government_level IN ('central', 'state', 'local', 'other')",
            name="ck_schemes_government_level",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_schemes_status",
        ),
        Index("ix_schemes_status_title", "status", "title"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    slug: Mapped[str] = mapped_column(
        String(180), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    administering_authority: Mapped[str | None] = mapped_column(
        String(300), nullable=True
    )
    government_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="central"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    versions: Mapped[list["SchemeVersion"]] = relationship(
        back_populates="scheme",
        cascade="all, delete-orphan",
        order_by="SchemeVersion.version_number",
    )


class SchemeVersion(Base):
    """Versioned content and eligibility criteria for a scheme."""

    __tablename__ = "scheme_versions"
    __table_args__ = (
        UniqueConstraint(
            "scheme_id",
            "version_number",
            name="uq_scheme_versions_scheme_version",
        ),
        CheckConstraint(
            "version_number >= 1",
            name="ck_scheme_versions_version_positive",
        ),
        CheckConstraint(
            "review_status IN ('draft', 'pending_review', 'approved', 'rejected')",
            name="ck_scheme_versions_review_status",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from",
            name="ck_scheme_versions_valid_dates",
        ),
        Index("ix_scheme_versions_review_status", "review_status"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    scheme_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(
        String(12), nullable=False, default="en"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)
    eligibility_criteria: Mapped[dict | list | None] = mapped_column(
        JSONB, nullable=True
    )
    required_documents: Mapped[list | dict | None] = mapped_column(
        JSONB, nullable=True
    )
    application_process: Mapped[list | dict | None] = mapped_column(
        JSONB, nullable=True
    )
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    scheme: Mapped["Scheme"] = relationship(back_populates="versions")
    source_documents: Mapped[list["SourceDocument"]] = relationship(
        back_populates="scheme_version",
        cascade="all, delete-orphan",
    )


class SourceDocument(Base):
    """Provenance and review metadata for source material."""

    __tablename__ = "source_documents"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('pending', 'verified', 'rejected')",
            name="ck_source_documents_review_status",
        ),
        Index("ix_source_documents_version", "scheme_version_id"),
        Index("ix_source_documents_content_hash", "content_hash"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    scheme_version_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("scheme_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(300), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str | None] = mapped_column(String(12), nullable=True)
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )

    scheme_version: Mapped["SchemeVersion"] = relationship(
        back_populates="source_documents"
    )


class Conversation(Base):
    """User conversation thread with the chatbot."""

    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_profile_updated", "profile_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    profile_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="New Conversation"
    )
    language: Mapped[str] = mapped_column(
        String(12), nullable=False, default="en"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=utc_now,
    )

    profile: Mapped["Profile"] = relationship(back_populates="conversations")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """A single turn/message within a conversation."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_chat_messages_role",
        ),
        Index("ix_chat_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list | dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages"
    )
