from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import (
    ActivityLevel, DefaultUnitType, DiaryEntry, Food, Goal, IdempotencyRecord,
    IdempotencyState, LabResult, NutritionBasis, NutritionDataSource, Principal, PrincipalRole,
    PrincipalStatus, Profile, Sex, TargetPlan, UnitBasis,
)
from app.services.admin_auth import AdminAuthError, AdminIdentity
from app.services.admin_lifecycle import (
    LifecycleError,
    create_account,
    delete_account,
    reconcile_retired_identity,
    reconcile_recent_tombstones,
    reconcile_all_retired,
    reset_account_password,
    set_account_enabled,
)
from app.services.food import to_food_response
from app.api.routes.foods import read_food
from app.api.routes.admin import list_users
from app.core.auth import PrincipalContext
from app.schemas import AdminAccountCreate, AdminAccountEdit
from pydantic import ValidationError


class FakeAuth:
    def __init__(self) -> None:
        self.users: dict[UUID, str] = {}
        self.passwords: dict[UUID, str] = {}
        self.create_ids: list[UUID] = []
        self.fail_create = False
        self.fail_delete = False

    def create_user(self, auth_id: UUID, email: str, password: str) -> AdminIdentity:
        self.create_ids.append(auth_id)
        if self.fail_create:
            raise AdminAuthError("unavailable")
        if any(existing_id != auth_id and existing_email == email for existing_id, existing_email in self.users.items()):
            raise AdminAuthError("duplicate_email")
        self.users[auth_id] = email
        self.passwords[auth_id] = password
        return AdminIdentity(auth_id, email)

    def get_user_by_id(self, auth_id: UUID) -> AdminIdentity | None:
        email = self.users.get(auth_id)
        return AdminIdentity(auth_id, email) if email is not None else None

    def find_user_by_email(self, email: str) -> AdminIdentity | None:
        for auth_id, existing_email in self.users.items():
            if existing_email == email:
                return AdminIdentity(auth_id, email)
        return None

    def reset_password(self, auth_id: UUID, password: str) -> None:
        if auth_id not in self.users:
            raise AdminAuthError("unavailable")
        self.passwords[auth_id] = password

    def delete_user(self, auth_id: UUID) -> None:
        if self.fail_delete:
            raise AdminAuthError("unavailable")
        self.users.pop(auth_id, None)


@pytest.fixture
def lifecycle_session():
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", lambda dbapi, _: dbapi.execute("PRAGMA foreign_keys=ON"))
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin = Principal(auth_user_id=uuid4(), email="admin@example.com", role=PrincipalRole.admin)
        session.add(admin)
        session.commit()
        yield session, admin.id


