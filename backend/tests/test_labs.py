"""Atomic Labs creation and durable receipts against real PostgreSQL."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.labs.catalog import load_catalog
from app.models import IdempotencyRecord, LabResult, Principal, Profile
from labs_fixtures import count_receipts, count_results, request


@pytest.fixture
def service(monkeypatch):
    from app.services import labs

    monkeypatch.setattr(labs, "database_calendar_date", lambda session: date(2026, 9, 20))
    return labs


def test_batch_is_atomic_on_existing_conflict(service, labs_postgresql_session, lab_owner):
    from app.services.labs_errors import LabValidationError

    session = labs_postgresql_session
    service.create_results(
        session,
        lab_owner.context,
        request("2026-09-19", [("hba1c", "5.2", "%")]),
        "first",
        load_catalog(),
    )
    with pytest.raises(LabValidationError) as error:
        service.create_results(
            session,
            lab_owner.context,
            request("2026-09-19", [("hba1c", "5.3", "%"), ("ferritin", "70", "ng/mL")]),
            "conflict",
            load_catalog(),
        )
    assert error.value.status_code == 409
    assert error.value.errors[0].loc == ["body", "results", 0, "test_key"]
    assert error.value.errors[0].test_key == "hba1c"
    assert count_results(session, lab_owner.id, "ferritin") == 0
    assert count_receipts(session, lab_owner.id, "conflict") == 0


def test_receipt_survives_lost_response_and_original_edits_or_deletion(
    service,
    labs_postgresql_session,
    lab_owner,
):
    session = labs_postgresql_session
    payload = request("2026-09-19", [("hba1c", "5.270", "%"), ("ferritin", "70", "ng/mL")])
    saved = []

    def lost_response():
        saved.append(
            service.create_results(session, lab_owner.context, payload, "lost", load_catalog())
        )
        raise ConnectionError("Synthetic transport loss after committed response")

    with pytest.raises(ConnectionError):
        lost_response()
    receipt, replayed = saved[0]
    assert not replayed
    rows = session.exec(select(LabResult).order_by(LabResult.test_key)).all()
    facts = [(row.id, row.created_at, row.updated_at) for row in rows]
    replay, replayed = service.create_results(
        session, lab_owner.context, payload, "lost", load_catalog()
    )
    assert replayed and replay == receipt
    assert [
        (row.id, row.created_at, row.updated_at)
        for row in session.exec(select(LabResult).order_by(LabResult.test_key)).all()
    ] == facts
    rows[0].entered_value = Decimal("77")
    session.add(rows[0])
    session.delete(rows[1])
    session.delete(session.exec(select(Profile).where(Profile.principal_id == lab_owner.id)).one())
    session.commit()
    catalog = replace(load_catalog(), tests={})
    replay, replayed = service.create_results(session, lab_owner.context, payload, "lost", catalog)
    assert replayed and replay == receipt
    assert count_results(session, lab_owner.id) == 1
    ledger = session.exec(select(IdempotencyRecord)).one()
    assert ledger.response_status == 201 and ledger.expires_at is None
    assert ledger.resource_type == "lab_result_set" and ledger.resource_id is None
    assert ledger.response_document == {
        "receipt_version": 1,
        "result_ids": [str(i) for i in receipt.result_ids],
    }
    assert ledger.state == "completed" and ledger.completed_at is not None
    assert len(ledger.request_hash) == 64


def test_idempotency_normalizes_spelling_and_row_order(service, labs_postgresql_session, lab_owner):
    first = request("2026-09-19", [("hba1c", "٠٠٥٫٢٧٠", "%"), ("ferritin", "070", "ng/mL")])
    second = request("2026-09-19", [("ferritin", "70", "ng/mL"), ("hba1c", "5.270", "%")])
    assert service.canonical_request_hash(first) == service.canonical_request_hash(second)
    assert (
        service.canonical_request_hash(first)
        == "064a7f1adbae916f37477421e8b58de40bf795a2074b1e43f457dfcafdea133e"
    )
    original, _ = service.create_results(
        labs_postgresql_session, lab_owner.context, first, "same", load_catalog()
    )
    replay, replayed = service.create_results(
        labs_postgresql_session, lab_owner.context, second, "same", load_catalog()
    )
    assert replayed and replay == original
    assert count_results(labs_postgresql_session, lab_owner.id) == 2


@pytest.mark.parametrize(
    "day,value,unit",
    [
        ("2026-09-19", "5.27", "%"),
        ("2026-09-19", "5.271", "%"),
        ("2026-09-18", "5.270", "%"),
        ("2026-09-19", "5.270", "mmol/mol"),
    ],
)
def test_idempotency_changed_identity_conflicts(
    service, labs_postgresql_session, lab_owner, day, value, unit
):
    from app.services.labs_errors import LabValidationError

    service.create_results(
        labs_postgresql_session,
        lab_owner.context,
        request("2026-09-19", [("hba1c", "5.270", "%")]),
        "same",
        load_catalog(),
    )
    with pytest.raises(LabValidationError) as caught:
        service.create_results(
            labs_postgresql_session,
            lab_owner.context,
            request(day, [("hba1c", value, unit)]),
            "same",
            load_catalog(),
        )
    assert caught.value.status_code == 409
    assert caught.value.errors[0].code == "LAB_IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize(
    "bad_date", ["2025-02-29", "2026-09-19T00:00:00", 1790000000, "20260919", date(2026, 9, 19)]
)
def test_batch_requires_real_iso_date_string(bad_date):
    with pytest.raises(ValidationError):
        request(bad_date, [("hba1c", "5.2", "%")])


@pytest.mark.parametrize(
    "bad_value", ["", "  ", "-1", "1e3", "NaN", "Infinity", "<5", 5.2, None, "1" * 129]
)
def test_batch_rejects_non_plain_or_overlong_values(bad_value):
    with pytest.raises(ValidationError):
        request("2026-09-19", [("hba1c", bad_value, "%")])


@pytest.mark.parametrize("rows", [[], [("hba1c", "5.2", "%")] * 52])
def test_batch_cardinality(rows):
    with pytest.raises(ValidationError):
        request("2026-09-19", rows)


def test_batch_rejects_missing_value_and_unknown_fields():
    from app.schemas import LabCreateRequest

    for row in (
        {"test_key": "hba1c", "entered_unit": "%"},
        {"test_key": "hba1c", "entered_value": "5.2", "entered_unit": "%", "owner": "other"},
    ):
        with pytest.raises(ValidationError):
            LabCreateRequest.model_validate({"test_date": "2026-09-19", "results": [row]})


@pytest.mark.parametrize(
    "rows,code",
    [
        ([("hba1c", "5.2", "%"), ("bogus", "1", "%")], "LAB_TEST_UNSUPPORTED"),
        ([("hba1c", "5.2", "%"), ("ferritin", "1", "bogus")], "LAB_UNIT_UNSUPPORTED"),
        ([("hba1c", "5.2", "%"), ("hba1c", "5.3", "%")], "LAB_DUPLICATE"),
    ],
)
def test_batch_invalid_final_row_rolls_back(
    service, labs_postgresql_session, lab_owner, rows, code
):
    from app.services.labs_errors import LabValidationError

    with pytest.raises(LabValidationError) as caught:
        service.create_results(
            labs_postgresql_session,
            lab_owner.context,
            request("2026-09-19", rows),
            "invalid",
            load_catalog(),
        )
    assert code in [error.code for error in caught.value.errors]
    assert count_results(labs_postgresql_session, lab_owner.id) == 0
    assert count_receipts(labs_postgresql_session, lab_owner.id, "invalid") == 0


@pytest.mark.parametrize("failure", ["flush", "commit"])
def test_batch_unexpected_failure_rolls_back(
    service, labs_postgresql_session, lab_owner, monkeypatch, failure
):
    session = labs_postgresql_session
    original = getattr(session, failure)

    def fail(*args, **kwargs):
        if failure == "flush":
            has_result = any(isinstance(row, LabResult) for row in session.new)
            original(*args, **kwargs)
            if not has_result:
                return
        else:
            session.flush()
        raise RuntimeError("synthetic persistence failure")

    with monkeypatch.context() as patch:
        patch.setattr(session, failure, fail)
        with pytest.raises(RuntimeError, match="synthetic persistence failure"):
            service.create_results(
                session,
                lab_owner.context,
                request("2026-09-19", [("hba1c", "5.2", "%")]),
                "failure",
                load_catalog(),
            )
    assert (
        count_results(session, lab_owner.id)
        == count_receipts(session, lab_owner.id, "failure")
        == 0
    )


def test_batch_validates_canonical_domain_without_status(
    service, labs_postgresql_session, lab_owner
):
    from app.services.labs_errors import LabValidationError

    catalog = load_catalog()
    test = catalog.tests["hba1c"]
    # A synthetic future registry conversion makes this entered value negative canonically.
    synthetic = replace(test, conversion=replace(test.conversion, pre_offset=Decimal("10")))
    catalog = replace(catalog, tests={"hba1c": synthetic})
    with pytest.raises(LabValidationError) as caught:
        service.create_results(
            labs_postgresql_session,
            lab_owner.context,
            request("2026-09-19", [("hba1c", "1", "mmol/mol")]),
            "canonical",
            catalog,
        )
    assert caught.value.errors[0].code == "LAB_DECIMAL_INVALID"
    assert count_results(labs_postgresql_session, lab_owner.id) == 0


def test_batch_collects_multiple_field_errors(service, labs_postgresql_session, lab_owner):
    from app.services.labs_errors import LabValidationError

    with pytest.raises(LabValidationError) as caught:
        service.create_results(
            labs_postgresql_session,
            lab_owner.context,
            request("2026-09-21", [("hba1c", "5.2", "bad"), ("unknown", "1", "%")]),
            "multiple",
            load_catalog(),
        )
    assert [(e.code, e.loc) for e in caught.value.errors] == [
        ("LAB_DATE_FUTURE", ["body", "test_date"]),
        ("LAB_UNIT_UNSUPPORTED", ["body", "results", 0, "entered_unit"]),
        ("LAB_TEST_UNSUPPORTED", ["body", "results", 1, "test_key"]),
    ]


def test_batch_admin_cannot_write_own_results(service, labs_postgresql_session, lab_admin):
    from app.services.labs_errors import LabValidationError

    with pytest.raises(LabValidationError) as caught:
        service.create_results(
            labs_postgresql_session,
            lab_admin.context,
            request("2026-09-19", [("hba1c", "5.2", "%")]),
            "admin",
            load_catalog(),
        )
    assert caught.value.status_code == 403 and caught.value.errors[0].code == "LAB_READ_ONLY"
    assert count_results(labs_postgresql_session, lab_admin.id) == 0


@pytest.mark.parametrize("value", ["0", "5.270", "9" * 128, "0." + "1" * 126])
def test_batch_preserves_exact_storage_at_boundaries(
    service, labs_postgresql_session, lab_owner, value
):
    receipt, replayed = service.create_results(
        labs_postgresql_session,
        lab_owner.context,
        request("2026-09-19", [("hba1c", value, "%")]),
        "x" * 128,
        load_catalog(),
    )
    assert not replayed
    actual = labs_postgresql_session.get(LabResult, receipt.result_ids[0])
    assert format(actual.entered_value, "f") == value


def test_batch_maps_only_known_unique_constraint_with_owner_locations(
    service,
    labs_postgresql_session,
    lab_owner,
):
    from app.services.labs_errors import LabValidationError

    session = labs_postgresql_session
    saved, _ = service.create_results(
        session,
        lab_owner.context,
        request("2026-09-19", [("ferritin", "70", "ng/mL")]),
        "seed",
        load_catalog(),
    )

    def competing_update(session, flush_context, instances):
        if not any(isinstance(row, LabResult) for row in session.new):
            return
        # An independent raw writer bypasses the application owner-lock protocol.
        # It changes no FK, so it can race the constrained insert under test.
        with Session(session.get_bind()) as other:
            row = other.get(LabResult, saved.result_ids[0])
            row.test_key = "hba1c"
            row.entered_unit = "%"
            other.add(row)
            other.commit()

    event.listen(session, "before_flush", competing_update)
    try:
        with pytest.raises(LabValidationError) as caught:
            service.create_results(
                session,
                lab_owner.context,
                request("2026-09-19", [("hba1c", "5.2", "%")]),
                "constraint",
                load_catalog(),
            )
    finally:
        event.remove(session, "before_flush", competing_update)
    assert caught.value.status_code == 409
    assert [(e.test_key, e.loc) for e in caught.value.errors] == [
        ("hba1c", ["body", "results", 0, "test_key"]),
    ]
    assert count_receipts(session, lab_owner.id, "constraint") == 0
    assert count_results(session, lab_owner.id) == 1


def test_batch_does_not_hide_unexpected_database_constraint(
    service, labs_postgresql_session, lab_owner
):
    session = labs_postgresql_session

    def corrupt_pending_fact(session, flush_context, instances):
        for row in session.new:
            if isinstance(row, LabResult):
                row.entered_unit = ""

    event.listen(session, "before_flush", corrupt_pending_fact)
    try:
        with pytest.raises(IntegrityError) as caught:
            service.create_results(
                session,
                lab_owner.context,
                request("2026-09-19", [("hba1c", "5.2", "%")]),
                "unexpected",
                load_catalog(),
            )
    finally:
        event.remove(session, "before_flush", corrupt_pending_fact)
    assert caught.value.orig.diag.constraint_name == "ck_lab_result_entered_unit_nonempty"
    assert (
        count_receipts(session, lab_owner.id, "unexpected")
        == count_results(session, lab_owner.id)
        == 0
    )


@pytest.mark.parametrize("key", ["", " ", "hello world", "x" * 129, "ع", "a\n"])
def test_idempotency_key_validation(service, labs_postgresql_session, lab_owner, key):
    from app.services.labs_errors import LabValidationError

    with pytest.raises(LabValidationError) as caught:
        service.create_results(
            labs_postgresql_session,
            lab_owner.context,
            request("2026-09-19", [("hba1c", "5.2", "%")]),
            key,
            load_catalog(),
        )
    assert caught.value.status_code == 422


@pytest.mark.parametrize("change,status", [("disabled", 401), ("admin", 403)])
def test_receipt_rechecks_current_actor_despite_stale_context(
    service, labs_postgresql_session, lab_owner, change, status
):
    from app.services.labs_errors import LabValidationError

    session = labs_postgresql_session
    payload = request("2026-09-19", [("hba1c", "5.2", "%")])
    service.create_results(session, lab_owner.context, payload, "auth", load_catalog())
    cached = session.get(Principal, lab_owner.id)
    with Session(session.get_bind()) as other:
        actor = other.get(Principal, lab_owner.id)
        setattr(actor, "status" if change == "disabled" else "role", change)
        other.add(actor)
        other.commit()
    assert cached.status == "active" and cached.role == "user"
    with pytest.raises(LabValidationError) as caught:
        service.create_results(session, lab_owner.context, payload, "auth", load_catalog())
    assert caught.value.status_code == status


@pytest.mark.parametrize(
    "mode,code",
    [
        ("missing", "LAB_PROFILE_REQUIRED"),
        ("minor", "LAB_ADULT_REQUIRED"),
        ("future", "LAB_DATE_FUTURE"),
    ],
)
def test_batch_profile_and_date_validation(service, labs_postgresql_session, lab_owner, mode, code):
    from app.services.labs_errors import LabValidationError

    session = labs_postgresql_session
    profile = session.exec(select(Profile).where(Profile.principal_id == lab_owner.id)).one()
    if mode == "missing":
        session.delete(profile)
    elif mode == "minor":
        profile.birth_date = date(2010, 1, 1)
        session.add(profile)
    session.commit()
    with pytest.raises(LabValidationError) as caught:
        service.create_results(
            session,
            lab_owner.context,
            request("2026-09-21" if mode == "future" else "2026-09-19", [("hba1c", "5.2", "%")]),
            "date",
            load_catalog(),
        )
    assert caught.value.status_code == 422 and code in [e.code for e in caught.value.errors]


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_batch_serializes_same_owner(
    service, lab_owner, run_owner_lock_race, labs_postgresql_session, same_key
):
    from app.services.labs_errors import LabValidationError

    payload = request("2026-09-19", [("hba1c", "5.2", "%")])

    def create(session, key):
        try:
            return service.create_results(session, lab_owner.context, payload, key, load_catalog())
        except LabValidationError as error:
            return error.status_code

    first, second = run_owner_lock_race(
        lab_owner.id, lambda s: create(s, "one"), lambda s: create(s, "one" if same_key else "two")
    )
    assert first[1] is False
    if same_key:
        assert second == (first[0], True)
    else:
        assert second == 409
    assert count_results(labs_postgresql_session, lab_owner.id) == 1


def test_disjoint_owner_batch_does_not_wait_for_other_owner_lock(
    service, labs_postgresql_database, lab_owner, other_lab_owner
):
    from concurrent.futures import ThreadPoolExecutor

    with Session(labs_postgresql_database.engine) as locked:
        locked.exec(select(Principal).where(Principal.id == lab_owner.id).with_for_update()).one()

        def create_other():
            with Session(labs_postgresql_database.engine) as session:
                return service.create_results(
                    session,
                    other_lab_owner.context,
                    request("2026-09-19", [("hba1c", "5.2", "%")]),
                    "other",
                    load_catalog(),
                )

        with ThreadPoolExecutor(max_workers=1) as executor:
            assert executor.submit(create_other).result(timeout=5)[1] is False
