from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import (
    BehaviorGoal,
    BehaviorGoalCommandIdempotency,
    BehaviorGoalHistory,
    NutritionAnalysis,
    NutritionAnalysisRevision,
    Principal,
    WeeklyPriorityRecommendation,
)
from app.schemas import BehaviorGoalCommandV1
from app.services.weekly_priorities import (
    WeeklyPriorityError,
    command_goal,
    evaluate_recommendation,
)
from test_weekly_priorities import _persisted_producer_document

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000333")
PRINCIPAL = PrincipalContext(PRINCIPAL_ID)


def _url() -> str:
    value = os.environ.get("TEST_DATABASE_URL", "")
    parsed = make_url(value) if value else None
    if parsed is None:
        pytest.skip("TEST_DATABASE_URL is required for PLAN 033 PostgreSQL concurrency tests.")
    if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith(
        "mynutri_test_"
    ):
        pytest.fail("PLAN 033 concurrency tests require a disposable mynutri_test_ database.")
    return value


def _prepare() -> str:
    url = _url()
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
    return url


def _seed_goal(url: str, state: str = "offered") -> UUID:
    engine = create_engine(url)
    analysis_id, revision_id, goal_id = uuid4(), uuid4(), uuid4()
    document = _persisted_producer_document(PRINCIPAL_ID, analysis_id)
    for day in document["days"]:
        if day["logging_status"] == "complete":
            day["metric_values"] = [{
                "metric_key": "nutrient:trans_fat_g",
                "value": 1,
                "value_state": "known",
                "known_entry_count": 1,
                "total_entry_count": 1,
                "amount_qualifier": "exact",
                "unit": "g",
            }]
    metric = document["metric_facts"][0]
    metric.update({
        "metric_key": "nutrient:trans_fat_g",
        "unit": "g",
        "direction": "maximum",
        "target": {
            "type": "maximum",
            "value": 0.1,
            "lower": None,
            "upper": None,
            "source_plan_ids": [],
        },
    })
    metric["current"].update({"value": 1, "status": "above_target"})
    canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()
        series = NutritionAnalysis(
            id=analysis_id,
            principal_id=PRINCIPAL_ID,
            as_of_diary_date=date.fromisoformat(document["as_of_diary_date"]),
            calendar_timezone="Asia/Riyadh",
        )
        session.add(series)
        session.commit()
        session.add(
            NutritionAnalysisRevision(
                id=revision_id,
                analysis_id=analysis_id,
                principal_id=PRINCIPAL_ID,
                revision=1,
                period_start=date.fromisoformat(document["period_start"]),
                period_end=date.fromisoformat(document["period_end"]),
                previous_period_start=date.fromisoformat(document["previous_period_start"]),
                previous_period_end=date.fromisoformat(document["previous_period_end"]),
                analysis_rules_version="w3-analysis-1.1.0",
                source_versions={
                    "calculation_engine_version": "2.0.0",
                    "source_reliability_rules_version": "1.0.0",
                    "status_evidence_version": "1",
                    "rules_manifest_hash": "0" * 64,
                },
                source_input_hash="1" * 64,
                content_hash=hashlib.sha256(canonical.encode()).hexdigest(),
                complete_day_count=4,
                previous_complete_day_count=0,
                result_status="available",
                analysis_document=document,
            )
        )
        session.commit()
        series.current_revision_id = revision_id
        series.current_revision_number = 1
        session.add(series)
        session.commit()
        recommendation = evaluate_recommendation(session, PRINCIPAL)
        now = datetime.now(timezone.utc)
        window_start = date.fromisoformat(document["period_start"])
        window_end = date.fromisoformat(document["period_end"])
        assert recommendation.main is not None
        assert recommendation.main.goal_trackability == "trackable"
        progress_status = "not_yet_reached" if state == "incomplete" else "unknown"
        session.add(
            BehaviorGoal(
                id=goal_id,
                principal_id=PRINCIPAL_ID,
                recommendation_id=recommendation.recommendation_id,
                root_goal_id=goal_id,
                sequence_number=1,
                state=state,
                version=1,
                rule_key=recommendation.main.rule_key,
                action_key=recommendation.main.action_key,
                weekly_target_count=3,
                day_mask=[],
                window_start=window_start,
                window_end=window_end,
                rules_version="w3-priority-1.1.0",
                copy_version="w3-priority-ar-1.1.0",
                progress_document={
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "progress_count": 1,
                    "target_count": 3,
                    "progress_percent": 33,
                    "complete_day_count": 4,
                    "partial_day_count": 0,
                    "unregistered_day_count": 3,
                    "status": progress_status,
                    "as_of_diary_date": window_end.isoformat(),
                    "source_day_versions": {},
                    "calculation_rules_version": "w3-priority-1.1.0",
                    "last_recomputed_at": now.isoformat(),
                },
                progress_revision=1,
                reminder_preference="disabled",
                reviewed_at=now if state == "incomplete" else None,
            )
        )
        session.commit()
    engine.dispose()
    return goal_id


