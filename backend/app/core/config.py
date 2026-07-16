from functools import lru_cache
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")


class Settings(BaseSettings):
    app_name: str = "myNutri API"
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mynutri"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    single_user_token: str = "dev-token"
    previous_single_user_tokens: list[str] = Field(default_factory=list)
    deployment_principal_id: UUID | None = None
    principal_token_map: dict[str, UUID] = Field(default_factory=dict)

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    def credential_map(self) -> dict[str, UUID]:
        if self.principal_token_map:
            return dict(self.principal_token_map)

        principal_id = self.deployment_principal_id
        if principal_id is None and self.environment in {"dev", "test"}:
            principal_id = DEV_PRINCIPAL_ID
        if principal_id is None:
            return {}

        tokens = [self.single_user_token, *self.previous_single_user_tokens]
        return {token: principal_id for token in tokens if token.strip()}


def validate_runtime_configuration(settings: Settings) -> None:
    if settings.environment != "production":
        return

    if settings.deployment_principal_id is None:
        raise RuntimeError("DEPLOYMENT_PRINCIPAL_ID is required in production.")
    if not settings.single_user_token.strip():
        raise RuntimeError("SINGLE_USER_TOKEN is required in production.")
    if settings.principal_token_map:
        raise RuntimeError("PRINCIPAL_TOKEN_MAP is test-only and prohibited in production.")

    mapped_principals = set(settings.credential_map().values())
    if mapped_principals != {settings.deployment_principal_id}:
        raise RuntimeError("Production credentials must map to the deployment Principal only.")


@lru_cache
def get_settings() -> Settings:
    return Settings()
