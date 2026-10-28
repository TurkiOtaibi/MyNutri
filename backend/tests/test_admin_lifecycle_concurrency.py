"""Disposable PostgreSQL races at the Principal lock boundary."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier, Event
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.labs import get_catalog
from app.models import Principal, PrincipalRole, PrincipalStatus
from app.schemas import DiaryEntryCreate, LabCreateRequest, TargetPlanWriteRequest
from app.services.admin_lifecycle import create_internal_account, delete_account
from app.services.diary import create_entry
from app.services.labs import LabValidationError, create_results
from app.services.target_plans import TargetPlanError, write_target_plan


def _actors(engine) -> tuple[UUID, UUID]:
    admin_id, user_id = uuid4(), uuid4()
    with Session(engine) as session:
        session.add(Principal(id=admin_id, role=PrincipalRole.admin))
        session.add(Principal(id=user_id, auth_user_id=uuid4(), email="writer@example.test"))
        session.commit()
    return admin_id, user_id


@pytest.mark.migration
@pytest.mark.parametrize("writer", ["target", "diary", "labs"])
def test_deletion_racing_private_writer_cannot_leave_a_row(labs_postgresql_database, monkeypatch, writer: str) -> None:
    engine = labs_postgresql_database.engine
    admin_id, user_id = _actors(engine)
    from app.services import admin_lifecycle

    purge_entered, writer_entered = Event(), Event()
    original_purge = admin_lifecycle._purge_private_rows

    def paused_purge(session, principal_id):
        purge_entered.set()
        assert writer_entered.wait(timeout=15)
        original_purge(session, principal_id)

    monkeypatch.setattr(admin_lifecycle, "_purge_private_rows", paused_purge)
    now = datetime.now(timezone.utc)

    def delete() -> None:
        with Session(engine) as session:
            delete_account(session, admin_id, user_id, now)

    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(delete)
        assert purge_entered.wait(timeout=15)
        # Signal the competing writer when it reaches its Principal lock.
        with Session(engine) as session:
            def before_execute(connection, cursor, statement, parameters, context, many):
                if "FOR UPDATE" in statement:
                    writer_entered.set()

            event.listen(session.connection(), "before_cursor_execute", before_execute)
            actor = PrincipalContext(principal_id=user_id)
            if writer == "target":
                payload = TargetPlanWriteRequest.model_validate({
                    "sex": "male", "birth_date": "1990-01-01", "height_cm": 175,
                    "weight_kg": 80, "activity_level": "moderate", "goal": "maintain",
                    "effective_from": date.today().isoformat(), "confirmed": True,
                    "expected_preview_hash": "0" * 64,
                })
                with pytest.raises(TargetPlanError) as blocked:
                    write_target_plan(session, actor, payload, "race-target")
                assert blocked.value.status_code == 401
            elif writer == "diary":
                payload = DiaryEntryCreate(entry_date=date.today(), food_id=uuid4(), quantity=1)
                with pytest.raises(Exception) as blocked:
                    create_entry(session, actor, payload)
                assert getattr(blocked.value, "status_code", None) == 401
            else:
                payload = LabCreateRequest.model_validate({
                    "test_date": date.today().isoformat(),
                    "results": [{"test_key": "hba1c", "entered_value": "5.2", "entered_unit": "%"}],
                })
                with pytest.raises(LabValidationError) as blocked:
                    create_results(session, actor, payload, "race-labs", get_catalog())
                assert blocked.value.status_code == 401
        future.result(timeout=15)
    with engine.connect() as connection:
        for table in ("profile", "target_plan", "diary_entry", "lab_result", "idempotency_record"):
            assert connection.scalar(text(f"SELECT count(*) FROM {table} WHERE principal_id=:id"), {"id": user_id}) == 0


@pytest.mark.migration
def test_two_concurrent_deletes_leave_one_scrubbed_tombstone(labs_postgresql_database) -> None:
    engine = labs_postgresql_database.engine
    admin_id, user_id = _actors(engine)
    start = Barrier(3)
    now = datetime.now(timezone.utc)

    def delete() -> PrincipalStatus:
        start.wait(timeout=15)
        with Session(engine) as session:
            return delete_account(session, admin_id, user_id, now).status

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(delete) for _ in range(2)]
        start.wait(timeout=15)
        assert [future.result(timeout=30) for future in futures] == [PrincipalStatus.deleted] * 2
    with Session(engine) as session:
        row = session.get(Principal, user_id)
        assert row.status == PrincipalStatus.deleted
        assert row.auth_user_id is None and row.retired_auth_user_id is not None


@pytest.mark.migration
def test_concurrent_same_key_creates_one_internal_account(labs_postgresql_database) -> None:
    engine = labs_postgresql_database.engine
    admin_id, _ = _actors(engine)
    start = Barrier(3)
    now = datetime.now(timezone.utc)

    def create() -> UUID:
        start.wait(timeout=15)
        with Session(engine) as session:
            return create_internal_account(
                session, admin_id, "same-user", "Same", "password", "same-key",
                now,
            ).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        start.wait(timeout=15)
        ids = [future.result(timeout=30) for future in futures]
    assert ids[0] == ids[1]
    with Session(engine) as session:
        assert len(session.exec(select(Principal).where(Principal.normalized_username == "same-user")).all()) == 1
