"""Atomic Labs creation and durable receipts against real PostgreSQL."""

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.labs.catalog import load_catalog
from app.models import IdempotencyRecord, LabResult, Principal, Profile
from labs_fixtures import count_receipts, count_results, request


def patch_request(day="2026-09-19", value="5.270", unit="%", *, expected_updated_at=None, **extra):
    from app.schemas import LabResultPatch

    return LabResultPatch.model_validate(
        {"test_date": day, "entered_value": value, "entered_unit": unit,
         "expected_updated_at": expected_updated_at or datetime(2026, 9, 19, tzinfo=timezone.utc), **extra}
    )


@pytest.mark.parametrize("field", ["test_key", "principal_id", "owner", "id", "unknown"])
def test_edit_schema_rejects_immutable_and_unknown_fields(field):
    with pytest.raises(ValidationError):
        patch_request(**{field: "hba1c"})


@pytest.mark.parametrize("field", ["test_date", "entered_value", "entered_unit"])
def test_edit_schema_requires_complete_triplet(field):
    from app.schemas import LabResultPatch

    body = {"test_date": "2026-09-19", "entered_value": "5.2", "entered_unit": "%",
            "expected_updated_at": datetime(2026, 9, 19, tzinfo=timezone.utc)}
    del body[field]
    with pytest.raises(ValidationError):
        LabResultPatch.model_validate(body)


@pytest.mark.parametrize("value", ["-1", "1e3", "NaN", "<5", 5.2, "1" * 129])
def test_edit_schema_rejects_invalid_decimal(value):
    with pytest.raises(ValidationError):
        patch_request(value=value)


def test_edit_schema_requires_expected_version_and_rejects_extra_fields():
    from app.schemas import LabResultPatch

    body = {"test_date": "2026-09-19", "entered_value": "5.2", "entered_unit": "%"}
    with pytest.raises(ValidationError) as missing:
        LabResultPatch.model_validate(body)
    assert missing.value.errors()[0]["loc"] == ("expected_updated_at",)
    expected = datetime(2026, 9, 19, tzinfo=timezone.utc)
    assert LabResultPatch.model_validate(body | {"expected_updated_at": expected}).expected_updated_at == expected
    with pytest.raises(ValidationError) as extra:
        LabResultPatch.model_validate(body | {"expected_updated_at": expected, "test_key": "hba1c"})
    assert extra.value.errors()[0]["type"] == "extra_forbidden"


def test_edit_rejects_stale_version_before_other_validation(
    service, labs_postgresql_session, lab_owner, lab_result
):
    from app.services.labs_errors import LabValidationError

    before = lab_result.model_dump()
    stale = before["updated_at"].replace(microsecond=0)
    with pytest.raises(LabValidationError) as caught:
        service.update_result(
            labs_postgresql_session, lab_owner.context, lab_result.id,
            patch_request(day="2007-01-01", value="7.0", expected_updated_at=stale),
            load_catalog(),
        )
    assert caught.value.status_code == 409
    assert [(error.code, error.loc) for error in caught.value.errors] == [
        ("LAB_RESULT_CHANGED", ["body", "expected_updated_at"])
    ]
    assert labs_postgresql_session.get(LabResult, lab_result.id).model_dump() == before


def test_edit_version_advances_when_clock_has_not_advanced(
    service, labs_postgresql_session, lab_owner, lab_result, monkeypatch
):
    from app.services.labs_errors import LabValidationError

    before = lab_result.updated_at
    monkeypatch.setattr(service, "utcnow", lambda: before)
    saved = service.update_result(
        labs_postgresql_session, lab_owner.context, lab_result.id,
        patch_request(value="6.0", expected_updated_at=before), load_catalog(),
    )
    assert saved.updated_at > before
    with pytest.raises(LabValidationError) as caught:
        service.update_result(
            labs_postgresql_session, lab_owner.context, lab_result.id,
            patch_request(value="7.0", expected_updated_at=before), load_catalog(),
        )
    assert caught.value.status_code == 409
    assert caught.value.errors[0].code == "LAB_RESULT_CHANGED"


def test_edit_overwrites_only_owned_fact_and_enforces_duplicate(
    service, labs_postgresql_session, lab_owner, two_dated_results, get_result_fact
):
    from app.services.labs_errors import LabValidationError

    session = labs_postgresql_session
    result_id = two_dated_results.first_id
    before = get_result_fact(result_id).model_dump()
    other_before = get_result_fact(two_dated_results.second_id).model_dump()
    result = service.update_result(
        session, lab_owner.context, result_id,
        patch_request("2026-08-01", "38.797950", "mmol/mol",
                      expected_updated_at=before["updated_at"]), load_catalog(),
    )
    assert result.entered_value == "38.797950"
    assert result.entered_unit == "mmol/mol" and result.test_date == date(2026, 8, 1)
    assert result.test_key == "hba1c" and result.created_at == before["created_at"]
    assert result.updated_at > before["updated_at"]
    assert result.medical_rules_version == load_catalog().version
    assert get_result_fact(two_dated_results.second_id).model_dump() == other_before
    with pytest.raises(LabValidationError) as caught:
        service.update_result(session, lab_owner.context, result_id,
            patch_request(two_dated_results.second_date.isoformat(),
                          expected_updated_at=result.updated_at), load_catalog())
    assert caught.value.status_code == 409
    assert [(e.code, e.loc) for e in caught.value.errors] == [
        ("LAB_DUPLICATE", ["body", "test_date"])
    ]
    assert get_result_fact(result_id).test_date == date(2026, 8, 1)
    # Same date is allowed when the only matching row is this result itself.
    again = service.update_result(session, lab_owner.context, result_id,
        patch_request("2026-08-01", "5.270", expected_updated_at=result.updated_at), load_catalog())
    assert again.entered_value == "5.270" and again.display_value == "5.270"


