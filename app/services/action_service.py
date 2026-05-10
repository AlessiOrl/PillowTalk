from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.action_assignment import ActionAssignment
from app.models.prompt_session import PromptSession
from app.models.question import QUESTION_CATEGORY_ACTION, Question
from app.models.user import User


class ActionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def assign_action_to_user(
        self,
        user: User,
        prompt_session: PromptSession,
    ) -> ActionAssignment | None:
        """Assign a random action question to a user for this prompt session.

        Returns None if no action questions are available.
        Skips actions the user has already been assigned in any session.
        """
        # Check if already assigned for this session
        existing = await self.session.scalar(
            select(ActionAssignment).where(
                ActionAssignment.prompt_session_id == prompt_session.id,
                ActionAssignment.user_id == user.id,
            )
        )
        if existing is not None:
            return existing

        # Get all action question ids already assigned to this user (ever)
        already_assigned = (
            select(ActionAssignment.question_id)
            .where(ActionAssignment.user_id == user.id)
            .distinct()
        )

        statement = (
            select(Question)
            .where(
                Question.category == QUESTION_CATEGORY_ACTION,
                Question.id.not_in(already_assigned),
            )
            .order_by(func.random())
            .limit(1)
        )
        question = await self.session.scalar(statement)

        if question is None:
            # All actions exhausted for this user — pick any action at random
            question = await self.session.scalar(
                select(Question)
                .where(Question.category == QUESTION_CATEGORY_ACTION)
                .order_by(func.random())
                .limit(1)
            )

        if question is None:
            return None

        assignment = ActionAssignment(
            prompt_session_id=prompt_session.id,
            user_id=user.id,
            question_id=question.id,
        )
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def get_user_assignment(
        self,
        user_id: int,
        prompt_session_id: int,
    ) -> ActionAssignment | None:
        statement = (
            select(ActionAssignment)
            .options(selectinload(ActionAssignment.question))
            .where(
                ActionAssignment.user_id == user_id,
                ActionAssignment.prompt_session_id == prompt_session_id,
            )
        )
        return await self.session.scalar(statement)

    async def mark_completed(self, assignment_id: int) -> ActionAssignment | None:
        assignment = await self.session.get(ActionAssignment, assignment_id)
        if assignment is None:
            return None

        assignment.completed = True
        assignment.completed_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def list_completed_group_actions(
        self,
        prompt_session_id: int,
        group_id: int,
    ) -> list[ActionAssignment]:
        """Return completed action assignments for a group, with user and question loaded."""
        statement = (
            select(ActionAssignment)
            .options(
                selectinload(ActionAssignment.user),
                selectinload(ActionAssignment.question),
            )
            .join(User, User.id == ActionAssignment.user_id)
            .where(
                ActionAssignment.prompt_session_id == prompt_session_id,
                ActionAssignment.completed.is_(True),
                User.group_id == group_id,
            )
            .order_by(ActionAssignment.completed_at.asc())
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def count_completed_group_actions(
        self,
        prompt_session_id: int,
        group_id: int,
    ) -> int:
        statement = (
            select(func.count(ActionAssignment.id))
            .join(User, User.id == ActionAssignment.user_id)
            .where(
                ActionAssignment.prompt_session_id == prompt_session_id,
                ActionAssignment.completed.is_(True),
                User.group_id == group_id,
            )
        )
        result = await self.session.scalar(statement)
        return int(result or 0)
