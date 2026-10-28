from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import (
    ActivityLevel, AuthSession, DefaultUnitType, DiaryEntry, Food, Goal, IdempotencyRecord,
    IdempotencyState, LabResult, NutritionBasis, NutritionDataSource, Principal, PrincipalRole,
    PrincipalStatus, Profile, Sex, TargetPlan, UnitBasis,
)
from app.services.admin_lifecycle import (
    LifecycleError,
    create_internal_account,
    delete_account,
    reset_account_password,
    set_account_enabled,
)
from app.services.food import to_food_response
from app.api.routes.foods import read_food
from app.api.routes.admin import list_users
from app.core.auth import PrincipalContext
from app.schemas import AdminInternalAccountCreate, AdminAccountEdit
from pydantic import ValidationError


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
        AdminInternalAccountCreate(username="user", display_name=" \t ", initial_password="secret")
    with pytest.raises(ValidationError):
        AdminAccountEdit(display_name=" \t ")


def test_reset_disable_and_enable_revoke_all_existing_sessions(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    now = datetime(2026, 9, 28, 12, 0, 0, 100_000, timezone.utc)
    user = create_internal_account(session, admin_id, "cutoff", "Cutoff", "initial-password", "key-cutoff", now)
    for index, operation in enumerate(("reset", "disable", "enable")):
        tokens = [AuthSession(
            principal_id=user.id, token_hash=f"{index * 2 + offset:064x}",
            created_at=now, last_used_at=now, expires_at=now + timedelta(days=1),
        ) for offset in range(2)]
        session.add_all(tokens)
        session.commit()
        mutation_time = now + timedelta(seconds=index)
        if operation == "reset":
            reset_account_password(session, admin_id, user.id, "new-password", mutation_time)
        else:
            set_account_enabled(session, admin_id, user.id, operation == "enable", mutation_time)
        for token in tokens:
            session.refresh(token)
            assert token.revoked_at.replace(tzinfo=timezone.utc) == mutation_time
        session.refresh(user)
        assert user.status == (PrincipalStatus.disabled if operation == "disable" else PrincipalStatus.active)


def test_account_mutations_reject_admin_target(lifecycle_session) -> None:
    session, admin_id = lifecycle_session
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    with pytest.raises(LifecycleError) as caught:
        delete_account(session, admin_id, admin_id, now)
    assert caught.value.status_code == 403


def test_principal_foreign_key_catalog_has_explicit_purge_or_food_attribution_decision() -> None:
    decisions = {
        ("auth_session", "principal_id"),
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


@pytest.mark.parametrize("legacy", [False, True])
def test_deletion_purges_every_private_dependent_and_preserves_global_food(lifecycle_session, legacy) -> None:
    session, admin_id = lifecycle_session
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    user = create_internal_account(session, admin_id, "purge", "Purge", "password", "key-purge", now)
    if legacy:
        user.auth_user_id = uuid4()
        user.email = "purge@example.test"
        user.username = user.normalized_username = user.password_hash = None
        session.add(user)
        session.commit()
    auth_session = AuthSession(principal_id=user.id, token_hash="a" * 64, created_at=now, last_used_at=now, expires_at=now + timedelta(days=1))
    session.add(auth_session)
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
    deleted = delete_account(session, admin_id, user.id, now + timedelta(minutes=6))
    assert deleted.status == PrincipalStatus.deleted
    assert deleted.email is None and deleted.display_name is None
    for model in (AuthSession, Profile, TargetPlan, DiaryEntry, LabResult, IdempotencyRecord):
        assert session.exec(select(model).where(model.principal_id == user.id)).all() == []
    session.refresh(food)
    assert food.created_by_principal_id == user.id
    assert to_food_response(food, {user.id}).created_by_label == "مستخدم محذوف"
    assert read_food(food.id, PrincipalContext(principal_id=admin_id), session).created_by_label == "مستخدم محذوف"


@pytest.mark.parametrize("status", [PrincipalStatus.active, PrincipalStatus.disabled, PrincipalStatus.provisioning, PrincipalStatus.deleting])
def test_legacy_deletion_is_local_and_idempotent(lifecycle_session, status):
    session, admin_id = lifecycle_session
    now = datetime.now(timezone.utc)
    auth_id = uuid4()
    row = Principal(auth_user_id=auth_id, email="legacy@example.test", display_name="Legacy", status=status, identity_requested_at=now)
    session.add(row)
    session.commit()
    deleted = delete_account(session, admin_id, row.id, now, confirmation_email="legacy@example.test", require_confirmation=True)
    assert deleted.status == PrincipalStatus.deleted
    assert deleted.auth_user_id is None and deleted.retired_auth_user_id == auth_id
    assert deleted.email is None and deleted.display_name is None
    repeated = delete_account(session, admin_id, row.id, now, confirmation_email="legacy@example.test", require_confirmation=True)
    assert repeated.id == row.id and repeated.retired_auth_user_id == auth_id


@pytest.mark.parametrize("status", [PrincipalStatus.active, PrincipalStatus.disabled])
def test_legacy_reset_refuses_without_attaching_credentials(lifecycle_session, status):
    session, admin_id = lifecycle_session
    row = Principal(auth_user_id=uuid4(), email="legacy@example.test", status=status)
    session.add(row)
    session.commit()
    with pytest.raises(LifecycleError) as error:
        reset_account_password(session, admin_id, row.id, "New-password", datetime.now(timezone.utc))
    assert error.value.code == "CREATION_INCOMPLETE"
    assert error.value.status_code == 409
    session.rollback()
    session.refresh(row)
    assert row.password_hash is None and row.username is None


@pytest.mark.parametrize("status", [PrincipalStatus.active, PrincipalStatus.provisioning, PrincipalStatus.deleting])
def test_legacy_delete_checks_confirmation_before_purge(lifecycle_session, status):
    session, admin_id = lifecycle_session
    row = Principal(auth_user_id=uuid4(), email="legacy@example.test", status=status)
    session.add(row)
    session.commit()
    with pytest.raises(LifecycleError) as error:
        delete_account(session, admin_id, row.id, datetime.now(timezone.utc), confirmation_email="wrong@example.test", require_confirmation=True)
    assert error.value.code == "DELETE_EMAIL_MISMATCH"
    assert row.status == status and row.email == "legacy@example.test"


@pytest.mark.parametrize("legacy", [False, True])
def test_purge_failure_rolls_back_private_data_and_tombstone(lifecycle_session, monkeypatch, legacy):
    from app.services import admin_lifecycle

    session, admin_id = lifecycle_session
    now = datetime.now(timezone.utc)
    user = create_internal_account(session, admin_id, "rollback", "Rollback", "initial-password", "rollback-key", now)
    if legacy:
        user.auth_user_id = uuid4()
        user.email = "rollback@example.test"
        user.username = user.normalized_username = user.password_hash = None
        session.add(user)
    token = AuthSession(principal_id=user.id, token_hash="b" * 64, created_at=now, last_used_at=now, expires_at=now + timedelta(days=1))
    session.add(token)
    session.commit()
    original_purge = admin_lifecycle._purge_private_rows

    def fail_after_purge(session, principal_id):
        original_purge(session, principal_id)
        raise RuntimeError("synthetic purge failure")

    monkeypatch.setattr(admin_lifecycle, "_purge_private_rows", fail_after_purge)
    with pytest.raises(LifecycleError, match="DELETION_INCOMPLETE"):
        delete_account(session, admin_id, user.id, now)
    session.rollback()
    session.refresh(user)
    assert user.status == PrincipalStatus.deleting and user.display_name == "Rollback"
    assert session.get(AuthSession, token.id).revoked_at is not None


def test_deleted_creation_key_cannot_restore_private_identity(lifecycle_session):
    session, admin_id = lifecycle_session
    now = datetime.now(timezone.utc)
    row = create_internal_account(session, admin_id, "retired", "Retired", "initial-password", "retired-key", now)
    delete_account(session, admin_id, row.id, now)
    with pytest.raises(LifecycleError) as error:
        create_internal_account(session, admin_id, "retired", "Retired", "initial-password", "retired-key", now)
    assert error.value.code == "CREATION_INCOMPLETE"
    assert row.status == PrincipalStatus.deleted and row.username is None