@pytest.mark.parametrize("day,unit,code", [
    ("2007-12-31", "%", "LAB_ADULT_REQUIRED"),
    ("2026-09-21", "%", "LAB_DATE_FUTURE"),
    ("2026-09-19", "bad", "LAB_UNIT_UNSUPPORTED"),
])
def test_edit_invalid_replacement_leaves_all_facts_unchanged(
    service, labs_postgresql_session, lab_owner, lab_result, day, unit, code
):
    from app.services.labs_errors import LabValidationError

    session = labs_postgresql_session
    before = lab_result.model_dump()
    with pytest.raises(LabValidationError) as caught:
        service.update_result(session, lab_owner.context, lab_result.id,
            patch_request(day, unit=unit, expected_updated_at=before["updated_at"]), load_catalog())
    assert caught.value.status_code == 422
    assert code in [error.code for error in caught.value.errors]
    assert session.get(LabResult, before["id"]).model_dump() == before


@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize("target", ["other", "missing"])
def test_mutations_hide_cross_owner_and_absent_results(
    service, labs_postgresql_session, lab_owner, other_lab_owner, lab_result, operation, target
):
    from fastapi import HTTPException
    from uuid import uuid4

    result_id = lab_result.id if target == "other" else uuid4()
    with pytest.raises(HTTPException) as caught:
        if operation == "update":
            service.update_result(labs_postgresql_session, other_lab_owner.context,
                result_id, patch_request(), load_catalog())
        else:
            service.delete_result(labs_postgresql_session, other_lab_owner.context, result_id)
    assert caught.value.status_code == 404
    assert caught.value.detail["code"] == "RESOURCE_NOT_FOUND"
    assert count_results(labs_postgresql_session, lab_owner.id) == 1


@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize("change,status,code", [
    ("admin", 403, "LAB_READ_ONLY"), ("inactive", 401, "INVALID_CREDENTIAL"),
])
def test_mutations_recheck_current_actor_under_lock(
    service, labs_postgresql_session, lab_owner, lab_result, operation, change, status, code
):
    from app.models import PrincipalRole, PrincipalStatus
    from app.services.labs_errors import LabValidationError

    session = labs_postgresql_session
    result_id = lab_result.id
    with Session(session.get_bind()) as writer:
        actor = writer.get(Principal, lab_owner.id)
        if change == "admin":
            actor.role = PrincipalRole.admin
        else:
            actor.status = PrincipalStatus.disabled
        writer.add(actor)
        writer.commit()
    with pytest.raises(LabValidationError) as caught:
        if operation == "update":
            service.update_result(session, lab_owner.context, result_id, patch_request(), load_catalog())
        else:
            service.delete_result(session, lab_owner.context, result_id)
    assert caught.value.status_code == status and caught.value.errors[0].code == code
    assert count_results(session, lab_owner.id) == 1


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_mutation_unexpected_commit_failure_rolls_back(
    service, labs_postgresql_session, lab_owner, lab_result, monkeypatch, operation
):
    session = labs_postgresql_session
    before = lab_result.model_dump()

    def fail():
        session.flush()
        raise RuntimeError("synthetic persistence failure")

    with monkeypatch.context() as patch:
        patch.setattr(session, "commit", fail)
        with pytest.raises(RuntimeError, match="synthetic persistence failure"):
            if operation == "update":
                service.update_result(session, lab_owner.context, before["id"],
                    patch_request(expected_updated_at=before["updated_at"]), load_catalog())
            else:
                service.delete_result(session, lab_owner.context, before["id"])
    assert session.get(LabResult, before["id"]).model_dump() == before


@pytest.mark.parametrize("delete_latest", [True, False])
def test_delete_recomputes_history_preserves_receipts_and_secure_second_delete(
    service, labs_postgresql_session, lab_owner, seeded_lab_history, delete_latest
):
    from fastapi import HTTPException

    session = labs_postgresql_session
    rows = session.exec(select(LabResult).order_by(LabResult.test_date)).all()
    deleted, remaining = (rows[1], rows[0]) if delete_latest else (rows[0], rows[1])
    deleted_id, remaining_id = deleted.id, remaining.id
    remaining_before = remaining.model_dump()
    receipts_before = session.execute(select(IdempotencyRecord.__table__)).all()
    service.delete_result(session, lab_owner.context, deleted_id)
    overview = service.read_labs(session, lab_owner.id, False, load_catalog())
    assert overview.items[0].latest.id == remaining_id
    assert overview.items[0].last_updated_at == remaining_before["updated_at"]
    assert session.get(LabResult, remaining_id).model_dump() == remaining_before
    with pytest.raises(HTTPException) as caught:
        service.delete_result(session, lab_owner.context, deleted_id)
    assert caught.value.status_code == 404
    service.delete_result(session, lab_owner.context, remaining_id)
    assert service.read_labs(session, lab_owner.id, False, load_catalog()).items == []
    detail = service.read_lab_test(session, lab_owner.id, "hba1c", False, load_catalog())
    assert detail.test.test_key == "hba1c" and detail.results == []
    assert session.execute(select(IdempotencyRecord.__table__)).all() == receipts_before


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


