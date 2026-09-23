from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect, null, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app import models
from app.models import IdempotencyRecord, IdempotencyState, Principal


def result(owner_id, **overrides):
    return models.LabResult(
        **{
            "principal_id": owner_id,
            "test_key": "hba1c",
            "test_date": date(2026, 9, 19),
            "entered_value": Decimal("5.270"),
            "entered_unit": "%",
            **overrides,
        }
    )


def test_numeric_preserves_entered_precision(labs_postgresql_session, lab_owner):
    assert "lab_result" in inspect(labs_postgresql_session.get_bind()).get_table_names()
    row = result(lab_owner.id)
    labs_postgresql_session.add(row)
    labs_postgresql_session.commit()
    row_id = row.id
    labs_postgresql_session.expire_all()
    actual = labs_postgresql_session.get(models.LabResult, row_id)
    assert actual.entered_value == Decimal("5.270")
    assert actual.entered_value.as_tuple().exponent == -3
    assert actual.created_at.tzinfo is not None
    assert actual.updated_at.tzinfo is not None


def test_database_unique_not_just_service(labs_postgresql_session, lab_owner):
    labs_postgresql_session.add_all([result(lab_owner.id), result(lab_owner.id)])
    with pytest.raises(IntegrityError) as caught:
        labs_postgresql_session.commit()
    assert caught.value.orig.diag.constraint_name == "uq_lab_result_principal_test_date"


def test_unique_scope_allows_other_owner_test_and_date(labs_postgresql_session, lab_owner):
    other = Principal(auth_user_id=uuid4())
    labs_postgresql_session.add(other)
    labs_postgresql_session.flush()
    labs_postgresql_session.add_all(
        [
            result(lab_owner.id),
            result(other.id),
            result(lab_owner.id, test_key="ferritin"),
            result(lab_owner.id, test_date=date(2026, 9, 18)),
        ]
    )
    labs_postgresql_session.commit()
    assert labs_postgresql_session.exec(text("SELECT count(*) FROM lab_result")).scalar_one() == 4


@pytest.mark.parametrize(
    "value", ["NaN", "Infinity", "-Infinity", "-0.01", "1" * 129, "0." + "0" * 126 + "1"]
)
def test_direct_numeric_invalid_values_rejected(labs_postgresql_session, lab_owner, value):
    with pytest.raises(IntegrityError) as caught:
        labs_postgresql_session.execute(
            text(
                "INSERT INTO lab_result (id, principal_id, test_key, test_date, entered_value, "
                "entered_unit, created_at, updated_at) VALUES "
                "(:id, :owner, 'hba1c', '2026-09-19', CAST(:value AS numeric), '%', now(), now())"
            ),
            {"id": uuid4(), "owner": lab_owner.id, "value": value},
        )
    assert caught.value.orig.diag.constraint_name in {
        "ck_lab_result_value_finite_nonnegative",
        "ck_lab_result_value_length",
    }


@pytest.mark.parametrize("value", ["1" * 128, "0." + "0" * 125 + "1", "0.000"])
def test_numeric_boundary_round_trip(labs_postgresql_session, lab_owner, value):
    row = result(lab_owner.id, entered_value=Decimal(value))
    labs_postgresql_session.add(row)
    labs_postgresql_session.commit()
    labs_postgresql_session.refresh(row)
    assert format(row.entered_value, "f") == value


@pytest.mark.parametrize(
    "field,value",
    [
        ("test_key", ""),
        ("entered_unit", ""),
        ("test_date", None),
        ("entered_value", None),
        ("test_key", "a" * 65),
        ("entered_unit", "a" * 65),
    ],
)
def test_required_bounded_facts_enforced(labs_postgresql_session, lab_owner, field, value):
    from sqlalchemy.exc import DataError

    labs_postgresql_session.add(result(lab_owner.id, **{field: value}))
    with pytest.raises((IntegrityError, DataError)):
        labs_postgresql_session.commit()


def test_owner_foreign_key_restricts_deletion(labs_postgresql_session, lab_owner):
    labs_postgresql_session.add(result(lab_owner.id))
    labs_postgresql_session.commit()
    labs_postgresql_session.execute(
        text("DELETE FROM profile WHERE principal_id=:id"), {"id": lab_owner.id}
    )
    with pytest.raises(IntegrityError) as caught:
        labs_postgresql_session.execute(
            text("DELETE FROM principal WHERE id=:id"), {"id": lab_owner.id}
        )
    assert caught.value.orig.diag.table_name == "lab_result"


