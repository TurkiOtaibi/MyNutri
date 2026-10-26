"""BR-LAB-017: private batch notes and stable replay semantics."""

import pytest

from app.schemas import LabCreateRequest
from app.services.labs import canonical_request_hash
from app.services.labs_errors import LabValidationError, validate_labs_payload


def payload(**extra):
    return {"test_date": "2026-09-19", "results": [
        {"test_key": "hba1c", "entered_value": "5.270", "entered_unit": "%"},
    ], **extra}


@pytest.mark.parametrize("note,expected", [(None, None), (" \n ", None), ("  مختبر تجريبي  ", "مختبر تجريبي"), ("ن" * 500, "ن" * 500)])
def test_note_normalization(note, expected):
    assert LabCreateRequest.model_validate(payload(note=note)).note == expected


def test_note_limit_has_private_arabic_field_error():
    with pytest.raises(LabValidationError) as caught:
        validate_labs_payload(LabCreateRequest, payload(note="ن" * 501))
    error = caught.value.errors[0]
    assert error.loc == ["body", "note"]
    assert error.code == "LAB_NOTE_TOO_LONG"
    assert error.msg == "يجب ألا تتجاوز الملاحظة 500 حرف."
    assert "ن" * 501 not in str(error.model_dump())


def test_note_hash_preserves_legacy_and_normalizes_only_whitespace():
    from hashlib import sha256
    import json

    body = payload()
    legacy = {"operation": "lab_results.create.v1", "hash_schema": 1, **body}
    expected = sha256(json.dumps(legacy, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    def digest(**extra):
        return canonical_request_hash(LabCreateRequest.model_validate(payload(**extra)))
    assert digest() == digest(note=None) == digest(note="  ") == expected
    assert digest(note=" مختبر ") == digest(note="مختبر")
    assert digest(note="مختبر") != digest(note="آخر") != expected


def test_batch_note_persists_replays_and_survives_edit_and_sibling_delete(labs_client):
    body = payload(note="  مختبر تجريبي  ")
    body["results"].append({"test_key": "ferritin", "entered_value": "30", "entered_unit": "ng/mL"})
    response = labs_client.post("/labs/results", json=body, headers={"Idempotency-Key": "note-batch"})
    assert response.status_code == 201, response.text
    replay = labs_client.post("/labs/results", json=body, headers={"Idempotency-Key": "note-batch"})
    assert replay.json() == response.json()
    assert replay.headers["Idempotent-Replayed"] == "true"
    conflict = labs_client.post("/labs/results", json=body | {"note": "آخر"}, headers={"Idempotency-Key": "note-batch"})
    assert conflict.status_code == 409
    assert conflict.json()["detail"][0]["code"] == "LAB_IDEMPOTENCY_CONFLICT"
    rows = [labs_client.get(f"/labs/tests/{key}").json()["results"][0] for key in ("hba1c", "ferritin")]
    assert all(row["note"] == "مختبر تجريبي" for row in rows)
    first = rows[0]
    edit = labs_client.patch(f"/labs/results/{first['id']}", json={
        "test_date": first["test_date"], "entered_value": "5.1", "entered_unit": "%",
        "expected_updated_at": first["updated_at"],
    })
    assert edit.status_code == 200 and edit.json()["note"] == "مختبر تجريبي"
    assert labs_client.delete(f"/labs/results/{first['id']}").status_code == 204
    assert labs_client.get("/labs/tests/ferritin").json()["results"][0]["note"] == "مختبر تجريبي"
    restored = labs_client.post("/labs/results", json=payload(note=first["note"]), headers={"Idempotency-Key": "undo-note"})
    assert restored.status_code == 201
    assert restored.json()["result_ids"][0] != first["id"]
    assert labs_client.get("/labs/tests/hba1c").json()["results"][0]["note"] == first["note"]


def test_note_owner_scope_and_admin_read_only(labs_client, lab_owner, other_lab_owner, lab_admin, as_actor):
    created = labs_client.post("/labs/results", json=payload(note="ملاحظة خاصة"), headers={"Idempotency-Key": "private-note"})
    assert created.status_code == 201
    result_id = created.json()["result_ids"][0]
    as_actor(other_lab_owner)
    assert labs_client.get("/labs/tests/hba1c").json()["results"] == []
    assert labs_client.delete(f"/labs/results/{result_id}").status_code == 404
    as_actor(lab_admin)
    selected = labs_client.get(f"/admin/users/{lab_owner.id}/labs/tests/hba1c")
    assert selected.status_code == 200
    assert selected.headers["Cache-Control"] == "no-store"
    assert selected.json()["read_only"] is True
    row = selected.json()["results"][0]
    assert row["note"] == "ملاحظة خاصة"
    assert labs_client.post("/labs/results", json=payload(note="تغيير"), headers={"Idempotency-Key": "admin-note"}).status_code == 403
    assert labs_client.patch(f"/labs/results/{result_id}", json={"test_date": row["test_date"], "entered_value": "6", "entered_unit": "%", "expected_updated_at": row["updated_at"]}).status_code == 403
    assert labs_client.delete(f"/labs/results/{result_id}").status_code == 403


@pytest.mark.migration
def test_note_migration_roundtrip_and_populated_downgrade_guard(labs_postgresql_database, labs_postgresql_session, lab_result):
    from sqlalchemy import inspect, text
    from labs_fixtures import run_labs_alembic

    result_id = lab_result.id
    labs_postgresql_session.close()
    run_labs_alembic("downgrade", "c7f5d3b89201")
    assert "note" not in {c["name"] for c in inspect(labs_postgresql_database.engine).get_columns("lab_result")}
    run_labs_alembic("upgrade", "head")
    with labs_postgresql_database.engine.begin() as connection:
        assert connection.execute(text("SELECT note FROM lab_result WHERE id=:id"), {"id": result_id}).scalar_one() is None
        connection.execute(text("UPDATE lab_result SET note='synthetic note' WHERE id=:id"), {"id": result_id})
    blocked = run_labs_alembic("downgrade", "c7f5d3b89201", check=False)
    assert blocked.returncode != 0
    assert "LAB_NOTE_DOWNGRADE_BLOCKED" in blocked.stdout + blocked.stderr
    with labs_postgresql_database.engine.connect() as connection:
        assert connection.execute(text("SELECT note FROM lab_result WHERE id=:id"), {"id": result_id}).scalar_one() == "synthetic note"
    sql = run_labs_alembic("upgrade", "c7f5d3b89201:head", "--sql").stdout
    assert "ADD COLUMN note VARCHAR(500)" in sql
    sql = run_labs_alembic("downgrade", "d8a6e4c90312:c7f5d3b89201", "--sql").stdout
    assert "LAB_NOTE_DOWNGRADE_BLOCKED" in sql and "DROP COLUMN note" in sql
