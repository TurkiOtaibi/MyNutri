from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "myNutri API"
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mynutri"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    supabase_url: str = ""
    supabase_jwks_url: str = ""
    supabase_jwt_audience: str = "authenticated"
    calendar_timezone: str = "Asia/Riyadh"
    snapshot_v3_writer_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    @field_validator("allowed_origins")
    @classmethod
    def normalize_origins(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().rstrip("/") for value in values if value.strip()]
        if "*" in normalized:
            raise ValueError("Wildcard CORS origins are prohibited.")
        return list(dict.fromkeys(normalized))

    @property
    def normalized_supabase_url(self) -> str:
        return self.supabase_url.strip().rstrip("/")

    @property
    def expected_supabase_issuer(self) -> str:
        return f"{self.normalized_supabase_url}/auth/v1"

    @property
    def effective_supabase_jwks_url(self) -> str:
        configured = self.supabase_jwks_url.strip()
        if configured:
            return configured
        return f"{self.expected_supabase_issuer}/.well-known/jwks.json"


def validate_runtime_configuration(settings: Settings) -> None:
    if not settings.calendar_timezone:
        raise RuntimeError("CALENDAR_TIMEZONE is required.")
    try:
        ZoneInfo(settings.calendar_timezone)
    except ZoneInfoNotFoundError as error:
        raise RuntimeError("CALENDAR_TIMEZONE must be a recognized IANA timezone.") from error
    if settings.calendar_timezone != "Asia/Riyadh":
        raise RuntimeError("Wave 1 requires CALENDAR_TIMEZONE=Asia/Riyadh.")

    if settings.environment != "production":
        return

    if not settings.normalized_supabase_url.startswith("https://"):
        raise RuntimeError("SUPABASE_URL must be an HTTPS URL in production.")
    if not settings.supabase_jwt_audience.strip():
        raise RuntimeError("SUPABASE_JWT_AUDIENCE is required in production.")
    if not settings.effective_supabase_jwks_url.startswith("https://"):
        raise RuntimeError("SUPABASE_JWKS_URL must be HTTPS in production.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
