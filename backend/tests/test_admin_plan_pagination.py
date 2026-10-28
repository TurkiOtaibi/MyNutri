from datetime import timedelta

import pytest
from sqlalchemy import event
from sqlmodel import select

from app.core.calendar import current_diary_date
from app.models import TargetPlan
from test_principal_security import profile_payload


def test_admin_history_traverses_more_than_100_stored_plans_without_writes(
    labs_client, labs_postgresql_session, lab_owner, lab_admin, as_actor,
):
    today = current_diary_date()
    payload = {**profile_payload(), "sex": "female", "effective_from": today.isoformat()}
    preview = labs_client.post("/profile/preview", json=payload)
    assert preview.status_code == 200
    saved = labs_client.post("/target-plans", headers={"Idempotency-Key": "history-seed"}, json={
        **payload, "confirmed": True, "expected_preview_hash": preview.json()["preview_hash"],
    })
    assert saved.status_code == 201
    first = labs_postgresql_session.exec(select(TargetPlan).where(TargetPlan.principal_id == lab_owner.id)).one()
    for revision in range(2, 106):
        labs_postgresql_session.add(TargetPlan(
            principal_id=first.principal_id, profile_id=first.profile_id,
            effective_from=first.effective_from, revision=revision,
            calculation_document=first.calculation_document,
            created_at=first.created_at + timedelta(seconds=revision),
        ))
    labs_postgresql_session.commit()
    stored = labs_postgresql_session.exec(select(TargetPlan).where(TargetPlan.principal_id == lab_owner.id).order_by(TargetPlan.revision.desc())).all()
    expected_ids = [str(plan.id) for plan in stored]
    expected_values = [plan.calculation_document["target_result"] for plan in stored]
    as_actor(lab_admin)
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement.strip().upper())

    engine = labs_postgresql_session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        collected = []
        cursor = None
        for page_index in range(6):
            params = {"plan_cursor": cursor} if cursor else {}
            response = labs_client.get(f"/admin/users/{lab_owner.id}", params=params)
            assert response.status_code == 200
            history = response.json()["plan_history"]
            assert len(history["items"]) == (20 if page_index < 5 else 5)
            collected.extend(history["items"])
            cursor = history["next_cursor"]
            assert bool(cursor) == (page_index < 5)
        assert [plan["id"] for plan in collected] == expected_ids
        assert [plan["revision"] for plan in collected] == list(range(105, 0, -1))
        for actual, original, values in zip(collected, stored, expected_values):
            assert actual["effective_from"] == today.isoformat()
            assert actual["created_at"] == original.created_at.isoformat().replace("+00:00", "Z")
            for field in ("calories", "protein_g", "carb_g", "fat_g"):
                assert actual["targets"][field] == values[field]
        bounded = labs_client.get(f"/admin/users/{lab_owner.id}?plan_limit=100").json()["plan_history"]
        assert len(bounded["items"]) == 100 and bounded["next_cursor"]
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert not any(sql.startswith(("INSERT", "UPDATE", "DELETE")) for sql in statements)


@pytest.mark.parametrize("query", ["plan_limit=0", "plan_limit=101", "plan_cursor=invalid"])
def test_admin_plan_history_rejects_invalid_pagination(labs_client, lab_owner, lab_admin, as_actor, query):
    as_actor(lab_admin)
    assert labs_client.get(f"/admin/users/{lab_owner.id}?{query}").status_code == 422


def test_admin_plan_pagination_is_not_available_to_normal_users(labs_client, other_lab_owner):
    assert labs_client.get(f"/admin/users/{other_lab_owner.id}?plan_limit=1").status_code == 403