def _run_while_owner_locked(engine, owner_id, worker, wait_for_result=None):
    from concurrent.futures import ThreadPoolExecutor

    with Session(engine) as locked:
        locked.exec(select(Principal).where(Principal.id == owner_id).with_for_update()).one()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                future = executor.submit(worker)
                return wait_for_result(future) if wait_for_result else future.result(timeout=5)
            finally:
                # Release before executor.__exit__ joins even when waiting fails.
                locked.rollback()


def test_disjoint_owner_batch_does_not_wait_for_other_owner_lock(
    service, labs_postgresql_database, lab_owner, other_lab_owner
):
    from sqlalchemy import text

    def create_other():
        with Session(labs_postgresql_database.engine) as session:
            session.exec(text("SET LOCAL lock_timeout = '4s'"))
            session.exec(text("SET LOCAL statement_timeout = '5s'"))
            return service.create_results(
                session,
                other_lab_owner.context,
                request("2026-09-19", [("hba1c", "5.2", "%")]),
                "other",
                load_catalog(),
            )

    assert (
        _run_while_owner_locked(labs_postgresql_database.engine, lab_owner.id, create_other)[1]
        is False
    )


def test_overview_latest_value_uses_test_date_not_edit_time(service, seeded_lab_history):
    history = seeded_lab_history
    response = service.read_labs(history.session, history.owner_id, False, load_catalog())
    item = next(x for x in response.items if x.test_key == "hba1c")
    assert item.latest.test_date == date(2026, 9, 1)
    assert item.latest.display_value == "5.7"
    assert item.last_updated_at == history.january_updated_at
    assert item.latest.medical_rules_version == response.medical_rules_version


@pytest.mark.parametrize("read_only", [False, True])
def test_reference_empty_known_test_and_missing_profile(
    service, labs_postgresql_session, lab_owner, read_only
):
    from fastapi import HTTPException

    session = labs_postgresql_session
    detail = service.read_lab_test(session, lab_owner.id, "ferritin", read_only, load_catalog())
    assert detail.results == detail.chart_zones == []
    assert detail.reference_at_date == detail.server_today == date(2026, 9, 20)
    assert [(z.low, z.high) for z in detail.reference_zones] == [
        (None, "6"),
        ("6", "175"),
        ("175", None),
    ]
    assert detail.eligibility.allowed is (not read_only)
    assert detail.eligibility.reason == ("read_only" if read_only else None)
    assert detail.test.test_key == "ferritin"
    assert "provenance" not in detail.test.model_dump()
    with pytest.raises(HTTPException) as caught:
        service.read_lab_test(session, lab_owner.id, "unknown", read_only, load_catalog())
    assert caught.value.status_code == 404
    assert caught.value.detail["code"] == "RESOURCE_NOT_FOUND"
    session.delete(session.exec(select(Profile).where(Profile.principal_id == lab_owner.id)).one())
    session.commit()
    missing = service.read_lab_test(session, lab_owner.id, "ferritin", read_only, load_catalog())
    assert missing.reference_zones == missing.results == []
    assert missing.eligibility.reason == ("read_only" if read_only else "profile_required")


def test_reference_minor_has_no_invented_adult_reference(
    service, labs_postgresql_session, lab_owner
):
    profile = labs_postgresql_session.get(Profile, lab_owner.profile.id)
    profile.birth_date = date(2010, 1, 1)
    labs_postgresql_session.add(profile)
    labs_postgresql_session.commit()
    response = service.read_lab_test(
        labs_postgresql_session, lab_owner.id, "hba1c", False, load_catalog()
    )
    assert response.eligibility.reason == "adult_only"
    assert response.reference_zones == []


def test_history_mixed_units_complete_and_owner_scoped(
    service, labs_postgresql_session, lab_owner, other_lab_owner
):
    from datetime import timedelta

    session = labs_postgresql_session
    catalog = load_catalog()
    for index in range(35):
        day = date(2026, 8, 1) + timedelta(days=index)
        value, unit = ("88.4", "µmol/L") if index % 2 else ("1.000", "mg/dL")
        service.create_results(
            session,
            lab_owner.context,
            request(day.isoformat(), [("creatinine", value, unit)]),
            str(index),
            catalog,
        )
    service.create_results(
        session,
        other_lab_owner.context,
        request("2026-09-19", [("creatinine", "99", "mg/dL")]),
        "other",
        catalog,
    )
    detail = service.read_lab_test(session, lab_owner.id, "creatinine", True, catalog)
    overview = service.read_labs(session, lab_owner.id, True, catalog)
    assert len(detail.results) == 35
    assert [r.test_date for r in detail.results] == sorted(
        [date(2026, 8, 1) + timedelta(days=i) for i in range(35)], reverse=True
    )
    assert {Decimal(r.display_value) for r in detail.results} == {Decimal(1)}
    assert {r.display_unit for r in detail.results} == {"mg/dL"}
    assert {r.status.code for r in detail.results} == {"in_range"}
    assert all(not r.display_is_approximate for r in detail.results)
    assert overview.items[0].latest == detail.results[0]
    assert detail.reference_at_date == date(2026, 9, 4)
    assert detail.chart_zones[0].from_date == date(2026, 8, 1)
    assert detail.chart_zones[-1].to_date_exclusive == date(2026, 9, 5)
    assert detail.eligibility.reason == "read_only"
    assert len(detail.reference_zones) == 3


