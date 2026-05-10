from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting

DAILY_QUESTION_HOUR_KEY = "daily_question_hour"
DAILY_QUESTION_MINUTE_KEY = "daily_question_minute"


class AppSettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_daily_question_time(self, *, default_hour: int, default_minute: int) -> tuple[int, int]:
        hour_setting = await self.session.get(AppSetting, DAILY_QUESTION_HOUR_KEY)
        minute_setting = await self.session.get(AppSetting, DAILY_QUESTION_MINUTE_KEY)

        hour = self._parse_int(hour_setting.value if hour_setting is not None else None, default_hour)
        minute = self._parse_int(minute_setting.value if minute_setting is not None else None, default_minute)
        return hour, minute

    async def set_daily_question_time(self, *, hour: int, minute: int) -> None:
        await self._set_value(DAILY_QUESTION_HOUR_KEY, str(hour))
        await self._set_value(DAILY_QUESTION_MINUTE_KEY, str(minute))
        await self.session.commit()

    async def _set_value(self, key: str, value: str) -> None:
        setting = await self.session.get(AppSetting, key)
        if setting is None:
            self.session.add(AppSetting(key=key, value=value))
            return
        setting.value = value

    @staticmethod
    def _parse_int(value: str | None, default: int) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default