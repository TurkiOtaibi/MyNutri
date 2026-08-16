from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import inspect
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import DiaryDayStatus, DiaryDayStatusHistory, Principal
from app.services import diary as diary_service
from app.services.day_logging_status import command_day_status

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
PRINCIPAL = PrincipalContext(PRINCIPAL_ID)
DAY = date(2026, 8, 15)


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL concurrency tests.")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith(
        "mynutri_test_"
    ):
        pytest.fail("PLAN 031 concurrency tests require a disposable mynutri_test_ PostgreSQL database.")
    return url


def _prepare_database(url: str) -> None:
    engine = create_engine(url)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
        text=True,
    )
    engine = create_engine(url)
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()
    engine.dispose()


def test_diary_create_declares_the_frozen_total_lock_order() -> None:
    source = inspect.getsource(diary_service.create_entry)
    symbols = [
        "lock_owner(",
        "resolve_target_binding(",
        "lock_day_for_entry(",
        "lock_food_namespace_for_logging(",
        "get_active_food_for_logging(",
    ]
    offsets = [source.index(symbol) for symbol in symbols]
    assert offsets == sorted(offsets)


@pytest.mark.migration
def test_two_postgresql_completers_serialize_one_transition() -> None:
    url = _database_url()
    _prepare_database(url)
    barrier = Barrier(2)
    authority = diary_calendar_authority(
        datetime(2026, 8, 15, 12, tzinfo=timezone.utc)
    )

    def worker(key: str) -> str:
        engine = create_engine(url)
        try:
            with Session(engine) as session:
                barrier.wait()
                try:
                    command_day_status(
                        session, PRINCIPAL, DAY, "complete", 0, key, authority
                    )
                    return "completed"
                except HTTPException as error:
                    session.rollback()
                    return str(error.detail["code"])
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(worker, ("complete-a", "complete-b")))
    assert outcomes == ["DAY_VERSION_CONFLICT", "completed"]

    engine = create_engine(url)
    with Session(engine) as session:
        day = session.exec(select(DiaryDayStatus)).one()
        history = session.exec(select(DiaryDayStatusHistory)).all()
        assert (day.status, day.version, day.entry_count) == ("complete", 1, 0)
        assert len(history) == 1
    engine.dispose()