@pytest.mark.parametrize(
    "operation,expires,allowed",
    [
        ("lab_results.create.v1", None, True),
        ("lab_results.create.v1", datetime(2026, 9, 21, tzinfo=timezone.utc), False),
        ("target_plan.write", None, False),
        ("target_plan.write", datetime(2026, 9, 21, tzinfo=timezone.utc), True),
        ("unrelated.operation", None, False),
    ],
)
def test_only_labs_receipts_are_durable(
    labs_postgresql_session, lab_owner, operation, expires, allowed
):
    record = IdempotencyRecord(
        principal_id=lab_owner.id,
        operation=operation,
        idempotency_key=str(uuid4()),
        request_hash="a" * 64,
        state=IdempotencyState.in_progress,
        response_document=null(),
        expires_at=expires,
    )
    labs_postgresql_session.add(record)
    if allowed:
        labs_postgresql_session.commit()
        labs_postgresql_session.refresh(record)
        assert record.expires_at == expires
    else:
        with pytest.raises(IntegrityError) as caught:
            labs_postgresql_session.commit()
        assert caught.value.orig.diag.constraint_name == "ck_idempotency_operation_expiry"


def test_fixture_supports_two_independent_sessions(labs_postgresql_database, lab_owner):
    with (
        Session(labs_postgresql_database.engine) as first,
        Session(labs_postgresql_database.engine) as second,
    ):
        row = result(lab_owner.id)
        first.add(row)
        first.commit()
        observed = second.get(models.LabResult, row.id)
        assert observed.entered_value == Decimal("5.270")


def test_scoped_fact_fixture_observes_committed_changes(
    labs_postgresql_database, lab_result, get_result_fact
):
    with Session(labs_postgresql_database.engine) as writer:
        row = writer.get(models.LabResult, lab_result.id)
        row.entered_value = Decimal("5.270")
        writer.add(row)
        other = Principal(auth_user_id=uuid4())
        writer.add(other)
        writer.flush()
        other_result = result(other.id)
        writer.add(other_result)
        writer.commit()
        other_id = other_result.id
    assert get_result_fact(lab_result.id).entered_value.as_tuple().exponent == -3
    assert get_result_fact(uuid4()) is None
    assert get_result_fact(other_id) is None


def test_date_fixtures_keep_history_order_separate_from_update_order(seeded_lab_history):
    rows = seeded_lab_history.session.exec(
        text(
            "SELECT test_date, entered_value, updated_at FROM lab_result WHERE principal_id=:id ORDER BY test_date"
        ).bindparams(id=seeded_lab_history.owner_id)
    ).all()
    assert [(row.test_date, row.entered_value) for row in rows] == [
        (date(2026, 1, 1), Decimal("5.2")),
        (date(2026, 9, 1), Decimal("5.7")),
    ]
    assert rows[0].updated_at == seeded_lab_history.january_updated_at > rows[1].updated_at

@pytest.mark.parametrize("labs_first", [True, False])
def test_profile_dob_and_lab_insert_serialize_on_owner_lock(
    labs_postgresql_database, labs_postgresql_session, lab_owner,
    run_owner_lock_race, monkeypatch, labs_first,
):
    from sqlmodel import select
    from app.core.auth import PrincipalContext
    from app.labs.catalog import load_catalog
    from app.models import Profile, TargetPlan
    from app.schemas import TargetPlanWriteRequest
    from app.services.profile import to_target_response
    from app.services.target_plans import TargetPlanError, write_target_plan
    from app.services.labs import create_results
    from app.services.labs_errors import LabValidationError
    from labs_fixtures import LABS_TODAY, request
    from test_target_plans import profile_payload

    owner_id = lab_owner.id
    labs_postgresql_session.rollback()
    monkeypatch.setattr("app.services.target_plans._database_riyadh_date", lambda _: LABS_TODAY)
    monkeypatch.setattr("app.services.labs.database_calendar_date", lambda _: LABS_TODAY)
    # This DOB is adult today, but 17 at yesterday's test date.
    payload = TargetPlanWriteRequest.model_validate(profile_payload() | {
        "sex": "female", "birth_date": "2008-09-20", "confirmed": True,
        "effective_from": LABS_TODAY, "expected_preview_hash": "0" * 64,
    })
    payload.expected_preview_hash = to_target_response(payload, LABS_TODAY).preview_hash

    def write_profile(session):
        try:
            response, replayed = write_target_plan(
                session, PrincipalContext(owner_id), payload, "concurrent-dob",
            )
            assert not replayed
            return response.plan.id
        except TargetPlanError as error:
            return error.code

    def write_lab(session):
        try:
            receipt, replayed = create_results(session, lab_owner.context,
                request("2026-09-19", [("hba1c", "5.2", "%")]), "concurrent-lab", load_catalog())
            assert not replayed
            return receipt.result_ids[0]
        except LabValidationError as error:
            return error.errors[0].code

    first, second = run_owner_lock_race(
        owner_id,
        write_lab if labs_first else write_profile,
        write_profile if labs_first else write_lab,
    )
    with Session(labs_postgresql_database.engine) as check:
        profile = check.exec(select(Profile).where(Profile.principal_id == owner_id)).one()
        labs = check.exec(select(models.LabResult)).all()
        plans = check.exec(select(TargetPlan)).all()
        receipts = check.exec(select(IdempotencyRecord)).all()
        if labs_first:
            assert second == "LABS_ADULT_HISTORY_REQUIRED"
            assert len(labs) == 1 and labs[0].id == first
            assert profile.birth_date == date(1990, 1, 1)
            assert not plans and len(receipts) == 1
            assert receipts[0].operation == "lab_results.create.v1"
        else:
            assert second == "LAB_ADULT_REQUIRED"
            assert profile.birth_date == date(2008, 9, 20)
            assert len(plans) == 1 and plans[0].id == first
            assert len(receipts) == 1
            assert not labs


