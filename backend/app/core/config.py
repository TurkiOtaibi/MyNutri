from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "myNutri API"
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mynutri"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    calendar_timezone: str = "Asia/Riyadh"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    @field_validator("allowed_origins")
    @classmethod
    def normalize_origins(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().rstrip("/") for value in values if value.strip()]
        if "*" in normalized:
            raise ValueError("Wildcard CORS origins are prohibited.")
        return list(dict.fromkeys(normalized))



def validate_runtime_configuration(settings: Settings) -> None:
    if not settings.calendar_timezone:
        raise RuntimeError("CALENDAR_TIMEZONE is required.")
    try:
        ZoneInfo(settings.calendar_timezone)
    except ZoneInfoNotFoundError as error:
        raise RuntimeError("CALENDAR_TIMEZONE must be a recognized IANA timezone.") from error
    if settings.calendar_timezone != "Asia/Riyadh":
        raise RuntimeError("Wave 1 requires CALENDAR_TIMEZONE=Asia/Riyadh.")



@lru_cache
def get_settings() -> Settings:
    return Settings()