def test_reinterpret_registry_and_dob_leave_entered_facts_unchanged(
    service, labs_postgresql_session, lab_owner
):
    from fractions import Fraction
    from types import MappingProxyType
    from app.labs.types import Zone

    session = labs_postgresql_session
    catalog = load_catalog()
    service.create_results(
        session, lab_owner.context, request("2026-09-19", [("hba1c", "5.700", "%")]), "one", catalog
    )
    before = service.read_lab_test(session, lab_owner.id, "hba1c", False, catalog)
    facts_before = session.exec(select(LabResult)).one().model_dump()
    test = catalog.tests["hba1c"]
    zones = (
        Zone("normal", None, Fraction(6), False, False),
        Zone("prediabetes_range", Fraction(6), None, True, False),
    )
    revised = replace(
        catalog,
        version="synthetic-b",
        tests=MappingProxyType(
            {
                **catalog.tests,
                "hba1c": replace(
                    test, rule_slices=tuple(replace(rule, zones=zones) for rule in test.rule_slices)
                ),
            }
        ),
    )
    after = service.read_lab_test(session, lab_owner.id, "hba1c", False, revised)
    assert before.results[0].status.code == "prediabetes_range"
    assert after.results[0].status.code == "normal"
    assert after.results[0].medical_rules_version == after.medical_rules_version == "synthetic-b"
    assert after.reference_zones[0].high == after.chart_zones[0].zones[0].high == "6"
    profile = session.exec(select(Profile).where(Profile.principal_id == lab_owner.id)).one()
    profile.birth_date = date(1980, 1, 1)
    session.add(profile)
    session.commit()
    fresh = service.read_lab_test(session, lab_owner.id, "hba1c", False, revised)
    assert (before.results[0].age_years, fresh.results[0].age_years) == (36, 46)
    assert session.exec(select(LabResult)).one().model_dump() == facts_before


@pytest.mark.parametrize(
    "key,sex,age,old_low,old_high,new_low,new_high",
    [
        ("ferritin", "female", 51, "6", "175", "11", "328"),
        ("calcium_total", "female", 60, "8.6", "10", "8.8", "10.2"),
        ("alp", "male", 19, "55", "149", "40", "129"),
        ("tsh", "female", 20, "0.5", "4.3", "0.3", "4.2"),
        ("free_t4", "female", 20, "1", "1.6", "0.9", "1.7"),
        ("free_t3", "male", 19, "3.3", "5.3", "2", "4.4"),
    ],
)
def test_history_reference_uses_actual_birthday(
    service, labs_postgresql_session, lab_owner, key, sex, age, old_low, old_high, new_low, new_high
):
    session = labs_postgresql_session
    profile = session.exec(select(Profile).where(Profile.principal_id == lab_owner.id)).one()
    profile.birth_date, profile.sex = date(2026 - age, 9, 1), sex
    session.add(profile)
    session.commit()
    catalog = load_catalog()
    for day in ("2026-08-31", "2026-09-02"):
        service.create_results(
            session,
            lab_owner.context,
            request(day, [(key, old_low, catalog.tests[key].canonical_unit)]),
            day,
            catalog,
        )
    response = service.read_lab_test(session, lab_owner.id, key, False, catalog)
    assert [r.age_years for r in response.results] == [age, age - 1]
    assert [(s.from_date, s.to_date_exclusive) for s in response.chart_zones] == [
        (date(2026, 8, 31), date(2026, 9, 1)),
        (date(2026, 9, 1), date(2026, 9, 3)),
    ]
    assert [(s.zones[1].low, s.zones[1].high) for s in response.chart_zones] == [
        (old_low, old_high),
        (new_low, new_high),
    ]
    assert response.reference_zones == response.results[0].reference_zones


def test_history_reads_do_not_autoflush_and_have_bounded_queries(
    service, labs_postgresql_session, lab_owner, seeded_lab_history
):
    session = labs_postgresql_session
    # A stale/dirty identity map must neither alter the response nor write during GET.
    profile = session.exec(select(Profile).where(Profile.principal_id == lab_owner.id)).one()
    profile.birth_date = date(2000, 1, 1)
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(session.get_bind(), "before_cursor_execute", capture)
    try:
        overview = service.read_labs(session, lab_owner.id, False, load_catalog())
        detail = service.read_lab_test(session, lab_owner.id, "hba1c", False, load_catalog())
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", capture)
        session.rollback()
    assert overview.items[0].latest.age_years == detail.results[0].age_years == 36
    assert len(statements) == 2  # Today is pinned by service fixture.
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)


@pytest.mark.parametrize(
    "key,value,unit,display,status,approximate",
    [
        ("hba1c", "38", "mmol/mol", "5.62699", "normal", True),
        ("hba1c", "0", "%", "0", "normal", False),
        ("hba1c", "9" * 128, "%", "9" * 128, "diabetes_range", False),
    ],
)
def test_history_single_point_exact_display_and_extremes(
    service, labs_postgresql_session, lab_owner, key, value, unit, display, status, approximate
):
    service.create_results(
        labs_postgresql_session,
        lab_owner.context,
        request("2026-09-19", [(key, value, unit)]),
        "single",
        load_catalog(),
    )
    detail = service.read_lab_test(
        labs_postgresql_session, lab_owner.id, key, False, load_catalog()
    )
    result = detail.results[0]
    assert (result.display_value, result.status.code, result.display_is_approximate) == (
        display,
        status,
        approximate,
    )
    assert result.created_at == result.updated_at
    assert result.reference_zones[0].high == "5.7"
    assert result.reference_zones[0].high_inclusive is False
    assert result.reference_zones[1].low_inclusive is True
    assert len(detail.chart_zones) == 1
    assert detail.chart_zones[0].to_date_exclusive == date(2026, 9, 20)


