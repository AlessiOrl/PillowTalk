from __future__ import annotations

import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import Group
from app.models.user import User


class GroupService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_group(self, name: str, created_by: int | None) -> Group:
        invite_code = await self._generate_invite_code()
        group = Group(name=name.strip(), invite_code=invite_code, created_by=created_by)
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def list_groups(self) -> list[tuple[Group, int]]:
        statement = (
            select(Group, func.count(User.id))
            .outerjoin(User, User.group_id == Group.id)
            .group_by(Group.id)
            .order_by(Group.created_at.asc())
        )
        result = await self.session.execute(statement)
        return [(group, member_count) for group, member_count in result.all()]

    async def get_group_by_code(self, invite_code: str) -> Group | None:
        statement = select(Group).where(Group.invite_code == invite_code.upper())
        return await self.session.scalar(statement)

    async def get_group_by_id(self, group_id: int) -> Group | None:
        return await self.session.get(Group, group_id)

    async def get_member_count(self, group_id: int) -> int:
        statement = select(func.count(User.id)).where(User.group_id == group_id)
        result = await self.session.scalar(statement)
        return int(result or 0)

    async def add_member(self, group: Group, user: User) -> User:
        user.group_id = group.id
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def list_group_members(self, group_id: int) -> list[User]:
        statement = (
            select(User)
            .where(User.group_id == group_id)
            .order_by(User.display_name.asc().nullslast(), User.username.asc().nullslast(), User.id.asc())
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def add_member_by_telegram_id(self, telegram_id: int, group: Group) -> User | None:
        statement = select(User).where(User.telegram_id == telegram_id)
        user = await self.session.scalar(statement)
        if user is None:
            return None

        user.group_id = group.id
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def remove_member(self, user: User) -> User:
        user.group_id = None
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def _generate_invite_code(self, length: int = 8) -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(length))
            existing = await self.get_group_by_code(code)
            if existing is None:
                return code
