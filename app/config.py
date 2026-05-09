from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PillowTalk"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_base_url: str = "http://localhost:8000"

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    admin_telegram_id: int | None = Field(default=None, alias="ADMIN_TELEGRAM_ID")
    admin_api_token: str = Field(default="change-me", alias="ADMIN_API_TOKEN")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/pillowtalk.db",
        alias="DATABASE_URL",
    )

    questions_csv_path: str = Field(
        default="data/questions.csv",
        alias="QUESTIONS_CSV_PATH",
    )
    question_cooldown_days: int = Field(default=30, alias="QUESTION_COOLDOWN_DAYS")
    answer_feed_page_size: int = Field(default=1, alias="ANSWER_FEED_PAGE_SIZE")

    daily_question_hour: int = Field(default=21, alias="DAILY_QUESTION_HOUR")
    daily_question_minute: int = Field(default=0, alias="DAILY_QUESTION_MINUTE")
    timezone: str = Field(default="Europe/Rome", alias="TIMEZONE")

    message_parse_mode: str = "HTML"
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def resolved_questions_csv_path(self) -> Path:
        path = Path(self.questions_csv_path)
        if path.is_absolute():
            return path
        return BASE_DIR / path

    @property
    def resolved_database_path(self) -> Path | None:
        parsed = urlsplit(self.database_url)
        if parsed.scheme not in {"sqlite", "sqlite+aiosqlite"}:
            return None

        database_path = parsed.path
        if not database_path or database_path == ":memory:":
            return None

        resolved_path = Path(database_path)
        if resolved_path.is_absolute():
            return resolved_path

        trimmed_path = database_path.lstrip("/")
        if not trimmed_path or trimmed_path == ":memory:":
            return None

        return BASE_DIR / trimmed_path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