def test_disjoint_owner_failure_cleanup_releases_lock_before_join(
    labs_postgresql_database, lab_owner
):
    from concurrent.futures import TimeoutError
    from threading import Event
    from sqlalchemy import text

    started, finished = Event(), Event()

    def blocked_worker():
        with Session(labs_postgresql_database.engine) as session:
            session.exec(text("SET LOCAL lock_timeout = '2s'"))
            started.set()
            session.exec(
                select(Principal).where(Principal.id == lab_owner.id).with_for_update()
            ).one()
            finished.set()

    def forced_timeout(future):
        assert started.wait(1)
        raise TimeoutError("synthetic failure before executor join")

    with pytest.raises(TimeoutError, match="synthetic failure"):
        _run_while_owner_locked(
            labs_postgresql_database.engine, lab_owner.id, blocked_worker, forced_timeout
        )
    assert finished.is_set(), "The lock must be released before executor shutdown waits"


def test_reinterpret_accepted_dob_change_moves_ferritin_birthday(
    service, labs_postgresql_session, lab_owner, monkeypatch
):
    from app.schemas import TargetPlanWriteRequest
    from app.services.profile import to_target_response
    from app.services.target_plans import write_target_plan
    from test_target_plans import profile_payload

    session = labs_postgresql_session
    monkeypatch.setattr(
        "app.services.target_plans._database_riyadh_date", lambda _: date(2026, 9, 20)
    )
    service.create_results(
        session,
        lab_owner.context,
        request("2026-09-19", [("ferritin", "8.00", "ng/mL")]),
        "ferritin",
        load_catalog(),
    )
    before = service.read_lab_test(session, lab_owner.id, "ferritin", False, load_catalog())
    facts_before = session.exec(select(LabResult)).one().model_dump()
    payload = TargetPlanWriteRequest.model_validate(
        profile_payload()
        | {
            "sex": "female",
            "birth_date": "1975-09-19",
            "confirmed": True,
            "effective_from": date(2026, 9, 20),
            "expected_preview_hash": "0" * 64,
        }
    )
    payload.expected_preview_hash = to_target_response(payload, date(2026, 9, 20)).preview_hash
    _, replayed = write_target_plan(session, lab_owner.context, payload, "dob-accepted")
    assert replayed is False
    after = service.read_lab_test(session, lab_owner.id, "ferritin", False, load_catalog())
    assert (before.results[0].status.code, after.results[0].status.code) == ("in_range", "low")
    assert (before.reference_zones[1].low, after.reference_zones[1].low) == ("6", "11")
    assert after.chart_zones[0].age_min == after.results[0].age_years == 51
    assert session.exec(select(LabResult)).one().model_dump() == facts_before


def http_payload(**overrides):
    return {
        "test_date": "2026-09-19",
        "results": [{"test_key": "hba1c", "entered_value": "5.270", "entered_unit": "%"}],
        **overrides,
    }


def test_http_labs_crud_receipt_replay_and_cors(labs_client):
    from app.main import settings

    catalog = labs_client.get("/labs/catalog")
    assert catalog.status_code == 200
    assert len(catalog.json()["tests"]) == 51
    assert len(catalog.json()["categories"]) == 15
    assert len(catalog.json()["panels"]) == 7
    assert not {"sources", "provenance", "content_sha256", "rule_slices"} & set(catalog.json())
    headers = {"Idempotency-Key": "http-create", "Origin": settings.allowed_origins[0]}
    response = labs_client.post("/labs/results", json=http_payload(), headers=headers)
    assert response.status_code == 201, response.text
    assert response.headers["Idempotent-Replayed"] == "false"
    assert response.headers["Access-Control-Allow-Origin"] == settings.allowed_origins[0]
    assert "idempotent-replayed" in response.headers["Access-Control-Expose-Headers"].lower()
    receipt = response.json()
    assert set(receipt) == {"receipt_version", "result_ids"}
    replay = labs_client.post("/labs/results", json=http_payload(), headers=headers)
    assert replay.status_code == 201 and replay.json() == receipt
    assert replay.headers["Idempotent-Replayed"] == "true"
    conflict = labs_client.post("/labs/results", json=http_payload(test_date="2026-09-18"), headers=headers)
    assert conflict.status_code == 409
    assert conflict.json()["detail"][0]["code"] == "LAB_IDEMPOTENCY_CONFLICT"
    duplicate = labs_client.post("/labs/results", json=http_payload(), headers={"Idempotency-Key": "other"})
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"][0]["code"] == "LAB_DUPLICATE"
    overview = labs_client.get("/labs")
    detail = labs_client.get("/labs/tests/hba1c")
    assert overview.status_code == detail.status_code == 200
    assert overview.json()["items"][0]["latest"] == detail.json()["results"][0]
    assert detail.json()["results"][0]["entered_value"] == "5.270"
    result_id = receipt["result_ids"][0]
    patch = labs_client.patch(f"/labs/results/{result_id}", json={
        "test_date": "2026-09-18", "entered_value": "5.1", "entered_unit": "%",
        "expected_updated_at": detail.json()["results"][0]["updated_at"],
    })
    assert patch.status_code == 200 and patch.json()["entered_value"] == "5.1"
    deleted = labs_client.delete(f"/labs/results/{result_id}")
    assert deleted.status_code == 204 and not deleted.content
    replay_deleted = labs_client.post("/labs/results", json=http_payload(), headers=headers)
    assert replay_deleted.status_code == 201 and replay_deleted.json() == receipt
    assert labs_client.get("/labs").json()["items"] == []
    for item in (catalog, response, replay, conflict, duplicate, overview, detail, patch, deleted):
        assert item.headers["Cache-Control"] == "no-store"


