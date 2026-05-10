from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


ANSWER_RATING_LIKE = "like"
ANSWER_RATING_NEUTRAL = "neutral"
ANSWER_RATING_DISLIKE = "dislike"
ANSWER_RATINGS = {
    ANSWER_RATING_LIKE,
    ANSWER_RATING_NEUTRAL,
    ANSWER_RATING_DISLIKE,
}


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (UniqueConstraint("user_id", "prompt_session_id", name="uq_user_prompt_answer"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_session_id: Mapped[int] = mapped_column(ForeignKey("prompt_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="answers")
    prompt_session: Mapped["PromptSession"] = relationship(back_populates="answers")
