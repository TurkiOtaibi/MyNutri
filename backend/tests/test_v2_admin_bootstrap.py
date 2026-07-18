from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models import Principal, PrincipalRole
from app.ops import bootstrap_admin as module
from app.ops.bootstrap_admin import BootstrapRequest, bootstrap_admin

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
AUTH_ID = UUID("10000000-0000-0000-0000-000000000001")


@pytest.fixture
def bootstrap_engine(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()
    monkeypatch.setattr(module, "engine", engine)
    return engine


def request(*, dry_run: bool) -> BootstrapRequest:
    return BootstrapRequest(
        principal_id=PRINCIPAL_ID,
        email="admin@example.test",
        display_name="Admin",
        auth_user_id=AUTH_ID,
        create_auth_user=False,
        dry_run=dry_run,
    )


def test_admin_bootstrap_dry_run_does_not_mutate(bootstrap_engine) -> None:
    assert bootstrap_admin(request(dry_run=True)) == AUTH_ID
    with Session(bootstrap_engine) as session:
        principal = session.get(Principal, PRINCIPAL_ID)
        assert principal is not None
        assert principal.auth_user_id is None
        assert principal.role == PrincipalRole.user


def test_admin_bootstrap_links_existing_principal_without_changing_id(bootstrap_engine) -> None:
    assert bootstrap_admin(request(dry_run=False)) == AUTH_ID
    with Session(bootstrap_engine) as session:
        principal = session.get(Principal, PRINCIPAL_ID)
        assert principal is not None
        assert principal.id == PRINCIPAL_ID
        assert principal.auth_user_id == AUTH_ID
        assert principal.role == PrincipalRole.admin


def test_admin_bootstrap_refuses_ambiguous_identity(bootstrap_engine) -> None:
    with Session(bootstrap_engine) as session:
        session.add(Principal(auth_user_id=AUTH_ID, email="other@example.test"))
        session.commit()
    with pytest.raises(RuntimeError, match="another Principal"):
        bootstrap_admin(request(dry_run=False))


def test_admin_bootstrap_refuses_email_owned_by_another_principal(bootstrap_engine) -> None:
    with Session(bootstrap_engine) as session:
        session.add(Principal(email="admin@example.test"))
        session.commit()
    with pytest.raises(RuntimeError, match="email is already linked"):
        bootstrap_admin(request(dry_run=True))


def test_admin_bootstrap_source_never_embeds_or_prints_secret_values() -> None:
    source = Path(module.__file__).read_text("utf-8")
    assert "response.text" not in source
    assert "ADMIN_BOOTSTRAP_PASSWORD" in source
    assert "SUPABASE_SERVICE_ROLE_KEY" in source
