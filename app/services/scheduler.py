from __future__ import annotations

from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings


class DailyQuestionScheduler:
    def __init__(self, dispatch_callback: Callable[[], Awaitable[None]]) -> None:
        self.settings = get_settings()
        self.dispatch_callback = dispatch_callback
        self.scheduler = AsyncIOScheduler(timezone=self.settings.timezone)
        self.started = False

    def start(self) -> None:
        if self.started:
            return

        self.scheduler.add_job(
            self.dispatch_callback,
            trigger=CronTrigger(
                hour=self.settings.daily_question_hour,
                minute=self.settings.daily_question_minute,
                timezone=self.settings.timezone,
            ),
            id="daily-question",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.start()
        self.started = True

    async def shutdown(self) -> None:
        if not self.started:
            return
        self.scheduler.shutdown(wait=False)
        self.started = False
