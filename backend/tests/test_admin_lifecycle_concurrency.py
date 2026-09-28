"""Disposable PostgreSQL races at the Principal lock boundary."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from threading import Barrier, Event, Lock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.labs import get_catalog
from app.models import Principal, PrincipalRole, PrincipalStatus
from app.schemas import DiaryEntryCreate, LabCreateRequest, TargetPlanWriteRequest
from app.services.admin_auth import AdminAuthError, AdminIdentity
from app.services.admin_lifecycle import create_account, delete_account
from app.services.diary import create_entry
from app.services.labs import LabValidationError, create_results
from app.services.target_plans import TargetPlanError, write_target_plan


class ConcurrentAuth:
    def __init__(self) -> None:
        self.users: dict[UUID, str] = {}
        self.mutex = Lock()
        self.delete_entered: Event | None = None
        self.finish_delete: Event | None = None

    def create_user(self, auth_id: UUID, email: str, password: str) -> AdminIdentity:
        with self.mutex:
            if email in self.users.values() and auth_id not in self.users:
                raise AdminAuthError("duplicate_email")
            self.users[auth_id] = email
        return AdminIdentity(auth_id, email)

    def get_user_by_id(self, auth_id: UUID) -> AdminIdentity | None:
        with self.mutex:
            email = self.users.get(auth_id)
        return AdminIdentity(auth_id, email) if email else None

    def find_user_by_email(self, email: str) -> AdminIdentity | None:
        with self.mutex:
            return next((AdminIdentity(id_, value) for id_, value in self.users.items() if value == email), None)

    def reset_password(self, auth_id: UUID, password: str) -> None:
        pass

    def delete_user(self, auth_id: UUID) -> None:
        if self.delete_entered:
            self.delete_entered.set()
        if self.finish_delete:
            assert self.finish_delete.wait(timeout=15)
        with self.mutex:
            self.users.pop(auth_id, None)


def _actors(engine) -> tuple[UUID, UUID, ConcurrentAuth]:
    admin_id, user_id, auth_id = uuid4(), uuid4(), uuid4()
    gateway = ConcurrentAuth()
    gateway.users[auth_id] = "writer@example.test"
    with Session(engine) as session:
        session.add(Principal(id=admin_id, auth_user_id=uuid4(), email="admin@example.test", role=PrincipalRole.admin))
        session.add(Principal(id=user_id, auth_user_id=auth_id, email="writer@example.test"))
        session.commit()
    return admin_id, user_id, gateway


@pytest.mark.migration
@pytest.mark.parametrize("writer", ["target", "diary", "labs"])
def test_deletion_racing_private_writer_cannot_leave_a_row(labs_postgresql_database, writer: str) -> None:
    engine = labs_postgresql_database.engine
    admin_id, user_id, gateway = _actors(engine)
    gateway.delete_entered = Event()
    gateway.finish_delete = Event()
    now = datetime.now(timezone.utc)

    def delete() -> None:
        with Session(engine) as session:
            delete_account(session, admin_id, user_id, gateway, now, 10)

    with ThreadPoolExecutor(max_workers=2) as pool:
        future = pool.submit(delete)
        assert gateway.delete_entered.wait(timeout=15)
        # The saga has committed deleting and purged before the provider call.
        with Session(engine) as session:
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
        gateway.finish_delete.set()
        future.result(timeout=15)
    with engine.connect() as connection:
        for table in ("profile", "target_plan", "diary_entry", "lab_result", "idempotency_record"):
            assert connection.scalar(text(f"SELECT count(*) FROM {table} WHERE principal_id=:id"), {"id": user_id}) == 0


@pytest.mark.migration
def test_two_concurrent_deletes_leave_one_scrubbed_tombstone(labs_postgresql_database) -> None:
    engine = labs_postgresql_database.engine
    admin_id, user_id, gateway = _actors(engine)
    start = Barrier(3)
    now = datetime.now(timezone.utc)

    def delete() -> PrincipalStatus:
        start.wait(timeout=15)
        with Session(engine) as session:
            return delete_account(session, admin_id, user_id, gateway, now, 10).status

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(delete) for _ in range(2)]
        start.wait(timeout=15)
        assert [future.result(timeout=30) for future in futures] == [PrincipalStatus.deleted] * 2
    with Session(engine) as session:
        row = session.get(Principal, user_id)
        assert row.status == PrincipalStatus.deleted
        assert row.auth_user_id is None and row.retired_auth_user_id is not None


@pytest.mark.migration
def test_delete_resuming_after_other_delete_preserves_retired_identity(labs_postgresql_database) -> None:
    engine = labs_postgresql_database.engine
    admin_id, user_id, gateway = _actors(engine)
    gateway.delete_entered = Event()
    gateway.finish_delete = Event()
    second_purged = Event()
    first_finished = Event()
    now = datetime.now(timezone.utc)

    class PausingSession(Session):
        def commit(self) -> None:
            super().commit()
            second_purged.set()
            assert first_finished.wait(timeout=15)

    def first_delete() -> None:
        with Session(engine) as session:
            delete_account(session, admin_id, user_id, gateway, now, 10)
        first_finished.set()

    def second_delete() -> None:
        with PausingSession(engine) as session:
            delete_account(session, admin_id, user_id, gateway, now, 10)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(first_delete)
        assert gateway.delete_entered.wait(timeout=15)
        second = pool.submit(second_delete)
        assert second_purged.wait(timeout=15)
        gateway.finish_delete.set()
        first.result(timeout=15)
        second.result(timeout=15)

    with Session(engine) as session:
        row = session.get(Principal, user_id)
        assert row.status == PrincipalStatus.deleted
        assert row.auth_user_id is None
        assert row.retired_auth_user_id is not None


@pytest.mark.migration
def test_concurrent_same_key_creates_one_account_and_identity(labs_postgresql_database) -> None:
    engine = labs_postgresql_database.engine
    admin_id, _, gateway = _actors(engine)
    start = Barrier(3)
    now = datetime.now(timezone.utc)

    def create() -> UUID:
        start.wait(timeout=15)
        with Session(engine) as session:
            return create_account(
                session, admin_id, "same@example.test", "Same", "password", "same-key",
                gateway, now, 10,
            ).id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        start.wait(timeout=15)
        ids = [future.result(timeout=30) for future in futures]
    assert ids[0] == ids[1]
    with Session(engine) as session:
        assert len(session.exec(select(Principal).where(Principal.email == "same@example.test")).all()) == 1
    assert list(gateway.users.values()).count("same@example.test") == 1
