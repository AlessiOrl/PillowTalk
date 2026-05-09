from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_answer_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)
    last_prompt_session_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_prompt_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    group: Mapped["Group | None"] = relationship(back_populates="users")
    answers: Mapped[list["Answer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