def _run(url: str, goal_id: UUID, key: str, command: BehaviorGoalCommandV1, barrier: Barrier):
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            barrier.wait()
            try:
                response, status, replayed = command_goal(session, PRINCIPAL, goal_id, command, key)
                return status, replayed, response.result
            except WeeklyPriorityError as error:
                return error.status_code, False, error.code
    finally:
        engine.dispose()


def _run_evaluation(url: str, barrier: Barrier):
    engine = create_engine(url)
    try:
        with Session(engine) as session:
            barrier.wait()
            result = evaluate_recommendation(session, PRINCIPAL)
            return result.recommendation_id, result.etag
    finally:
        engine.dispose()


@pytest.mark.migration
def test_duplicate_recommendation_evaluation_has_one_authoritative_result() -> None:
    url = _prepare()
    _seed_goal(url)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM behavior_goal_command_idempotency"))
        connection.execute(text("DELETE FROM behavior_goal_history"))
        connection.execute(text("DELETE FROM behavior_goal"))
        connection.execute(text("DELETE FROM weekly_priority_evaluation"))
        connection.execute(text("DELETE FROM weekly_priority_evidence_ref"))
        connection.execute(text("DELETE FROM weekly_priority_recommendation"))
    engine.dispose()
    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: _run_evaluation(url, barrier), range(2)))
    assert outcomes[0] == outcomes[1]
    engine = create_engine(url)
    with Session(engine) as session:
        recommendations = session.exec(select(WeeklyPriorityRecommendation)).all()
        assert len(recommendations) == 1
    engine.dispose()


@pytest.mark.migration
def test_duplicate_accept_replays_one_authoritative_response() -> None:
    url = _prepare()
    goal_id = _seed_goal(url)
    barrier = Barrier(2)
    command = BehaviorGoalCommandV1(event="accept", expected_version=1)
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: _run(url, goal_id, "same-key", command, barrier), range(2)))
    assert sorted(outcomes) == [(200, False, "accepted"), (200, True, "accepted")]
    engine = create_engine(url)
    with Session(engine) as session:
        assert len(session.exec(select(BehaviorGoalHistory)).all()) == 1
        assert len(session.exec(select(BehaviorGoalCommandIdempotency)).all()) == 1
    engine.dispose()


@pytest.mark.migration
def test_concurrent_accepts_allow_only_one_primary_transition() -> None:
    url = _prepare()
    goal_id = _seed_goal(url)
    barrier = Barrier(2)
    command = BehaviorGoalCommandV1(event="accept", expected_version=1)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_run, url, goal_id, key, command, barrier)
            for key in ("accept-a", "accept-b")
        ]
        outcomes = sorted(future.result() for future in futures)
    assert outcomes == [(200, False, "accepted"), (409, False, "GOAL_VERSION_CONFLICT")]


@pytest.mark.migration
def test_concurrent_repeat_and_reduce_create_at_most_one_successor() -> None:
    url = _prepare()
    goal_id = _seed_goal(url, "incomplete")
    barrier = Barrier(2)
    same = BehaviorGoalCommandV1(event="repeat", repeat_mode="same", expected_version=1)
    reduced = BehaviorGoalCommandV1(
        event="repeat", repeat_mode="reduce", weekly_target_count=2, expected_version=1
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [
            executor.submit(_run, url, goal_id, "repeat-same", same, barrier),
            executor.submit(_run, url, goal_id, "repeat-reduce", reduced, barrier),
        ]
        results = [future.result() for future in outcomes]
    assert sum(result[0] == 200 for result in results) == 1
    assert {result[2] for result in results} <= {
        "repeated",
        "reduced_and_repeated",
        "PRIMARY_GOAL_EXISTS",
        "GOAL_VERSION_CONFLICT",
    }
    engine = create_engine(url)
    with Session(engine) as session:
        successors = session.exec(select(BehaviorGoal).where(BehaviorGoal.previous_goal_id == goal_id)).all()
        assert len(successors) == 1
        source = session.get(BehaviorGoal, goal_id)
        assert source is not None and source.state == "incomplete" and source.version == 1
    engine.dispose()