def test_http_edit_version_conflict_and_sanitized_patch_shape(labs_client, lab_result):
    result_id = str(lab_result.id)
    current = labs_client.get("/labs/tests/hba1c").json()["results"][0]
    body = {"test_date": current["test_date"], "entered_value": "6.0",
            "entered_unit": "%", "expected_updated_at": current["updated_at"]}
    for invalid in ({key: value for key, value in body.items() if key != "expected_updated_at"},
                    body | {"test_key": "private-sentinel"}):
        response = labs_client.patch(f"/labs/results/{result_id}", json=invalid)
        assert response.status_code == 422
        assert "input" not in response.text and "ctx" not in response.text
        assert "private-sentinel" not in response.text
        assert response.json()["detail"][0]["loc"][-1] in {"expected_updated_at", "test_key"}
    stale = labs_client.patch(f"/labs/results/{result_id}", json=body | {
        "test_date": "2007-01-01", "expected_updated_at": "2000-01-01T00:00:00Z",
    })
    assert stale.status_code == 409
    assert [(error["code"], error["loc"]) for error in stale.json()["detail"]] == [
        ("LAB_RESULT_CHANGED", ["body", "expected_updated_at"])
    ]
    assert stale.json()["detail"][0]["msg"] == (
        "تغيّرت هذه النتيجة منذ فتحها. راجع قيمها الحالية قبل تعديلها مجددًا."
    )
    assert labs_client.get("/labs/tests/hba1c").json()["results"][0] == current
    saved = labs_client.patch(f"/labs/results/{result_id}", json=body)
    assert saved.status_code == 200 and saved.json()["entered_value"] == "6.0"
    assert saved.json()["updated_at"] != current["updated_at"]
    rejected = labs_client.patch(f"/labs/results/{result_id}", json=body | {"entered_value": "7.0"})
    assert rejected.status_code == 409
    assert rejected.json()["detail"][0]["code"] == "LAB_RESULT_CHANGED"
    assert labs_client.get("/labs/tests/hba1c").json()["results"][0] == saved.json()


@pytest.mark.parametrize("value,code", [(5.2, "LAB_DECIMAL_INVALID"), ("1e4", "LAB_DECIMAL_INVALID"),
    ("1" * 129, "LAB_VALUE_TOO_LONG")])
def test_http_nested_errors_are_stable_and_private(labs_client, value, code):
    response = labs_client.post("/labs/results", json=http_payload(results=[
        {"test_key": "hba1c", "entered_value": value, "entered_unit": "%"},
    ]), headers={"Idempotency-Key": "bad"})
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["loc"] == ["body", "results", 0, "entered_value"]
    assert error["field"] == "entered_value" and error["test_key"] == "hba1c"
    assert error["code"] == code
    assert set(error) == {"loc", "field", "test_key", "code", "msg", "type"}
    assert "input" not in response.text and "ctx" not in response.text


@pytest.mark.parametrize("body,code", [
    ({"results": []}, "LAB_BATCH_EMPTY"),
    ({"test_date": "2026-09-21"}, "LAB_DATE_FUTURE"),
    ({"test_date": "2007-01-01"}, "LAB_ADULT_REQUIRED"),
    ({"results": [{"test_key": "hba1c", "entered_value": "5", "entered_unit": "bad"}]}, "LAB_UNIT_UNSUPPORTED"),
    ({"results": [{"test_key": "unknown", "entered_value": "5", "entered_unit": "%"}]}, "LAB_TEST_UNSUPPORTED"),
    ({"sources": "private-source-sentinel"}, "NON_AUTHORITATIVE_FIELD"),
])
def test_http_labs_errors_use_exact_copy(labs_client, body, code):
    from app.services.labs_errors import MESSAGES

    response = labs_client.post("/labs/results", json=http_payload(**body), headers={"Idempotency-Key": "invalid"})
    assert response.status_code == 422
    error = response.json()["detail"][0]
    assert error["code"] == code
    assert error["msg"] == (MESSAGES[code] if code in MESSAGES else "هذا الحقل يحدده الخادم ولا يقبله من العميل.")
    assert "private-source-sentinel" not in response.text


@pytest.mark.parametrize("kind", ["missing_header", "bad_json", "bad_uuid"])
def test_http_framework_validation_never_echoes_payload(labs_client, kind):
    if kind == "missing_header":
        response = labs_client.post("/labs/results", json=http_payload())
    elif kind == "bad_json":
        response = labs_client.post("/labs/results", content='{"private-sentinel":', headers={"Content-Type": "application/json"})
    else:
        response = labs_client.delete("/labs/results/private-sentinel")
    assert response.status_code == 422
    assert response.headers["Cache-Control"] == "no-store"
    assert "private-sentinel" not in response.text
    assert "input" not in response.text and "ctx" not in response.text
    assert all(set(e) <= {"loc", "field", "test_key", "code", "msg", "type"} for e in response.json()["detail"])


