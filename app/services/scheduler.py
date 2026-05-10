from __future__ import annotations

from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import get_session
from app.services.app_settings_service import AppSettingsService


class DailyQuestionScheduler:
    def __init__(self, dispatch_callback: Callable[[], Awaitable[None]]) -> None:
        self.settings = get_settings()
        self.dispatch_callback = dispatch_callback
        self.scheduler = AsyncIOScheduler(timezone=self.settings.timezone)
        self.started = False
        self.current_hour = self.settings.daily_question_hour
        self.current_minute = self.settings.daily_question_minute

    async def start(self) -> None:
        if self.started:
            return

        async with get_session() as session:
            settings_service = AppSettingsService(session)
            hour, minute = await settings_service.get_daily_question_time(
                default_hour=self.settings.daily_question_hour,
                default_minute=self.settings.daily_question_minute,
            )

        self.set_daily_time(hour=hour, minute=minute)
        self.scheduler.start()
        self.started = True

    def set_daily_time(self, *, hour: int, minute: int) -> None:
        self.current_hour = hour
        self.current_minute = minute
        self.settings.daily_question_hour = hour
        self.settings.daily_question_minute = minute
        self.scheduler.add_job(
            self.dispatch_callback,
            trigger=CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.settings.timezone,
            ),
            id="daily-question",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )

    def get_daily_time(self) -> tuple[int, int]:
        return self.current_hour, self.current_minute

    async def shutdown(self) -> None:
        if not self.started:
            return
        self.scheduler.shutdown(wait=False)
        self.started = False