@pytest.mark.parametrize("projection", ["overview", "detail"])
def test_read_snapshot_survives_concurrent_dob_and_result_commit(
    labs_postgresql_database,
    labs_postgresql_session,
    lab_owner,
    lab_result,
    monkeypatch,
    projection,
):
    from sqlalchemy import event
    from sqlmodel import select
    from app.labs.catalog import load_catalog
    from app.services import labs

    monkeypatch.setattr(labs, "database_calendar_date", lambda _: date(2026, 9, 20))
    owner_id, result_id = lab_owner.id, lab_result.id
    # Warm stale identities too; scalar snapshot columns must bypass this cache.
    labs_postgresql_session.get(models.Profile, lab_owner.profile.id)
    written = False

    def commit_after_snapshot(connection, cursor, statement, parameters, context, executemany):
        nonlocal written
        if (
            written
            or not statement.lstrip().upper().startswith("SELECT")
            or "lab_result" not in statement
        ):
            return
        written = True
        with Session(labs_postgresql_database.engine) as writer:
            writer.exec(text("SET LOCAL lock_timeout = '2s'"))
            writer.exec(select(Principal).where(Principal.id == owner_id).with_for_update()).one()
            profile = writer.exec(
                select(models.Profile).where(models.Profile.principal_id == owner_id)
            ).one()
            profile.birth_date = date(1980, 1, 1)  # Still adult at every result date.
            row = writer.get(models.LabResult, result_id)
            row.entered_value = Decimal("6.7")
            writer.add_all([profile, row])
            writer.commit()

    def read():
        if projection == "overview":
            return (
                labs.read_labs(labs_postgresql_session, owner_id, False, load_catalog())
                .items[0]
                .latest
            )
        return labs.read_lab_test(
            labs_postgresql_session, owner_id, "hba1c", False, load_catalog()
        ).results[0]

    event.listen(labs_postgresql_database.engine, "after_cursor_execute", commit_after_snapshot)
    try:
        old = read()
    finally:
        event.remove(labs_postgresql_database.engine, "after_cursor_execute", commit_after_snapshot)
    assert written
    assert (old.age_years, old.display_value, old.status.code) == (36, "5.2", "normal")
    fresh = read()
    assert (fresh.age_years, fresh.display_value, fresh.status.code) == (
        46,
        "6.7",
        "diabetes_range",
    )


def test_edit_response_survives_later_delete_and_profile_change(
    labs_postgresql_database, labs_postgresql_session, lab_owner, lab_result, monkeypatch
):
    from sqlalchemy import event
    from sqlmodel import select
    from app.labs.catalog import load_catalog
    from app.services import labs
    from test_labs import patch_request

    session = labs_postgresql_session
    result_id, owner_id = lab_result.id, lab_owner.id
    monkeypatch.setattr(labs, "database_calendar_date", lambda _: date(2026, 9, 20))
    original = labs.project_result
    projected = []

    def project(row, profile, catalog):
        assert not session.in_transaction(), "Interpretation must happen after commit"
        projected.append(row.id)
        return original(row, profile, catalog)

    def after_commit(_):
        with Session(labs_postgresql_database.engine) as writer:
            labs.delete_result(writer, lab_owner.context, result_id)
            profile = writer.exec(select(models.Profile).where(models.Profile.principal_id == owner_id)).one()
            profile.birth_date = date(1980, 1, 1)
            writer.add(profile)
            writer.commit()

    monkeypatch.setattr(labs, "project_result", project)
    event.listen(session, "after_commit", after_commit)
    try:
        response = labs.update_result(session, lab_owner.context, result_id,
            patch_request(value="6.700", expected_updated_at=lab_result.updated_at), load_catalog())
    finally:
        event.remove(session, "after_commit", after_commit)
    assert projected == [result_id]
    assert (response.entered_value, response.age_years, response.status.code) == ("6.700", 36, "diabetes_range")
    with Session(labs_postgresql_database.engine) as check:
        assert check.get(models.LabResult, result_id) is None


