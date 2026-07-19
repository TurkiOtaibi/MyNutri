from __future__ import annotations

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

from app.core.config import Settings, get_settings, validate_runtime_configuration
from app.db.session import engine


def repository_head() -> str:
    config = Config("alembic.ini")
    return ScriptDirectory.from_config(config).get_current_head()


def verify_database_compatibility(database_engine: Engine, settings: Settings) -> None:
    validate_runtime_configuration(settings)
    expected_head = repository_head()
    if expected_head is None:
        raise RuntimeError("The repository has no Alembic head.")

    with database_engine.connect() as connection:
        actual_head = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
        if actual_head != expected_head:
            raise RuntimeError(
                f"Unsupported database revision: expected {expected_head}, found {actual_head or 'none'}."
            )

        if settings.environment == "production":
            admin_count = connection.execute(
                text(
                    "SELECT count(*) FROM principal WHERE status='active' "
                    "AND role='admin' AND auth_user_id IS NOT NULL"
                )
            ).scalar_one()
            if admin_count < 1:
                raise RuntimeError("No active linked admin Principal is configured.")


def main() -> None:
    verify_database_compatibility(engine, get_settings())
    print(f"Database preflight passed at {repository_head()}.")


if __name__ == "__main__":
    main()
