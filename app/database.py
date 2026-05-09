from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
database_path = settings.resolved_database_path
if database_path is not None:
    database_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    session = SessionLocal()
    try:
        yield session
    finally:
        await session.close()


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_ensure_answer_status_message_id_column)
        await connection.run_sync(_ensure_user_prompt_tracking_columns)


def _ensure_answer_status_message_id_column(connection) -> None:
    inspector = inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("answers")}
    if "status_message_id" in columns:
        return

    connection.execute(text("ALTER TABLE answers ADD COLUMN status_message_id INTEGER"))


def _ensure_user_prompt_tracking_columns(connection) -> None:
    inspector = inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("users")}

    if "last_prompt_session_id" not in columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN last_prompt_session_id INTEGER"))
    if "last_prompt_message_id" not in columns:
        connection.execute(text("ALTER TABLE users ADD COLUMN last_prompt_message_id INTEGER"))