@pytest.mark.parametrize("edit_first", [True, False])
def test_concurrent_edit_and_create_duplicate_serialize(
    labs_postgresql_session, lab_owner, lab_result, run_owner_lock_race, monkeypatch, edit_first
):
    from app.labs.catalog import load_catalog
    from app.services import labs
    from app.services.labs_errors import LabValidationError
    from labs_fixtures import request
    from test_labs import patch_request

    result_id = lab_result.id
    expected_updated_at = lab_result.updated_at
    labs_postgresql_session.rollback()
    monkeypatch.setattr(labs, "database_calendar_date", lambda _: date(2026, 9, 20))

    def edit(session):
        try:
            return labs.update_result(session, lab_owner.context, result_id,
                patch_request("2026-09-18", expected_updated_at=expected_updated_at), load_catalog()).id
        except LabValidationError as error:
            return error.errors[0].code

    def create(session):
        try:
            return labs.create_results(session, lab_owner.context,
                request("2026-09-18", [("hba1c", "5.8", "%")]), "race-create", load_catalog())[0].result_ids[0]
        except LabValidationError as error:
            return error.errors[0].code

    first, second = run_owner_lock_race(lab_owner.id, edit if edit_first else create, create if edit_first else edit)
    assert isinstance(first, type(result_id)) and second == "LAB_DUPLICATE"
    labs_postgresql_session.expire_all()
    row = labs_postgresql_session.get(models.LabResult, result_id)
    assert row.test_date == date(2026, 9, 18 if edit_first else 19)


@pytest.mark.parametrize("edit_first", [True, False])
def test_profile_dob_and_edit_serialize_on_owner_lock(
    labs_postgresql_session, lab_owner, lab_result, run_owner_lock_race, monkeypatch, edit_first
):
    from app.labs.catalog import load_catalog
    from app.schemas import TargetPlanWriteRequest
    from app.services import labs
    from app.services.labs_errors import LabValidationError
    from app.services.profile import to_target_response
    from app.services.target_plans import TargetPlanError, write_target_plan
    from labs_fixtures import LABS_TODAY
    from test_labs import patch_request
    from test_target_plans import profile_payload

    result_id = lab_result.id
    # Existing result is valid for both DOBs; only the requested backdate conflicts.
    lab_result.test_date = LABS_TODAY
    labs_postgresql_session.add(lab_result)
    labs_postgresql_session.commit()
    expected_updated_at = lab_result.updated_at
    monkeypatch.setattr(labs, "database_calendar_date", lambda _: LABS_TODAY)
    monkeypatch.setattr("app.services.target_plans._database_riyadh_date", lambda _: LABS_TODAY)
    payload = TargetPlanWriteRequest.model_validate(profile_payload() | {
        "sex": "female", "birth_date": "2008-09-20", "confirmed": True,
        "effective_from": LABS_TODAY, "expected_preview_hash": "0" * 64,
    })
    payload.expected_preview_hash = to_target_response(payload, LABS_TODAY).preview_hash

    def edit(session):
        try:
            return labs.update_result(session, lab_owner.context, result_id,
                patch_request("2026-09-19", expected_updated_at=expected_updated_at), load_catalog()).id
        except LabValidationError as error:
            return error.errors[0].code

    def profile(session):
        try:
            return write_target_plan(session, lab_owner.context, payload, "dob-edit-race")[0].plan.id
        except TargetPlanError as error:
            return error.code

    first, second = run_owner_lock_race(lab_owner.id, edit if edit_first else profile, profile if edit_first else edit)
    assert isinstance(first, type(result_id))
    assert second == ("LABS_ADULT_HISTORY_REQUIRED" if edit_first else "LAB_ADULT_REQUIRED")
    labs_postgresql_session.expire_all()
    row = labs_postgresql_session.get(models.LabResult, result_id)
    assert row.test_date == date(2026, 9, 19 if edit_first else 20)
