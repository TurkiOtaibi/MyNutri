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
    from app.core.calendar import age_on
    from app.models import Profile, TargetPlan
    from app.schemas import TargetPlanWriteRequest
    from app.services.profile import to_target_response
    from app.services.target_plans import TargetPlanError, write_target_plan
    from labs_fixtures import LABS_TODAY
    from test_target_plans import profile_payload

    owner_id = lab_owner.id
    labs_postgresql_session.rollback()
    monkeypatch.setattr("app.services.target_plans._database_riyadh_date", lambda _: LABS_TODAY)
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

    def write_synthetic_lab(session):
        session.exec(select(Principal).where(Principal.id == owner_id).with_for_update()).one()
        profile = session.exec(
            select(Profile).where(Profile.principal_id == owner_id).with_for_update()
        ).one()
        # Task5 replaces this synthetic locked insert with the real Labs service.
        if age_on(profile.birth_date, date(2026, 9, 19)) < 18:
            session.rollback()
            return "adult_only"
        row = result(owner_id)
        session.add(row)
        session.commit()
        return row.id

    first, second = run_owner_lock_race(
        owner_id,
        write_synthetic_lab if labs_first else write_profile,
        write_profile if labs_first else write_synthetic_lab,
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
            assert not plans and not receipts
        else:
            assert second == "adult_only"
            assert profile.birth_date == date(2008, 9, 20)
            assert len(plans) == 1 and plans[0].id == first
            assert len(receipts) == 1
            assert not labs