def test_http_ownership_and_admin_reads_only(labs_client, lab_result, lab_owner, other_lab_owner, lab_admin, as_actor):
    from uuid import uuid4

    result_id = str(lab_result.id)
    owner_id = str(lab_owner.id)
    as_actor(other_lab_owner)
    assert labs_client.get("/labs").json()["items"] == []
    assert labs_client.get("/labs/tests/hba1c").json()["results"] == []
    patch = {"test_date": "2026-09-19", "entered_value": "5", "entered_unit": "%",
             "expected_updated_at": lab_result.updated_at.isoformat()}
    for method in ("patch", "delete"):
        foreign = labs_client.request(method, f"/labs/results/{result_id}", **({"json": patch} if method == "patch" else {}))
        missing = labs_client.request(method, f"/labs/results/{uuid4()}", **({"json": patch} if method == "patch" else {}))
        assert foreign.status_code == missing.status_code == 404
        assert foreign.json() == missing.json()
        assert result_id not in foreign.text
    as_actor(lab_admin)
    for suffix in ("", "/tests/hba1c"):
        selected = labs_client.get(f"/admin/users/{owner_id}/labs{suffix}")
        assert selected.status_code == 200 and selected.json()["read_only"] is True
        assert selected.json()["eligibility"] == {"allowed": False, "reason": "read_only"}
        assert selected.headers["Cache-Control"] == "no-store"
    assert labs_client.get(f"/admin/users/{owner_id}/labs/tests/hba1c").json()["results"][0]["id"] == result_id
    assert labs_client.get(f"/admin/users/{uuid4()}/labs").status_code == 404
    assert labs_client.get("/labs").json()["read_only"] is True
    for method, path, body in (
        ("post", "/labs/results", http_payload()),
        ("patch", f"/labs/results/{result_id}", patch),
        ("delete", f"/labs/results/{result_id}", None),
    ):
        response = labs_client.request(method, path, json=body, headers={"Idempotency-Key": "admin"})
        assert response.status_code == 403
        assert response.json()["detail"][0]["code"] == "LAB_READ_ONLY"
    assert labs_client.post(f"/admin/users/{owner_id}/labs/results", json=http_payload()).status_code == 404


@pytest.mark.parametrize("operation", ["catalog", "overview", "detail", "create", "patch", "delete", "admin_overview", "admin_detail"])
def test_http_unexpected_errors_are_sanitized(labs_client, lab_owner, lab_admin, as_actor, monkeypatch, caplog, operation):
    from uuid import uuid4
    from app.labs.catalog import get_catalog
    from app.main import app
    from sqlalchemy.exc import StatementError

    def failure(*args, **kwargs):
        raise StatementError("private-medical-sentinel", "SQL sentinel", {"value": "patient-sentinel"}, RuntimeError("secret-sentinel"))

    methods = {
        "overview": ("read_labs", "get", "/labs", None),
        "detail": ("read_lab_test", "get", "/labs/tests/hba1c", None),
        "create": ("create_results", "post", "/labs/results", http_payload()),
        "patch": ("update_result", "patch", f"/labs/results/{uuid4()}", {"test_date": "2026-09-19", "entered_value": "5", "entered_unit": "%", "expected_updated_at": "2026-09-19T00:00:00Z"}),
        "delete": ("delete_result", "delete", f"/labs/results/{uuid4()}", None),
        "admin_overview": ("read_labs", "get", f"/admin/users/{lab_owner.id}/labs", None),
        "admin_detail": ("read_lab_test", "get", f"/admin/users/{lab_owner.id}/labs/tests/hba1c", None),
    }
    if operation == "catalog":
        app.dependency_overrides[get_catalog] = lambda: failure()
        method, path, body = "get", "/labs/catalog", None
    else:
        function, method, path, body = methods[operation]
        monkeypatch.setattr(f"app.services.labs.{function}", failure)
    if operation.startswith("admin"):
        as_actor(lab_admin)
    response = labs_client.request(method, path, json=body, headers={"Idempotency-Key": "private-key-sentinel"})
    assert response.status_code == 500
    assert response.headers["Cache-Control"] == "no-store"
    assert "sentinel" not in response.text + caplog.text
    assert "StatementError" in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_http_dependency_cleanup_failure_is_sanitized(monkeypatch, caplog):
    from uuid import uuid4
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import StatementError
    from app.core.auth import PrincipalContext, get_principal_context
    from app.db.session import get_session
    from app.main import app, settings
    from app.schemas import LabOverviewResponse, LabEligibility

    def session_with_failed_cleanup():
        yield None
        raise StatementError("cleanup-sentinel", "SQL sentinel", {"value": "patient-sentinel"}, RuntimeError("secret-sentinel"))

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_principal_context] = lambda: PrincipalContext(uuid4())
    app.dependency_overrides[get_session] = session_with_failed_cleanup
    monkeypatch.setattr("app.services.labs.read_labs", lambda *args: LabOverviewResponse(
        items=[], eligibility=LabEligibility(allowed=False, reason="profile_required"),
        server_today=date(2026, 9, 20), medical_rules_version=load_catalog().version, read_only=False,
    ))
    try:
        with TestClient(app) as client:
            response = client.get("/labs", headers={"Origin": settings.allowed_origins[0]})
        assert response.headers["Access-Control-Allow-Origin"] == settings.allowed_origins[0]
        assert "idempotent-replayed" in response.headers["Access-Control-Expose-Headers"].lower()
        assert response.status_code == 500
        assert response.headers["Cache-Control"] == "no-store"
        assert "sentinel" not in response.text + caplog.text
        assert "StatementError" in caplog.text
        assert all(record.exc_info is None for record in caplog.records)
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.mark.migration
def test_configured_engine_hides_lab_parameters_in_debug_logs(caplog):
    import logging
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from app.db.session import engine
    from labs_fixtures import safe_labs_database_url

    assert engine.url == make_url(safe_labs_database_url())
    engine_log = logging.getLogger("sqlalchemy.engine.Engine")
    original_echo = engine.echo
    original_handlers = engine_log.handlers[:]
    original_level, original_propagate = engine_log.level, engine_log.propagate
    try:
        engine.echo = True
        with engine.connect() as connection:
            value = connection.execute(text("SELECT CAST(:private_lab_value AS TEXT)"), {
                "private_lab_value": "private-medical-parameter-sentinel",
            }).scalar_one()
        assert value == "private-medical-parameter-sentinel"
        assert "private-medical-parameter-sentinel" not in caplog.text
        assert "SQL parameters hidden due to hide_parameters=True" in caplog.text
    finally:
        engine.echo = original_echo
        engine_log.handlers[:] = original_handlers
        engine_log.setLevel(original_level)
        engine_log.propagate = original_propagate


