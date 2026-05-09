from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        statement = select(User).where(User.telegram_id == telegram_id)
        return await self.session.scalar(statement)

    async def register_user(
        self,
        telegram_id: int,
        username: str | None,
        display_name: str | None,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(telegram_id)
        created = False
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                display_name=display_name,
                is_admin=telegram_id == self.settings.admin_telegram_id,
            )
            self.session.add(user)
            created = True
        else:
            user.username = username
            user.display_name = display_name
            if self.settings.admin_telegram_id is not None:
                user.is_admin = telegram_id == self.settings.admin_telegram_id

        await self.session.commit()
        await self.session.refresh(user)
        return user, created

    async def list_users(self) -> list[User]:
        statement = select(User).order_by(User.joined_at.asc())
        result = await self.session.scalars(statement)
        return list(result.all())

    async def update_streak(self, user: User, answered_on: date) -> User:
        if user.last_answer_date == answered_on:
            return user

        if user.last_answer_date == answered_on - timedelta(days=1):
            user.streak += 1
        else:
            user.streak = 1

        user.last_answer_date = answered_on
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def break_streak(self, user: User) -> User:
        user.streak = 0
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def join_group(self, user: User, group_id: int) -> User:
        user.group_id = group_id
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def leave_group(self, user: User) -> User:
        user.group_id = None
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def set_last_prompt_message(self, user: User, prompt_session_id: int, message_id: int) -> User:
        user.last_prompt_session_id = prompt_session_id
        user.last_prompt_message_id = message_id
        await self.session.commit()
        await self.session.refresh(user)
        return user
