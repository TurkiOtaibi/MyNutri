from datetime import date, datetime, timezone
from copy import deepcopy
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import Principal
from app.services.day_logging_status import (
    command_day_status,
    evaluate_status_event,
    project_day_status,
)
from app.services.target_plans import resolve_target_binding


@pytest.fixture
def day_session() -> tuple[Session, PrincipalContext]:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    principal = Principal()
    session.add(principal)
    session.commit()
    yield session, PrincipalContext(principal.id)
    session.close()
    engine.dispose()


def _authority():
    return diary_calendar_authority(
        datetime(2026, 8, 15, 12, tzinfo=timezone.utc)
    )


def test_empty_complete_replay_and_reopen_are_versioned(day_session) -> None:
    session, principal = day_session
    authority = _authority()
    target = date(2026, 8, 15)

    initial = project_day_status(session, principal, target, authority)
    assert (initial.logging_status, initial.logging_status_version, initial.entry_count) == (
        "unregistered",
        0,
        0,
    )
    completed, replayed = command_day_status(
        session, principal, target, "complete", 0, "empty-complete", authority
    )
    replay, replayed_again = command_day_status(
        session, principal, target, "complete", 0, "empty-complete", authority
    )
    assert completed == replay
    assert not replayed and replayed_again
    assert completed.logging_status == "complete"
    assert completed.analysis_eligible is True
    assert completed.logging_status_version == 1

    reopened, _ = command_day_status(
        session, principal, target, "reopen", 1, "reopen-empty", authority
    )
    assert reopened.logging_status == "partial"
    assert reopened.analysis_eligible is False
    assert reopened.entry_count == 0
    assert reopened.logging_status_version == 2


def test_future_stale_and_key_reuse_fail_closed(day_session) -> None:
    session, principal = day_session
    authority = _authority()
    target = date(2026, 8, 15)
    command_day_status(
        session, principal, target, "complete", 0, "complete-key", authority
    )

    with pytest.raises(HTTPException) as stale:
        command_day_status(
            session, principal, target, "reopen", 0, "stale-reopen", authority
        )
    assert stale.value.status_code == 409
    assert stale.value.detail["code"] == "DAY_VERSION_CONFLICT"

    with pytest.raises(HTTPException) as reused:
        command_day_status(
            session, principal, target, "complete", 1, "complete-key", authority
        )
    assert reused.value.detail["code"] == "IDEMPOTENCY_KEY_REUSED"

    with pytest.raises(HTTPException) as future:
        command_day_status(
            session,
            principal,
            date(2026, 8, 16),
            "complete",
            0,
            "future-key",
            authority,
        )
    assert future.value.status_code == 422
    assert future.value.detail["code"] == "FUTURE_DIARY_DATE"


def test_all_frozen_vectors_execute_against_production_transition_logic() -> None:
    vector_path = (
        Path(__file__).parents[2]
        / "docs/product/nutrition-quality-expansion/26A_W2_DAY_LOGGING_STATUS_GOLDEN_VECTORS.json"
    )
    document = json.loads(vector_path.read_text(encoding="utf-8"))
    assert len(document["vectors"]) == 21
    for vector in document["vectors"]:
        _assert_vector_matches_production_oracle(vector)


def test_vector_acceptance_oracle_rejects_a_mutated_expectation() -> None:
    vector = {
        "initial": {
            "record": False,
            "persisted_status": None,
            "entry_count": 0,
            "version": 0,
        },
        "events": [
            {
                "type": "complete",
                "expected_version": 0,
                "idempotency_key": "negative-mutation",
                "expected": {
                    "result": "completed",
                    "public_status": "partial",
                    "persisted_status": "complete",
                    "entry_count": 0,
                    "version": 1,
                },
            }
        ],
    }
    with pytest.raises(AssertionError):
        _assert_vector_matches_production_oracle(vector)


def _assert_vector_matches_production_oracle(vector: dict) -> None:
    state = deepcopy(vector["initial"])
    replays: dict[tuple[str, str], dict] = {}
    for event in vector["events"]:
        assert evaluate_status_event(state, event, replays) == event["expected"]


def test_target_binding_uses_the_request_captured_date(day_session, monkeypatch) -> None:
    session, principal = day_session
    monkeypatch.setattr(
        "app.services.target_plans.current_diary_date",
        lambda: (_ for _ in ()).throw(AssertionError("must not recapture the clock")),
    )
    binding = resolve_target_binding(
        session,
        principal,
        date(2026, 8, 15),
        authoritative_current_date=date(2026, 8, 15),
    )
    assert binding.provenance.value == "no_target_source"
