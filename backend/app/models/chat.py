import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy import String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="New Conversation", nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", 
        back_populates="session", 
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="ChatMessage.created_at"
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Serialized JSON sources storage (stores list of dicts with keys 'filename', 'page')
    _sources: Mapped[Optional[str]] = mapped_column("sources", Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    
    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    @property
    def sources(self) -> List[Dict[str, Any]]:
        """
        JSON deserializes the sources column.
        """
        if not self._sources:
            return []
        try:
            return json.loads(self._sources)
        except Exception:
            return []

    @sources.setter
    def sources(self, value: List[Dict[str, Any]]) -> None:
        """
        JSON serializes list inputs to the sources database column.
        """
        if value is None:
            self._sources = None
        else:
            self._sources = json.dumps(value)