@pytest.mark.parametrize("dependency_scope,error_kind", [
    ("request", "http"), ("request", "domain"),
    ("function", "http"), ("function", "domain"),
])
def test_http_intentional_teardown_preserves_contract(dependency_scope, error_kind, caplog):
    from fastapi import Depends, FastAPI, HTTPException, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient
    from app.api.routes.labs import LabsRoute
    from app.services.labs_errors import LabValidationError, field_error

    isolated_app = FastAPI()
    isolated_app.router.route_class = LabsRoute
    isolated_app.add_middleware(CORSMiddleware, allow_origins=["https://labs.example.test"],
                               expose_headers=["Idempotent-Replayed"])

    def cleanup():
        yield
        if error_kind == "http":
            raise HTTPException(403, detail={"code": "FORBIDDEN"}, headers={
                "WWW-Authenticate": "Bearer", "X-Test": "retained", "cache-control": "public",
            })
        raise LabValidationError(403, [field_error("LAB_READ_ONLY")])

    @isolated_app.get("/labs")
    def endpoint(response: Response, _=Depends(cleanup, scope=dependency_scope)):
        response.headers["Idempotent-Replayed"] = "false"
        return {"ok": True}

    with TestClient(isolated_app) as client:
        response = client.get("/labs", headers={"Origin": "https://labs.example.test"})
    assert response.status_code == 403
    assert response.headers.get_list("Cache-Control") == ["no-store"]
    assert response.headers["Access-Control-Allow-Origin"] == "https://labs.example.test"
    assert response.headers["Access-Control-Expose-Headers"] == "Idempotent-Replayed"
    assert "Idempotent-Replayed" not in response.headers
    if error_kind == "http":
        assert response.json() == {"detail": {"code": "FORBIDDEN"}}
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.headers["X-Test"] == "retained"
    else:
        assert response.json() == {"detail": [field_error("LAB_READ_ONLY").model_dump()]}
    assert "Labs request failed" not in caplog.text


def test_http_unrelated_runtime_error_with_http_cause_remains_sanitized(caplog):
    from fastapi import Depends, FastAPI, HTTPException
    from fastapi.testclient import TestClient
    from app.api.routes.labs import LabsRoute

    isolated_app = FastAPI()
    isolated_app.router.route_class = LabsRoute

    def cleanup():
        yield
        raise RuntimeError("private-runtime-sentinel") from HTTPException(
            418, detail="private-http-sentinel", headers={"X-Private": "secret-sentinel"},
        )

    @isolated_app.get("/labs")
    def endpoint(_=Depends(cleanup)):
        return {"ok": True}

    with TestClient(isolated_app) as client:
        response = client.get("/labs")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert response.headers["Cache-Control"] == "no-store"
    assert "X-Private" not in response.headers
    assert "sentinel" not in response.text + caplog.text
    assert all(record.exc_info is None for record in caplog.records)


@pytest.mark.parametrize("dependency_scope", ["request", "function"])
@pytest.mark.parametrize("kind", ["cancel", "base"])
def test_http_teardown_cancellation_and_baseexceptions_propagate(dependency_scope, kind, caplog):
    import asyncio
    from fastapi import Depends, FastAPI
    from app.api.routes.labs import LabsRoute

    class StopSignal(BaseException):
        pass

    failure = asyncio.CancelledError() if kind == "cancel" else StopSignal()
    isolated_app = FastAPI()
    isolated_app.router.route_class = LabsRoute

    async def cleanup():
        yield
        raise failure

    @isolated_app.get("/labs")
    def endpoint(_=Depends(cleanup, scope=dependency_scope)):
        return {"ok": True}

    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "GET", "scheme": "http", "path": "/labs", "raw_path": b"/labs",
        "query_string": b"", "root_path": "", "headers": [],
        "client": ("127.0.0.1", 12345), "server": ("127.0.0.1", 80),
    }
    with pytest.raises(type(failure)) as caught:
        asyncio.run(isolated_app(scope, receive, send))
    assert caught.value is failure
    assert sent == []
    assert "Labs request failed" not in caplog.text
