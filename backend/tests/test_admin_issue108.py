from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text

from app.models import Principal, PrincipalStatus
from app.services.admin_lifecycle import set_account_enabled


def test_disable_time_is_nullable_and_timezone_aware():
    column = Principal.__table__.c.disabled_at
    assert column.nullable and column.type.timezone
    assert Principal().disabled_at is None


@pytest.mark.parametrize("path", [
    "/admin/accounts", "/admin/users/{id}", "/admin/users/{id}/diary",
    "/admin/users/{id}/diary/summaries?dates=2026-10-17",
    "/admin/users/{id}/labs", "/admin/users/{id}/labs/tests/hba1c",
])
def test_admin_reads_reject_normal_users(labs_client, other_lab_owner, path):
    assert labs_client.get(path.format(id=other_lab_owner.id)).status_code == 403


def test_disable_time_tracks_transition_not_repeated_requests(labs_postgresql_session, lab_admin, lab_owner):
    session = labs_postgresql_session
    now = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    row = set_account_enabled(session, lab_admin.id, lab_owner.id, False, now)
    assert row.disabled_at == now
    row = set_account_enabled(session, lab_admin.id, lab_owner.id, False, now + timedelta(hours=1))
    assert row.disabled_at == now
    row = set_account_enabled(session, lab_admin.id, lab_owner.id, True, now + timedelta(hours=2))
    assert row.disabled_at is None
    row = set_account_enabled(session, lab_admin.id, lab_owner.id, False, now + timedelta(hours=3))
    assert row.disabled_at == now + timedelta(hours=3)


def test_account_counts_ignore_filters_and_exclude_admin_and_deleted(labs_client, labs_postgresql_session, lab_admin, as_actor, monkeypatch):
    as_actor(lab_admin)
    for status in (PrincipalStatus.disabled, PrincipalStatus.provisioning, PrincipalStatus.deleting, PrincipalStatus.deleted):
        labs_postgresql_session.add(Principal(status=status, email=f"{uuid4()}@example.test"))
    labs_postgresql_session.commit()
    response = labs_client.get("/admin/accounts?search=not-a-match")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["total"] == 0
    assert response.json()["counts"] == {"active": 1, "disabled": 1, "provisioning": 1, "deleting": 1}


def test_admin_profile_age_uses_server_riyadh_date(labs_client, lab_owner, lab_admin, as_actor, monkeypatch):
    as_actor(lab_admin)
    monkeypatch.setattr("app.api.routes.admin.current_diary_date", lambda: date(2026, 10, 26))
    response = labs_client.get(f"/admin/users/{lab_owner.id}")
    assert response.status_code == 200
    assert response.json()["age"] == 36
    assert response.json()["profile"]["sex"] == "female"


@pytest.mark.migration
def test_disabled_time_migration_roundtrip(labs_postgresql_database, labs_postgresql_session, lab_owner):
    from labs_fixtures import run_labs_alembic

    owner_id = lab_owner.id
    labs_postgresql_session.close()
    run_labs_alembic("downgrade", "d8a6e4c90312")
    with labs_postgresql_database.engine.begin() as connection:
        connection.execute(text("UPDATE principal SET status='disabled' WHERE id=:id"), {"id": owner_id})
    run_labs_alembic("upgrade", "head")
    with labs_postgresql_database.engine.connect() as connection:
        assert connection.execute(text("SELECT disabled_at FROM principal WHERE id=:id"), {"id": owner_id}).scalar_one() is None
    assert "disabled_at" in {c["name"] for c in inspect(labs_postgresql_database.engine).get_columns("principal")}
    sql = run_labs_alembic("upgrade", "d8a6e4c90312:head", "--sql").stdout
    assert "ADD COLUMN disabled_at TIMESTAMP WITH TIME ZONE" in sql
    run_labs_alembic("downgrade", "d8a6e4c90312")
    assert "disabled_at" not in {c["name"] for c in inspect(labs_postgresql_database.engine).get_columns("principal")}
    run_labs_alembic("upgrade", "head")


def test_normal_user_cannot_change_disable_time(labs_client, other_lab_owner):
    response = labs_client.put(f"/admin/accounts/{other_lab_owner.id}/status", json={"enabled": False})
    assert response.status_code == 403


def test_admin_diary_units_and_full_day_totals_are_owner_scoped(labs_client, labs_postgresql_session, lab_owner, other_lab_owner, lab_admin, as_actor):
    from test_admin_monitoring_performance import _seed_diary
    from app.services.aggregation import weekly_summary
    from app.services.profile import to_target_response
    from app.models import TargetPlan

    rows = _seed_diary(labs_postgresql_session, lab_owner.id, 4)
    _seed_diary(labs_postgresql_session, other_lab_owner.id, 6)
    as_actor(lab_admin)
    page = labs_client.get(f"/admin/users/{lab_owner.id}/diary?limit=1")
    assert page.status_code == 200
    assert len(page.json()["items"]) == 1 and page.json()["next_cursor"]
    item = page.json()["items"][0]
    assert item["recorded_unit_type"] == "serving"
    assert item["recorded_unit_amount"] == 100
    assert item["recorded_unit_basis"] == "g"
    assert item["recorded_unit_label"] is None
    day = rows[0].entry_date
    stored = to_target_response(lab_owner.profile, calculation_date=day).model_dump(mode="json")
    for effective, calories in [(day - timedelta(days=1), 1800), (day, 2000)]:
        labs_postgresql_session.add(TargetPlan(
            principal_id=lab_owner.id, profile_id=lab_owner.profile.id,
            effective_from=effective, revision=1,
            calculation_document={"target_result": stored | {"calories": calories}},
        ))
    labs_postgresql_session.commit()
    response = labs_client.get(f"/admin/users/{lab_owner.id}/diary/summaries?dates={day}&dates={day}")
    assert response.status_code == 200
    assert len(response.json()) == 1
    expected = next(item for item in weekly_summary(labs_postgresql_session, lab_owner.context, day).days if item.date == day).model_dump(mode="json")
    assert response.json()[0] == expected
    assert response.json()[0]["totals"]["calories"] == 300
    assert response.json()[0]["targets"]["calories"] == 2000
    previous = labs_client.get(f"/admin/users/{lab_owner.id}/diary/summaries?dates={day - timedelta(days=1)}")
    assert previous.json()[0]["targets"]["calories"] == 1800
    filtered = labs_client.get(f"/admin/users/{lab_owner.id}/diary?entry_date={rows[-1].entry_date}")
    assert len(filtered.json()["items"]) == 1
    assert filtered.json()["items"][0]["entry_date"] == rows[-1].entry_date.isoformat()


@pytest.mark.parametrize("query", ["", "dates=invalid", "&".join(["dates=2026-10-17"] * 101)])
def test_admin_day_summaries_validate_dates(labs_client, lab_owner, lab_admin, as_actor, query):
    as_actor(lab_admin)
    assert labs_client.get(f"/admin/users/{lab_owner.id}/diary/summaries?{query}").status_code == 422
