from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.answer import Answer
from app.models.prompt_session import PromptSession
from app.models.question import QUESTION_CATEGORIES, Question


@dataclass(slots=True)
class PromptDispatch:
    prompt_session: PromptSession
    created: bool


class QuestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def import_questions_from_csv(self, csv_path: str) -> int:
        dataframe = pd.read_csv(csv_path)
        required_columns = {"id", "question", "category"}
        missing_columns = required_columns.difference(dataframe.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing columns in questions CSV: {missing}")

        imported = 0
        for row in dataframe.itertuples(index=False):
            question_id = int(row.id)
            category = self._normalize_category(row.category, question_id)
            question = await self.session.get(Question, question_id)
            if question is None:
                question = Question(
                    id=question_id,
                    text=str(row.question).strip(),
                    category=category,
                )
                self.session.add(question)
            else:
                question.text = str(row.question).strip()
                question.category = category
            imported += 1

        await self.session.commit()
        return imported

    async def create_or_get_daily_prompt(
        self,
        *,
        asked_on: date | None = None,
        source: str = "scheduled",
        force_new: bool = False,
    ) -> PromptDispatch:
        prompt_date = asked_on or datetime.now(ZoneInfo(self.settings.timezone)).date()
        if not force_new:
            existing = await self.get_latest_prompt_for_date(prompt_date)
            if existing is not None:
                return PromptDispatch(prompt_session=existing, created=False)

        question = await self._pick_next_question()
        if question is None:
            raise RuntimeError("No questions available. Seed the database first.")

        now = datetime.utcnow()
        question.last_used_at = now
        question.times_used += 1

        prompt_session = PromptSession(
            question_id=question.id,
            asked_on=prompt_date,
            source=source,
            question=question,
        )
        self.session.add(prompt_session)
        await self.session.commit()
        await self.session.refresh(prompt_session)
        prompt_session = await self.get_prompt_by_id(prompt_session.id)
        if prompt_session is None:
            raise RuntimeError("Prompt session was created but could not be reloaded.")
        return PromptDispatch(prompt_session=prompt_session, created=True)

    async def get_current_prompt(self) -> PromptSession | None:
        statement = (
            select(PromptSession)
            .options(selectinload(PromptSession.question))
            .order_by(PromptSession.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(statement)

    async def get_latest_prompt_for_date(self, asked_on: date) -> PromptSession | None:
        statement = (
            select(PromptSession)
            .options(selectinload(PromptSession.question))
            .where(PromptSession.asked_on == asked_on)
            .order_by(PromptSession.created_at.desc())
            .limit(1)
        )
        return await self.session.scalar(statement)

    async def get_prompt_by_id(self, prompt_session_id: int) -> PromptSession | None:
        statement = (
            select(PromptSession)
            .options(selectinload(PromptSession.question))
            .where(PromptSession.id == prompt_session_id)
        )
        return await self.session.scalar(statement)

    async def count_questions(self) -> int:
        statement = select(func.count(Question.id))
        result = await self.session.scalar(statement)
        return int(result or 0)

    async def count_remaining_questions(self) -> int:
        """Return how many questions have never been asked yet."""
        already_asked = select(PromptSession.question_id).distinct()
        statement = select(func.count(Question.id)).where(Question.id.not_in(already_asked))
        result = await self.session.scalar(statement)
        return int(result or 0)

    async def list_asked_questions(self) -> list[PromptSession]:
        """Return every prompt session with its question and answers (including the answering user)."""
        statement = (
            select(PromptSession)
            .options(
                selectinload(PromptSession.question),
                selectinload(PromptSession.answers).selectinload(Answer.user),
            )
            .order_by(PromptSession.created_at.desc())
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def _pick_next_question(self) -> Question | None:
        # Exclude every question that has already been asked (tracked via PromptSession).
        already_asked = select(PromptSession.question_id).distinct()
        statement = (
            select(Question)
            .where(Question.id.not_in(already_asked))
            .order_by(func.random())
            .limit(1)
        )
        question = await self.session.scalar(statement)
        if question is not None:
            return question

        # All questions have been asked at least once – start a new cycle
        # by picking the one that was used the longest time ago.
        fallback = (
            select(Question)
            .order_by(Question.last_used_at.asc())
            .limit(1)
        )
        return await self.session.scalar(fallback)

    @staticmethod
    def _normalize_category(value: object, question_id: int) -> str:
        if pd.isna(value):
            raise ValueError(f"Question {question_id} is missing a category.")

        category = str(value).strip().lower()
        if category not in QUESTION_CATEGORIES:
            allowed = ", ".join(sorted(QUESTION_CATEGORIES))
            raise ValueError(f"Question {question_id} has invalid category '{category}'. Allowed: {allowed}")
        return category
