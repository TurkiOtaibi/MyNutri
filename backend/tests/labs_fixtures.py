"""Opt-in synthetic PostgreSQL fixtures for Labs and concurrent service tests."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session

from app.models import ActivityLevel, Goal, Principal, Profile, Sex


BACKEND_ROOT = Path(__file__).parents[1]


def safe_labs_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for disposable PostgreSQL tests.")
    parsed = make_url(url)
    if (
        parsed.get_backend_name() != "postgresql"
        or parsed.host not in {"127.0.0.1", "localhost", "::1"}
        or not (parsed.database or "").startswith("mynutri_test_")
    ):
        pytest.fail("Labs tests require a disposable loopback mynutri_test_ database.")
    return url


def run_labs_alembic(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    url = safe_labs_database_url()
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_ROOT,
        env={**os.environ, "DATABASE_URL": url},
        capture_output=True,
        text=True,
    )
    if check and result.returncode:
        # Suppress any connection credentials before surfacing migration diagnostics.
        diagnostic = (result.stdout + result.stderr).replace(url, "<disposable database>")
        pytest.fail(f"Alembic {arguments} failed ({result.returncode}):\n{diagnostic}")
    return result


def reset_labs_database() -> None:
    engine = create_engine(safe_labs_database_url())
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS nova_retirement CASCADE"))
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


@dataclass(frozen=True)
class LabsPostgresqlDatabase:
    engine: Engine
    url: str = field(repr=False)


@pytest.fixture(scope="module")
def _labs_migrated_database() -> Iterator[LabsPostgresqlDatabase]:
    """Exclusive disposable database; callers may open independent committing sessions."""
    url = safe_labs_database_url()
    reset_labs_database()
    run_labs_alembic("upgrade", "head")
    engine = create_engine(url)
    try:
        yield LabsPostgresqlDatabase(engine=engine, url=url)
    finally:
        engine.dispose()
        reset_labs_database()
        run_labs_alembic("upgrade", "head")


@pytest.fixture
def labs_postgresql_database(_labs_migrated_database) -> Iterator[LabsPostgresqlDatabase]:
    """Each test owns synthetic rows; preserve real migrations between tests."""
    database = _labs_migrated_database
    try:
        yield database
    finally:
        safe_labs_database_url()
        with database.engine.begin() as connection:
            tables = inspect(connection).get_table_names()
            # TRUNCATE bypasses immutable-row DELETE triggers only in this disposable fixture.
            names = [
                connection.dialect.identifier_preparer.quote(name)
                for name in tables
                if name != "alembic_version"
            ]
            if names:
                connection.execute(text("TRUNCATE " + ", ".join(names) + " CASCADE"))
        run_labs_alembic("upgrade", "head")


@pytest.fixture
def labs_postgresql_session(labs_postgresql_database) -> Iterator[Session]:
    with Session(labs_postgresql_database.engine) as session:
        yield session


@pytest.fixture
def lab_owner(labs_postgresql_session) -> Principal:
    owner = Principal(auth_user_id=uuid4(), email=f"labs-{uuid4()}@example.test")
    labs_postgresql_session.add(owner)
    labs_postgresql_session.flush()
    labs_postgresql_session.add(
        Profile(
            principal_id=owner.id,
            sex=Sex.female,
            birth_date=date(1990, 1, 1),
            height_cm=165,
            weight_kg=65,
            activity_level=ActivityLevel.light,
            goal=Goal.maintain,
        )
    )
    labs_postgresql_session.commit()
    labs_postgresql_session.refresh(owner)
    return owner


@pytest.fixture
def lab_result(labs_postgresql_session, lab_owner):
    """Approved synthetic default: HbA1c 5.2% on September 19."""
    from decimal import Decimal
    from app.models import LabResult

    row = LabResult(
        principal_id=lab_owner.id,
        test_key="hba1c",
        test_date=date(2026, 9, 19),
        entered_value=Decimal("5.2"),
        entered_unit="%",
    )
    labs_postgresql_session.add(row)
    labs_postgresql_session.commit()
    labs_postgresql_session.refresh(row)
    return row


@pytest.fixture
def two_dated_results(labs_postgresql_session, lab_owner):
    from decimal import Decimal
    from types import SimpleNamespace
    from app.models import LabResult

    rows = [
        LabResult(
            principal_id=lab_owner.id,
            test_key="hba1c",
            test_date=day,
            entered_value=Decimal("5.2"),
            entered_unit="%",
        )
        for day in (date(2026, 7, 1), date(2026, 9, 1))
    ]
    labs_postgresql_session.add_all(rows)
    labs_postgresql_session.commit()
    return SimpleNamespace(first_id=rows[0].id, second_id=rows[1].id, second_date=rows[1].test_date)


@pytest.fixture
def get_result_fact(labs_postgresql_session, lab_owner):
    from sqlmodel import select
    from app.models import LabResult

    def read(result_id):
        return labs_postgresql_session.exec(
            select(LabResult)
            .where(LabResult.id == result_id, LabResult.principal_id == lab_owner.id)
            .execution_options(populate_existing=True)
        ).one_or_none()

    return read


@pytest.fixture
def seeded_lab_history(labs_postgresql_session, lab_owner):
    from datetime import datetime, timezone
    from decimal import Decimal
    from types import SimpleNamespace
    from app.models import LabResult

    january_updated_at = datetime(2026, 9, 20, 10, tzinfo=timezone.utc)
    rows = [
        LabResult(
            principal_id=lab_owner.id,
            test_key="hba1c",
            test_date=date(2026, 1, 1),
            entered_value=Decimal("5.2"),
            entered_unit="%",
            updated_at=january_updated_at,
        ),
        LabResult(
            principal_id=lab_owner.id,
            test_key="hba1c",
            test_date=date(2026, 9, 1),
            entered_value=Decimal("5.7"),
            entered_unit="%",
            updated_at=datetime(2026, 9, 1, 10, tzinfo=timezone.utc),
        ),
    ]
    labs_postgresql_session.add_all(rows)
    labs_postgresql_session.commit()
    return SimpleNamespace(
        session=labs_postgresql_session,
        owner_id=lab_owner.id,
        january_updated_at=january_updated_at,
    )
