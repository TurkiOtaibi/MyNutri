from datetime import date, datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import diary_calendar_authority
from app.models import (
    DiaryDayStatus,
    DiaryDayStatusEvent,
    DiaryDayStatusValue,
    DiaryEntry,
    Principal,
    utcnow,
)
from app.services.day_logging_status import (
    command_day_status,
    lock_day_for_entry,
    lock_owner,
    project_day_status,
    record_entry_mutation,
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
        _assert_vector_matches_persisted_services(vector)


def test_vector_acceptance_oracle_rejects_a_mutated_expectation() -> None:
    vector_path = (
        Path(__file__).parents[2]
        / "docs/product/nutrition-quality-expansion/26A_W2_DAY_LOGGING_STATUS_GOLDEN_VECTORS.json"
    )
    vector = json.loads(vector_path.read_text(encoding="utf-8"))["vectors"][0]
    vector["events"][0]["expected"]["public_status"] = "complete"
    with pytest.raises(AssertionError):
        _assert_vector_matches_persisted_services(vector)


def _assert_vector_matches_persisted_services(vector: dict) -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        principal_row = Principal()
        session.add(principal_row)
        session.commit()
        principal = PrincipalContext(principal_row.id)
        relation = next(
            (event.get("date_relation") for event in vector["events"] if event.get("date_relation")),
            "current",
        )
        diary_date = date(2026, 8, 16) if relation == "future" else date(2026, 8, 14) if relation == "past" else date(2026, 8, 15)
        initial = vector["initial"]
        for _ in range(initial["entry_count"]):
            session.add(
                DiaryEntry(
                    principal_id=principal.principal_id,
                    entry_date=diary_date,
                    quantity=1,
                    snapshot_schema_version=2,
                    nutrition_snapshot={"schema_version": 2},
                )
            )
        if initial["record"]:
            status = DiaryDayStatusValue(initial["persisted_status"])
            session.add(
                DiaryDayStatus(
                    principal_id=principal.principal_id,
                    diary_date=diary_date,
                    status=status,
                    version=initial["version"],
                    entry_count=initial["entry_count"],
                    completed_at=utcnow() if status == DiaryDayStatusValue.complete else None,
                )
            )
        session.commit()
        for event in vector["events"]:
            assert _apply_persisted_event(session, principal, diary_date, event) == event["expected"]
    engine.dispose()


def _apply_persisted_event(
    session: Session,
    principal: PrincipalContext,
    diary_date: date,
    event: dict,
) -> dict:
    authority = _authority()
    kind = event["type"]
    before = project_day_status(session, principal, diary_date, authority)
    result = "projected"
    try:
        if kind in {"complete", "reopen"}:
            response, replayed = command_day_status(
                session,
                principal,
                diary_date,
                kind,
                event["expected_version"],
                event["idempotency_key"],
                authority,
            )
            result = "replayed" if replayed else "no_change" if response.logging_status == before.logging_status else "completed" if kind == "complete" else "reopened"
        elif kind != "read":
            lock_owner(session, principal)
            row = lock_day_for_entry(
                session, principal, diary_date, event["expected_version"], authority
            )
            entries = session.exec(
                select(DiaryEntry).where(
                    DiaryEntry.principal_id == principal.principal_id,
                    DiaryEntry.entry_date == diary_date,
                )
            ).all()
            if kind == "create_entry":
                entry = DiaryEntry(
                    id=uuid4(),
                    principal_id=principal.principal_id,
                    entry_date=diary_date,
                    quantity=1,
                    snapshot_schema_version=2,
                    nutrition_snapshot={"schema_version": 2},
                )
                session.add(entry)
                session.flush()
                count = len(entries) + 1
                event_type = DiaryDayStatusEvent.entry_created
                result = "created"
            else:
                if not entries:
                    raise HTTPException(status_code=404, detail={"code": "RESOURCE_NOT_FOUND"})
                entry = entries[0]
                count = len(entries)
                if kind == "delete_entry":
                    session.delete(entry)
                    count -= 1
                    event_type = DiaryDayStatusEvent.entry_deleted
                    result = "deleted"
                else:
                    entry.quantity += 1
                    session.add(entry)
                    event_type = DiaryDayStatusEvent.entry_edited
                    result = "edited"
            record_entry_mutation(
                session,
                principal,
                diary_date,
                row,
                event_type,
                entry.id,
                count,
            )
            session.commit()
    except HTTPException as error:
        session.rollback()
        result = {
            "FUTURE_DIARY_DATE": "future_rejected",
            "DAY_VERSION_CONFLICT": "stale_version_conflict",
            "DAY_ALREADY_COMPLETE": "day_complete_conflict",
            "IDEMPOTENCY_KEY_REUSED": "idempotency_key_conflict",
            "RESOURCE_NOT_FOUND": "entry_not_found",
        }[error.detail["code"]]
    projected = project_day_status(session, principal, diary_date, authority)
    row = session.exec(
        select(DiaryDayStatus).where(
            DiaryDayStatus.principal_id == principal.principal_id,
            DiaryDayStatus.diary_date == diary_date,
        )
    ).first()
    persisted = row.status.value if row and isinstance(row.status, DiaryDayStatusValue) else row.status if row else None
    return {
        "result": result,
        "public_status": projected.logging_status.value,
        "persisted_status": persisted,
        "entry_count": projected.entry_count,
        "version": projected.logging_status_version,
    }


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
