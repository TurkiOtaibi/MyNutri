from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import inspect
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier, Event
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import (
    DiaryDayStatus,
    DiaryDayStatusValue,
    NutritionAnalysisCommandIdempotency,
    NutritionAnalysisRevision,
    NutritionAnalysisRevisionEvent,
    Principal,
)
from app.schemas import AnalysisEvaluateCommandV1
from app.services import pattern_analysis
from app.services.day_logging_status import command_day_status
from app.services.pattern_analysis import PatternAnalysisError, evaluate_analysis


PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000321")
PRINCIPAL = PrincipalContext(PRINCIPAL_ID)
AUTHORITY = diary_calendar_authority(datetime(2026, 8, 17, 9, tzinfo=timezone.utc))


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PLAN 032 PostgreSQL concurrency tests.")
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith("mynutri_test_"):
        pytest.fail("PLAN 032 concurrency tests require a disposable mynutri_test_ PostgreSQL database.")
    return url


def _prepare(url: str) -> None:
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
        session.flush()
        for offset in range(5):
            session.add(
                DiaryDayStatus(
                    principal_id=PRINCIPAL_ID,
                    diary_date=AUTHORITY.current_diary_date - timedelta(days=offset),
                    status=DiaryDayStatusValue.complete,
                    version=1,
                    entry_count=0,
                    completed_at=datetime(2026, 8, 17, 8, tzinfo=timezone.utc),
                )
            )
        session.commit()
    engine.dispose()
    pattern_analysis.diary_calendar_authority = lambda: AUTHORITY


def test_evaluation_declares_frozen_principal_series_day_lock_order() -> None:
    source = inspect.getsource(pattern_analysis.evaluate_analysis)
    assert source.index("select(Principal)") < source.index("select(NutritionAnalysis)")
    source_builder = inspect.getsource(pattern_analysis._build_source)
    assert source_builder.index("select(DiaryDayStatus)") < source_builder.index("select(DiaryEntry)")


@pytest.mark.migration
def test_two_same_date_evaluations_serialize_revision_creation() -> None:
    url = _database_url()
    _prepare(url)
    barrier = Barrier(2)

    def worker(key: str) -> str:
        engine = create_engine(url)
        try:
            with Session(engine) as session:
                barrier.wait()
                try:
                    _, status, _ = evaluate_analysis(
                        session,
                        PRINCIPAL,
                        AnalysisEvaluateCommandV1(expected_current_revision=None),
                        key,
                        '"analysis-none"',
                    )
                    return str(status)
                except PatternAnalysisError as error:
                    return error.code
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = sorted(executor.map(worker, ("evaluation-a", "evaluation-b")))
    assert outcomes == ["201", "ANALYSIS_VERSION_CONFLICT"]
    engine = create_engine(url)
    with Session(engine) as session:
        assert len(session.exec(select(NutritionAnalysisRevision)).all()) == 1
    engine.dispose()


@pytest.mark.migration
def test_concurrent_identical_command_has_one_revision_and_exact_replay() -> None:
    url = _database_url()
    _prepare(url)
    barrier = Barrier(2)

    def worker() -> tuple[int, bool, str]:
        engine = create_engine(url)
        try:
            with Session(engine) as session:
                barrier.wait()
                response, status, replayed = evaluate_analysis(
                    session,
                    PRINCIPAL,
                    AnalysisEvaluateCommandV1(expected_current_revision=None),
                    "same-command",
                    '"analysis-none"',
                )
                return status, replayed, response.source_versions.content_hash
        finally:
            engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: worker(), range(2)))
    assert sorted((status, replayed) for status, replayed, _ in outcomes) == [(201, False), (201, True)]
    assert len({content_hash for _, _, content_hash in outcomes}) == 1
    engine = create_engine(url)
    with Session(engine) as session:
        assert len(session.exec(select(NutritionAnalysisRevision)).all()) == 1
        assert len(session.exec(select(NutritionAnalysisCommandIdempotency)).all()) == 1
    engine.dispose()


@pytest.mark.migration
def test_reopen_and_evaluation_serialize_without_losing_stale_event() -> None:
    url = _database_url()
    _prepare(url)
    engine = create_engine(url)
    with Session(engine) as session:
        first, _, _ = evaluate_analysis(
            session,
            PRINCIPAL,
            AnalysisEvaluateCommandV1(expected_current_revision=None),
            "initial",
            '"analysis-none"',
        )
    engine.dispose()
    owner_locked = Event()
    evaluation_attempted = Event()

    def reopen() -> str:
        worker_engine = create_engine(url)
        try:
            with Session(worker_engine) as session:
                session.exec(
                    select(Principal)
                    .where(Principal.id == PRINCIPAL_ID)
                    .with_for_update()
                ).one()
                owner_locked.set()
                assert evaluation_attempted.wait(timeout=10)
                command_day_status(
                    session,
                    PRINCIPAL,
                    AUTHORITY.current_diary_date,
                    "reopen",
                    1,
                    "reopen-analysis-day",
                    AUTHORITY,
                )
                return "reopened"
        finally:
            worker_engine.dispose()

    def evaluate() -> str:
        worker_engine = create_engine(url)

        @event.listens_for(worker_engine, "before_cursor_execute")
        def observe_owner_lock(
            _connection,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
        ):
            if "FROM principal" in statement and "FOR UPDATE" in statement:
                evaluation_attempted.set()

        try:
            with Session(worker_engine) as session:
                assert owner_locked.wait(timeout=10)
                try:
                    _, status, _ = evaluate_analysis(
                        session,
                        PRINCIPAL,
                        AnalysisEvaluateCommandV1(expected_current_revision=1),
                        "racing-evaluation",
                        first.etag,
                    )
                    return str(status)
                except PatternAnalysisError as error:
                    return error.code
        finally:
            worker_engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        reopen_future = executor.submit(reopen)
        evaluate_future = executor.submit(evaluate)
        outcomes = {reopen_future.result(), evaluate_future.result()}
    assert outcomes == {"reopened", "201"}
    engine = create_engine(url)
    with Session(engine) as session:
        events = session.exec(select(NutritionAnalysisRevisionEvent)).all()
        assert sum(event.event_type == "day_reopened" for event in events) == 1
        assert sum(event.event_type == "superseded_by_revision" for event in events) == 1
        assert len(session.exec(select(NutritionAnalysisRevision)).all()) == 2
    engine.dispose()
