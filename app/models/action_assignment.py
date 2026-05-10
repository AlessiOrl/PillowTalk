from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class ActionAssignment(Base):
    __tablename__ = "action_assignments"
    __table_args__ = (UniqueConstraint("prompt_session_id", "user_id", name="uq_action_session_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_session_id: Mapped[int] = mapped_column(ForeignKey("prompt_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship()
    question: Mapped["Question"] = relationship()
    prompt_session: Mapped["PromptSession"] = relationship()
