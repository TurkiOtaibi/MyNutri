"""Direct HTTP coverage of the selected-account status boundary (BR-USM-021)."""

import pytest
from sqlmodel import Session

from app.models import Principal, PrincipalStatus


PATHS = (
    "",
    "/diary",
    "/diary/summaries?dates=2026-10-17",
    "/labs",
    "/labs/tests/hba1c",
)


@pytest.mark.parametrize("suffix", PATHS)
@pytest.mark.parametrize("status", list(PrincipalStatus))
def test_admin_monitoring_all_paths_require_active_or_disabled_target(
    labs_client, labs_postgresql_session, labs_postgresql_database,
    lab_owner, lab_admin, as_actor, suffix, status,
):
    as_actor(lab_admin)
    # Prime the request Session identity map, then change state through another
    # connection: the boundary must inspect current database state, not cached state.
    cached = labs_postgresql_session.get(Principal, lab_owner.id)
    assert cached.status == PrincipalStatus.active
    with Session(labs_postgresql_database.engine) as writer:
        row = writer.get(Principal, lab_owner.id)
        row.status = status
        writer.add(row)
        writer.commit()
    response = labs_client.get(f"/admin/users/{lab_owner.id}{suffix}")
    if status in {PrincipalStatus.active, PrincipalStatus.disabled}:
        assert response.status_code == 200
        if not suffix:
            assert response.json()["account"]["status"] == status
            assert "current_target" in response.json() and "plan_history" in response.json()
    else:
        assert response.status_code == 404
        assert "RESOURCE_NOT_FOUND" in response.text
        assert str(lab_owner.id) not in response.text
        assert "profile" not in response.json() and "plan_history" not in response.json()
    if suffix.startswith("/labs"):
        assert response.headers["Cache-Control"] == "no-store"
    with Session(labs_postgresql_database.engine) as observer:
        assert observer.get(Principal, lab_owner.id).status == status
