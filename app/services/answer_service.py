from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.answer import ANSWER_RATINGS, Answer
from app.models.prompt_session import PromptSession
from app.models.user import User


class AnswerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_answer(self, user: User, prompt_session: PromptSession, text: str) -> tuple[Answer, bool]:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Answer cannot be empty.")

        statement = select(Answer).where(
            Answer.user_id == user.id,
            Answer.prompt_session_id == prompt_session.id,
        )
        answer = await self.session.scalar(statement)
        created = False
        if answer is None:
            answer = Answer(
                user_id=user.id,
                question_id=prompt_session.question_id,
                prompt_session_id=prompt_session.id,
                text=clean_text,
            )
            self.session.add(answer)
            created = True
        else:
            answer.text = clean_text

        await self.session.commit()
        await self.session.refresh(answer)
        return answer, created

    async def count_group_answers(self, prompt_session_id: int, group_id: int) -> int:
        statement = (
            select(func.count(Answer.id))
            .join(User, User.id == Answer.user_id)
            .where(Answer.prompt_session_id == prompt_session_id, User.group_id == group_id)
        )
        result = await self.session.scalar(statement)
        return int(result or 0)

    async def get_user_answer(self, user_id: int, prompt_session_id: int) -> Answer | None:
        statement = select(Answer).where(
            Answer.user_id == user_id,
            Answer.prompt_session_id == prompt_session_id,
        )
        return await self.session.scalar(statement)

    async def set_answer_rating(self, answer: Answer, rating: str) -> Answer:
        if rating not in ANSWER_RATINGS:
            raise ValueError(f"Unsupported rating: {rating}")

        answer.rating = rating
        await self.session.commit()
        await self.session.refresh(answer)
        return answer

    async def get_group_answers(
        self,
        prompt_session_id: int,
        group_id: int,
        *,
        offset: int = 0,
        limit: int = 1,
        exclude_user_id: int | None = None,
    ) -> tuple[list[Answer], int]:
        filters = [Answer.prompt_session_id == prompt_session_id, User.group_id == group_id]
        if exclude_user_id is not None:
            filters.append(Answer.user_id != exclude_user_id)

        count_statement = (
            select(func.count(Answer.id))
            .join(User, User.id == Answer.user_id)
            .where(*filters)
        )
        total = int((await self.session.scalar(count_statement)) or 0)

        statement = (
            select(Answer)
            .options(selectinload(Answer.user))
            .join(User, User.id == Answer.user_id)
            .where(*filters)
            .order_by(Answer.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        answers = list((await self.session.scalars(statement)).all())
        return answers, total

    async def set_status_message_id(self, answer_id: int, message_id: int | None) -> None:
        answer = await self.session.get(Answer, answer_id)
        if answer is None:
            return

        answer.status_message_id = message_id
        await self.session.commit()

    async def list_group_answers_with_users(self, prompt_session_id: int, group_id: int) -> list[Answer]:
        statement = (
            select(Answer)
            .options(selectinload(Answer.user))
            .join(User, User.id == Answer.user_id)
            .where(Answer.prompt_session_id == prompt_session_id, User.group_id == group_id)
            .order_by(Answer.created_at.asc())
        )
        result = await self.session.scalars(statement)
        return list(result.all())
