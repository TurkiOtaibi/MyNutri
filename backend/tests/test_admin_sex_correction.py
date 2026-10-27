"""BR-USM-032/034/061: the sole selected-user Profile write."""

from datetime import date

import pytest
from sqlmodel import select

from app.models import DiaryEntry, LabResult, Principal, PrincipalStatus, Profile, TargetPlan
from app.services.profile import to_target_response


def endpoint(owner):
    return f"/admin/accounts/{owner.id}/profile/sex"


def snapshot(session, model):
    session.expire_all()
    return {str(row.id): row.model_dump(mode="json") for row in session.exec(select(model)).all()}


def test_normal_user_cannot_correct_sex(labs_client, other_lab_owner):
    assert labs_client.put(endpoint(other_lab_owner), json={"sex": "male"}).status_code == 403


def test_admin_cannot_correct_self(labs_client, lab_admin, as_actor):
    as_actor(lab_admin)
    assert labs_client.put(endpoint(lab_admin), json={"sex": "male"}).status_code == 403


@pytest.mark.parametrize("status", ["provisioning", "deleting", "deleted"])
def test_incomplete_accounts_cannot_be_corrected(labs_client, labs_postgresql_session, lab_owner, lab_admin, as_actor, status):
    row = labs_postgresql_session.get(Principal, lab_owner.id)
    row.status = PrincipalStatus(status)
    labs_postgresql_session.commit()
    as_actor(lab_admin)
    assert labs_client.put(endpoint(lab_owner), json={"sex": "male"}).status_code == 409


def test_missing_profile_has_clear_error_and_list_flag(labs_client, labs_postgresql_session, lab_admin, as_actor, monkeypatch):
    monkeypatch.setattr("app.api.routes.admin_accounts._background_reconcile_recent", lambda *args: None)
    owner = Principal(email="no-profile@example.test")
    labs_postgresql_session.add(owner)
    labs_postgresql_session.commit()
    as_actor(lab_admin)
    result = labs_client.put(endpoint(owner), json={"sex": "male"})
    assert result.status_code == 409
    assert result.json()["error"] == {"code": "PROFILE_REQUIRED", "message_ar": "لا يمكن تصحيح الجنس قبل حفظ الملف الشخصي للمستخدم."}
    listed = labs_client.get("/admin/accounts").json()["items"]
    assert next(row for row in listed if row["principal_id"] == str(owner.id))["profile_complete"] is False


@pytest.mark.parametrize("status", ["active", "disabled"])
def test_correction_changes_only_sex_and_preserves_owner_lock(labs_client, labs_postgresql_session, lab_owner, other_lab_owner, lab_admin, as_actor, lab_result, status):
    from test_admin_monitoring_performance import _seed_diary

    session = labs_postgresql_session
    _seed_diary(session, lab_owner.id, 2)
    stored = to_target_response(lab_owner.profile, calculation_date=date(2026, 8, 1)).model_dump(mode="json")
    session.add(TargetPlan(principal_id=lab_owner.id, profile_id=lab_owner.profile.id,
                           effective_from=date(2026, 8, 1), revision=1,
                           calculation_document={"target_result": stored}))
    session.get(Principal, lab_owner.id).status = PrincipalStatus(status)
    session.commit()
    models = (Principal, Profile, TargetPlan, DiaryEntry, LabResult)
    before = {model: snapshot(session, model) for model in models}
    as_actor(lab_admin)
    response = labs_client.put(endpoint(lab_owner), json={"sex": "male"})
    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store"
    before[Profile][str(lab_owner.profile.id)]["sex"] = "male"
    assert {model: snapshot(session, model) for model in models} == before
    # A stale owner preview cannot silently restore the old sex.
    as_actor(lab_owner)
    payload = {"sex": "female", "birth_date": "1990-01-01", "height_cm": 165,
               "weight_kg": 65, "activity_level": "light", "goal": "maintain",
               "protein_per_kg": 1.2, "fat_pct": 0.25, "selected_cut_intensity": 0.2,
               "effective_from": "2026-09-20"}
    rejected = labs_client.post("/profile/preview", json=payload)
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "PROFILE_SEX_IMMUTABLE"
    write = labs_client.post("/target-plans", json=payload | {
        "confirmed": True, "expected_preview_hash": "0" * 64,
    }, headers={"Idempotency-Key": "stale-owner-after-correction"})
    # Disabled owners remain barred independently of their submitted sex.
    assert write.status_code == (401 if status == "disabled" else 422)
    if status == "active":
        assert write.json()["error"]["code"] == "PROFILE_SEX_IMMUTABLE"


@pytest.mark.parametrize("payload", [{"sex": "other"}, {"sex": "male", "weight_kg": 100}])
def test_correction_rejects_invalid_or_extra_fields(labs_client, lab_owner, lab_admin, as_actor, payload):
    as_actor(lab_admin)
    assert labs_client.put(endpoint(lab_owner), json=payload).status_code == 422


def test_fresh_labs_reads_use_corrected_sex_without_rewriting_result(labs_client, labs_postgresql_session, lab_owner, lab_admin, as_actor, lab_result):
    lab_result.test_key = "hemoglobin"
    lab_result.entered_value = 12
    lab_result.entered_unit = "g/dL"
    labs_postgresql_session.commit()
    before = labs_client.get("/labs/tests/hemoglobin").json()
    as_actor(lab_admin)
    assert labs_client.put(endpoint(lab_owner), json={"sex": "male"}).status_code == 204
    after = labs_client.get(f"/admin/users/{lab_owner.id}/labs/tests/hemoglobin").json()
    assert before["reference_zones"] != after["reference_zones"]


def test_correction_serializes_with_concurrent_owner_edit(labs_postgresql_database, labs_postgresql_session, lab_owner, lab_admin):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from sqlalchemy import event
    from sqlmodel import Session
    from app.models import Sex
    from app.services.admin_profile import correct_profile_sex

    engine = labs_postgresql_database.engine
    owner_id, admin_id = lab_owner.id, lab_admin.id
    labs_postgresql_session.rollback()
    attempting_lock = Event()
    with Session(engine) as owner:
        owner.exec(select(Principal).where(Principal.id == owner_id).with_for_update()).one()
        profile = owner.exec(select(Profile).where(Profile.principal_id == owner_id).with_for_update()).one()
        profile.weight_kg = 70

        def correct():
            with Session(engine) as admin:
                connection = admin.connection()

                def before_execute(_conn, _cursor, statement, parameters, _context, _many):
                    if "FOR UPDATE" in statement and owner_id in parameters.values():
                        attempting_lock.set()

                event.listen(connection, "before_cursor_execute", before_execute)
                correct_profile_sex(admin, admin_id, owner_id, Sex.male)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(correct)
            try:
                assert attempting_lock.wait(5), "Correction must acquire the target Principal lock"
            finally:
                owner.commit()
            future.result(timeout=5)
    labs_postgresql_session.expire_all()
    actual = labs_postgresql_session.get(Profile, lab_owner.profile.id)
    assert actual.sex == Sex.male
    assert actual.weight_kg == 70
