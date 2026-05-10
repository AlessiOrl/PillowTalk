from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


QUESTION_CATEGORY_OPEN = "open"
QUESTION_CATEGORY_CLOSED = "closed"
QUESTION_CATEGORY_ACTION = "action"
QUESTION_CATEGORY_WOULD = "would"
QUESTION_CATEGORIES = {
    QUESTION_CATEGORY_OPEN,
    QUESTION_CATEGORY_CLOSED,
    QUESTION_CATEGORY_ACTION,
    QUESTION_CATEGORY_WOULD,
}

CHOICE_QUESTION_OPTIONS = {
    QUESTION_CATEGORY_WOULD: [
        "🟢 would do",
        "🟠 maybe",
        "🔴 never",
    ],
}

BUTTON_QUESTION_CATEGORIES = {
    QUESTION_CATEGORY_CLOSED,
    *CHOICE_QUESTION_OPTIONS.keys(),
}


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    times_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    prompts: Mapped[list["PromptSession"]] = relationship(back_populates="question")
