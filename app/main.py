from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

import app.models  # noqa: F401
from app.bot.handlers import pillowtalkBot
from app.config import get_settings
from app.database import create_tables, get_session
from app.routers.admin import router as admin_router
from app.services.question_service import QuestionService
from app.services.scheduler import DailyQuestionScheduler

settings = get_settings()


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger = logging.getLogger(__name__)

    await create_tables()

    async with get_session() as session:
        question_service = QuestionService(session)
        csv_path = Path(settings.resolved_questions_csv_path)
        if csv_path.exists():
            imported = await question_service.import_questions_from_csv(str(csv_path))
            logger.info("Imported %s questions from %s", imported, csv_path)
        else:
            logger.warning("Questions CSV not found at %s", csv_path)

    async def _reimport_questions() -> int:
        csv_path = Path(settings.resolved_questions_csv_path)
        if not csv_path.exists():
            logger.warning("Questions CSV not found at %s", csv_path)
            return 0
        async with get_session() as sess:
            count = await QuestionService(sess).import_questions_from_csv(str(csv_path))
        logger.info("Re-imported %s questions from %s", count, csv_path)
        return count

    bot_service = pillowtalkBot()

    async def scheduled_dispatch() -> None:
        await _reimport_questions()
        await bot_service.dispatch_next_prompt(force_new=False, source="scheduled")

    scheduler = DailyQuestionScheduler(scheduled_dispatch)
    app.state.bot_service = bot_service
    app.state.scheduler = scheduler

    app.state.reimport_questions = _reimport_questions

    await bot_service.start()
    scheduler.start()
    try:
        yield
    finally:
        await scheduler.shutdown()
        await bot_service.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(admin_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"app": settings.app_name, "status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
