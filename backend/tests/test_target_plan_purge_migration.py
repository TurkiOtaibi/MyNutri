"""The account-purge exception must not weaken immutable plan revisions."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models import TargetPlan
from labs_fixtures import run_labs_alembic


PARENT = "f0c8a6e12534"
REVISION = "a1d9b7f23645"


def _plan(session, owner):
    row = TargetPlan(
        principal_id=owner.id,
        profile_id=owner.profile.id,
        effective_from=date(2026, 10, 28),
        revision=1,
        calculation_document={"target_result": {"calories": 1800}},
    )
    session.add(row)
    session.commit()
    return row.id


@pytest.mark.parametrize("status", ["active", "disabled", "provisioning", "deleting", "deleted"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_plan_purge_exception_is_delete_only_for_deleting_owner(
    labs_postgresql_database, labs_postgresql_session, lab_owner, status, operation,
):
    plan_id = _plan(labs_postgresql_session, lab_owner)
    with labs_postgresql_database.engine.begin() as connection:
        connection.execute(text("UPDATE principal SET status=:status WHERE id=:id"),
                           {"status": status, "id": lab_owner.id})
    statement = (
        "UPDATE target_plan SET revision=2 WHERE id=:id"
        if operation == "UPDATE" else "DELETE FROM target_plan WHERE id=:id"
    )
    if operation == "DELETE" and status == "deleting":
        with labs_postgresql_database.engine.begin() as connection:
            assert connection.execute(text(statement), {"id": plan_id}).rowcount == 1
    else:
        with pytest.raises(IntegrityError, match="Target Plan revisions are immutable"):
            with labs_postgresql_database.engine.begin() as connection:
                connection.execute(text(statement), {"id": plan_id})
        with labs_postgresql_database.engine.connect() as connection:
            assert connection.scalar(text("SELECT revision FROM target_plan WHERE id=:id"),
                                     {"id": plan_id}) == 1


@pytest.mark.migration
def test_plan_purge_migration_roundtrip_preserves_rows_and_restores_guard(
    labs_postgresql_database, labs_postgresql_session, lab_owner,
):
    plan_id = _plan(labs_postgresql_session, lab_owner)
    labs_postgresql_session.close()
    run_labs_alembic("downgrade", PARENT)
    with labs_postgresql_database.engine.begin() as connection:
        connection.execute(text("UPDATE principal SET status='deleting' WHERE id=:id"),
                           {"id": lab_owner.id})
    with pytest.raises(IntegrityError, match="Target Plan revisions are immutable"):
        with labs_postgresql_database.engine.begin() as connection:
            connection.execute(text("DELETE FROM target_plan WHERE id=:id"), {"id": plan_id})
    run_labs_alembic("upgrade", REVISION)
    with labs_postgresql_database.engine.begin() as connection:
        assert connection.scalar(text("SELECT revision FROM target_plan WHERE id=:id"),
                                 {"id": plan_id}) == 1
        assert connection.execute(text("DELETE FROM target_plan WHERE id=:id"),
                                  {"id": plan_id}).rowcount == 1
    assert "No new upgrade operations detected" in run_labs_alembic("check").stdout


@pytest.mark.migration
def test_plan_purge_migration_offline_sql(labs_postgresql_database):
    upgrade = run_labs_alembic("upgrade", f"{PARENT}:{REVISION}", "--sql").stdout
    assert "TG_OP = 'DELETE'" in upgrade
    assert "status = 'deleting'" in upgrade
    assert "RAISE EXCEPTION 'Target Plan revisions are immutable'" in upgrade
    downgrade = run_labs_alembic("downgrade", f"{REVISION}:{PARENT}", "--sql").stdout
    assert "RAISE EXCEPTION 'Target Plan revisions are immutable'" in downgrade
    assert "status = 'deleting'" not in downgrade