def test_create_preassigns_identity_and_same_key_retry_resumes(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    fake.fail_create = True
    with pytest.raises(AdminAuthError):
        create_account(session, admin_id, "new@example.com", "New User", "secret", "key-1", fake, now, 10)
    pending = session.exec(select(Principal).where(Principal.email == "new@example.com")).one()
    assert pending.status == PrincipalStatus.provisioning
    assert pending.auth_user_id is not None
    assert pending.identity_requested_at.replace(tzinfo=timezone.utc) == now
    fake.fail_create = False
    active = create_account(session, admin_id, "new@example.com", "New User", "secret", "key-1", fake, now + timedelta(seconds=1), 10)
    assert active.id == pending.id
    assert active.status == PrincipalStatus.active
    assert fake.create_ids == [pending.auth_user_id, pending.auth_user_id]


def test_retry_with_existing_identity_sets_submitted_password(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    fake.fail_create = True
    with pytest.raises(AdminAuthError):
        create_account(session, admin_id, "late-password@example.com", "User", "first-password", "key-password", fake, now, 10)
    pending = session.exec(select(Principal).where(Principal.email == "late-password@example.com")).one()
    assert pending.auth_user_id is not None
    fake.users[pending.auth_user_id] = pending.email
    fake.passwords[pending.auth_user_id] = "first-password"
    active = create_account(session, admin_id, pending.email, "User", "new-password", "key-password", fake, now + timedelta(seconds=1), 10)
    assert active.status == PrincipalStatus.active
    assert fake.passwords[pending.auth_user_id] == "new-password"


def test_late_create_is_refused_during_lease_then_reconciled(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    fake.fail_create = True
    with pytest.raises(AdminAuthError):
        create_account(session, admin_id, "late@example.com", "Late", "secret", "key-late", fake, now, 10)
    pending = session.exec(select(Principal).where(Principal.email == "late@example.com")).one()
    retired_id = pending.auth_user_id
    assert retired_id is not None
    with pytest.raises(LifecycleError) as leased:
        delete_account(session, admin_id, pending.id, fake, now + timedelta(minutes=1), 10)
    assert leased.value.status_code == 409
    deleted = delete_account(session, admin_id, pending.id, fake, now + timedelta(minutes=5, seconds=1), 10)
    assert deleted.status == PrincipalStatus.deleted
    assert deleted.auth_user_id is None
    assert deleted.retired_auth_user_id == retired_id
    fake.users[retired_id] = "late@example.com"
    assert reconcile_retired_identity(session, retired_id, fake) is True
    assert retired_id not in fake.users


def test_recent_reconciliation_rotates_bounded_tombstone_batches(lifecycle_session) -> None:
    session, _ = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    retired_ids = []
    for index in range(101):
        auth_id = uuid4()
        retired_ids.append(auth_id)
        session.add(Principal(
            auth_user_id=None, retired_auth_user_id=auth_id, email=None, display_name=None,
            status=PrincipalStatus.deleted, deleted_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        ))
        fake.users[auth_id] = f"late-{index}@example.com"
    session.commit()
    first = reconcile_recent_tombstones(session, fake, now, limit=100)
    second = reconcile_recent_tombstones(session, fake, now + timedelta(seconds=1), limit=100)
    assert first["checked"] == 100
    assert second["checked"] == 100
    assert all(auth_id not in fake.users for auth_id in retired_ids)


def test_monitoring_list_excludes_deleting_and_deleted_accounts(lifecycle_session) -> None:
    session, _ = lifecycle_session
    session.add(Principal(auth_user_id=uuid4(), email="active@example.com", status=PrincipalStatus.active))
    session.add(Principal(auth_user_id=uuid4(), email="deleting@example.com", status=PrincipalStatus.deleting))
    session.add(Principal(auth_user_id=None, retired_auth_user_id=uuid4(), email=None, display_name=None, status=PrincipalStatus.deleted))
    session.commit()
    page = list_users(page=1, page_size=20, _admin=None, session=session)
    assert {item.email for item in page.items} == {"admin@example.com", "active@example.com"}


def test_account_display_name_rejects_whitespace_only() -> None:
    with pytest.raises(ValidationError):
        AdminAccountCreate(email="user@example.com", display_name=" \t ", initial_password="secret")
    with pytest.raises(ValidationError):
        AdminAccountEdit(display_name=" \t ")


def test_password_reset_and_disable_set_fail_closed_session_cutoff(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, 12, 0, 0, 100_000, timezone.utc)
    user = create_account(session, admin_id, "cutoff@example.com", "Cutoff", "initial", "key-cutoff", fake, now, 10)
    reset_account_password(session, admin_id, user.id, "new-password", fake, now)
    session.refresh(user)
    assert user.sessions_valid_after.replace(tzinfo=timezone.utc) == datetime(2026, 9, 28, 12, 0, 1, tzinfo=timezone.utc)
    set_account_enabled(session, admin_id, user.id, False, now + timedelta(seconds=3))
    session.refresh(user)
    assert user.status == PrincipalStatus.disabled
    assert user.sessions_valid_after.replace(tzinfo=timezone.utc) == datetime(2026, 9, 28, 12, 0, 4, tzinfo=timezone.utc)


def test_account_mutations_reject_admin_target(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    with pytest.raises(LifecycleError) as caught:
        delete_account(session, admin_id, admin_id, fake, now, 10)
    assert caught.value.status_code == 403


def test_recent_and_full_reconciliation_remove_late_identity_idempotently(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    user = create_account(session, admin_id, "late2@example.com", "Late", "password", "key-late2", fake, now, 10)
    retired_id = user.auth_user_id
    assert retired_id is not None
    delete_account(session, admin_id, user.id, fake, now + timedelta(minutes=6), 10)
    fake.users[retired_id] = "late2@example.com"
    assert reconcile_recent_tombstones(session, fake, now + timedelta(minutes=7), limit=10) == {"checked": 1, "failed": 0}
    assert retired_id not in fake.users
    fake.users[retired_id] = "late2@example.com"
    assert reconcile_all_retired(session, fake, batch_size=10) == {"checked": 1, "failed": 0}
    assert retired_id not in fake.users
    assert reconcile_all_retired(session, fake, batch_size=10) == {"checked": 1, "failed": 0}


def test_principal_foreign_key_catalog_has_explicit_purge_or_food_attribution_decision() -> None:
    decisions = {
        ("profile", "principal_id"),
        ("target_plan", "principal_id"),
        ("diary_entry", "principal_id"),
        ("lab_result", "principal_id"),
        ("idempotency_record", "principal_id"),
        ("food", "created_by_principal_id"),
        ("food", "updated_by_principal_id"),
    }
    actual = {
        (table.name, column.name)
        for table in SQLModel.metadata.tables.values()
        for column in table.columns
        for foreign_key in column.foreign_keys
        if foreign_key.target_fullname == "principal.id"
    }
    assert actual == decisions


def test_deletion_purges_every_private_dependent_and_preserves_global_food(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    user = create_account(session, admin_id, "purge@example.com", "Purge", "password", "key-purge", fake, now, 10)
    profile = Profile(
        principal_id=user.id, sex=Sex.male, birth_date=date(1990, 1, 1),
        height_cm=175, weight_kg=80, activity_level=ActivityLevel.moderate,
        goal=Goal.maintain, protein_per_kg=1.2, fat_pct=0.25,
    )
    food = Food(
        principal_id=user.id, name="Global Food", normalized_name="global food",
        nutrition_basis=NutritionBasis.per_100g, default_unit_type=DefaultUnitType.g,
        unit_amount=1, unit_basis=UnitBasis.g, calories=100, protein_g=1,
        carb_g=2, fat_g=3, nutrition_data_source=NutritionDataSource.estimated,
    )
    session.add_all([profile, food])
    session.commit()
    plan = TargetPlan(
        principal_id=user.id, profile_id=profile.id, effective_from=date(2026, 9, 28),
        revision=1, calculation_document={"target_result": {}},
    )
    session.add(plan)
    session.commit()
    entry = DiaryEntry(
        principal_id=user.id, entry_date=date(2026, 9, 28), food_id=food.id,
        target_plan_id=plan.id, quantity=1, recorded_unit_type=DefaultUnitType.g,
        recorded_unit_amount=1, recorded_unit_basis=UnitBasis.g,
    )
    lab = LabResult(
        principal_id=user.id, test_key="hba1c", test_date=date(2026, 9, 28),
        entered_value=Decimal("5.2"), entered_unit="%",
    )
    receipt = IdempotencyRecord(
        principal_id=user.id, operation="lab_results.create.v1", idempotency_key="purge-receipt",
        request_hash="x" * 64, state=IdempotencyState.completed,
        response_status=201, response_document={"id": str(lab.id)}, completed_at=now,
    )
    session.add_all([entry, lab, receipt])
    session.commit()
    deleted = delete_account(session, admin_id, user.id, fake, now + timedelta(minutes=6), 10)
    assert deleted.status == PrincipalStatus.deleted
    assert deleted.email is None and deleted.display_name is None
    for model in (Profile, TargetPlan, DiaryEntry, LabResult, IdempotencyRecord):
        assert session.exec(select(model).where(model.principal_id == user.id)).all() == []
    session.refresh(food)
    assert food.created_by_principal_id == user.id
    assert to_food_response(food, {user.id}).created_by_label == "مستخدم محذوف"
    assert read_food(food.id, PrincipalContext(principal_id=admin_id), session).created_by_label == "مستخدم محذوف"


def test_creation_retry_refused_after_deletion_begins(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    fake.fail_create = True
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    with pytest.raises(AdminAuthError):
        create_account(session, admin_id, "stopped@example.com", "Stopped", "pw", "key-stopped", fake, now, 10)
    pending = session.exec(select(Principal).where(Principal.email == "stopped@example.com")).one()
    delete_account(session, admin_id, pending.id, fake, now + timedelta(minutes=6), 10)
    fake.fail_create = False
    with pytest.raises(LifecycleError) as caught:
        create_account(session, admin_id, "stopped@example.com", "Stopped", "pw", "key-stopped", fake, now + timedelta(minutes=7), 10)
    assert caught.value.status_code == 409
    assert len(fake.create_ids) == 1


def test_new_account_cleans_retired_late_email_but_rejects_nonretired_duplicate(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    old = create_account(session, admin_id, "reuse@example.com", "Old", "pw", "key-old", fake, now, 10)
    retired_id = old.auth_user_id
    assert retired_id is not None
    delete_account(session, admin_id, old.id, fake, now + timedelta(minutes=6), 10)
    fake.users[retired_id] = "reuse@example.com"
    replacement = create_account(session, admin_id, "reuse@example.com", "New", "pw", "key-new", fake, now + timedelta(minutes=7), 10)
    assert replacement.auth_user_id != retired_id
    assert retired_id not in fake.users
    fake.users[uuid4()] = "taken@example.com"
    with pytest.raises(LifecycleError) as caught:
        create_account(session, admin_id, "taken@example.com", "Taken", "pw", "key-taken", fake, now + timedelta(minutes=8), 10)
    assert caught.value.code == "DUPLICATE_EMAIL"


def test_failed_identity_delete_leaves_locked_out_deleting_for_retry(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    fake = FakeAuth()
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    user = create_account(session, admin_id, "retry@example.com", "Retry", "pw", "key-retry", fake, now, 10)
    fake.fail_delete = True
    with pytest.raises(AdminAuthError):
        delete_account(session, admin_id, user.id, fake, now + timedelta(minutes=6), 10)
    session.refresh(user)
    assert user.status == PrincipalStatus.deleting
    fake.fail_delete = False
    deleted = delete_account(session, admin_id, user.id, fake, now + timedelta(minutes=7), 10)
    assert deleted.status == PrincipalStatus.deleted
