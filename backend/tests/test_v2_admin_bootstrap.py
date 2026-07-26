from dataclasses import replace
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import (
    Settings,
    validate_runtime_configuration,
    validate_supabase_base_url,
)
from app.models import Principal, PrincipalRole
from app.ops import bootstrap_admin as module
from app.ops.bootstrap_admin import BootstrapRequest, bootstrap_admin

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
AUTH_ID = UUID("10000000-0000-0000-0000-000000000001")


@pytest.mark.parametrize(
    ("url", "allow_loopback_http", "expected"),
    [
        ("https://project.supabase.co/", False, "https://project.supabase.co"),
        ("https://project.supabase.co/base/", False, "https://project.supabase.co/base"),
        ("http://localhost:54321/", True, "http://localhost:54321"),
        ("http://127.0.0.1:54321/", True, "http://127.0.0.1:54321"),
        ("http://[::1]:54321/", True, "http://[::1]:54321"),
    ],
)
def test_plan007_endpoint_policy_accepts_https_and_explicit_loopback_emulator(
    url: str, allow_loopback_http: bool, expected: str
) -> None:
    assert (
        validate_supabase_base_url(
            url, allow_loopback_http=allow_loopback_http
        )
        == expected
    )


@pytest.mark.parametrize(
    "url",
    [
        "",
        "project.supabase.co",
        "https:///missing-host",
        "https://exa mple.com",
        "https://project.supabase.co\\@attacker.test",
        "https://project.supabase.co:99999",
        "https://user:password@project.supabase.co",
        "http://project.supabase.co",
        "http://localhost.example.com:54321",
        "http://127.0.0.1.example.com:54321",
        "http://[::2]:54321",
    ],
)
def test_plan007_endpoint_policy_rejects_malformed_credentials_and_insecure_hosts(
    url: str,
) -> None:
    with pytest.raises(ValueError):
        validate_supabase_base_url(url, allow_loopback_http=True)


def test_plan007_endpoint_policy_requires_explicit_loopback_emulator_opt_in() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        validate_supabase_base_url("http://localhost:54321")


def test_plan007_production_runtime_rejects_loopback_http() -> None:
    settings = Settings(
        environment="production",
        supabase_url="http://localhost:54321",
        supabase_jwks_url="https://project.supabase.co/auth/v1/.well-known/jwks.json",
    )
    with pytest.raises(RuntimeError, match="valid HTTPS URL"):
        validate_runtime_configuration(settings)


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


def configure_bootstrap_secrets(
    monkeypatch, *, url: str, environment: str = "dev"
) -> None:
    monkeypatch.setenv("SUPABASE_URL", url)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fixture-service-role-key")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_PASSWORD", "fixture-bootstrap-password")
    monkeypatch.setenv("ENVIRONMENT", environment)


@pytest.mark.parametrize(
    ("url", "allow_loopback", "environment"),
    [
        ("", False, "dev"),
        ("not-an-absolute-url", False, "dev"),
        ("https://exa mple.com", False, "dev"),
        ("https://project.supabase.co\\@attacker.test", False, "dev"),
        ("https://user:password@project.supabase.co", False, "dev"),
        ("http://project.supabase.co", True, "dev"),
        ("http://localhost.example.com:54321", True, "dev"),
        ("http://localhost:54321", False, "dev"),
        ("http://localhost:54321", True, "production"),
    ],
)
def test_plan007_rejected_endpoint_makes_zero_http_calls_and_hides_secrets(
    monkeypatch, url: str, allow_loopback: bool, environment: str
) -> None:
    configure_bootstrap_secrets(monkeypatch, url=url, environment=environment)
    calls = 0

    def unexpected_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("Rejected endpoints must not make HTTP requests.")

    monkeypatch.setattr(module.httpx, "post", unexpected_post)
    bootstrap_request = replace(
        request(dry_run=False),
        allow_loopback_auth_emulator=allow_loopback,
    )

    with pytest.raises(RuntimeError) as error:
        module._create_supabase_user(bootstrap_request)

    assert calls == 0
    assert "fixture-service-role-key" not in str(error.value)
    assert "fixture-bootstrap-password" not in str(error.value)


@pytest.mark.parametrize(
    ("url", "allow_loopback", "expected_endpoint"),
    [
        (
            "https://project.supabase.co/",
            False,
            "https://project.supabase.co/auth/v1/admin/users",
        ),
        (
            "http://127.0.0.1:54321/",
            True,
            "http://127.0.0.1:54321/auth/v1/admin/users",
        ),
    ],
)
def test_plan007_accepted_endpoint_disables_redirects(
    monkeypatch, url: str, allow_loopback: bool, expected_endpoint: str
) -> None:
    configure_bootstrap_secrets(monkeypatch, url=url)
    calls: list[tuple[tuple, dict]] = []

    class Response:
        status_code = 200

        @staticmethod
        def json() -> dict[str, str]:
            return {"id": str(AUTH_ID)}

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return Response()

    monkeypatch.setattr(module.httpx, "post", fake_post)
    bootstrap_request = replace(
        request(dry_run=False),
        allow_loopback_auth_emulator=allow_loopback,
    )

    assert module._create_supabase_user(bootstrap_request) == AUTH_ID
    assert len(calls) == 1
    assert calls[0][0] == (expected_endpoint,)
    assert calls[0][1]["follow_redirects"] is False
    assert calls[0][1]["timeout"] == 30


def test_plan007_redirect_response_fails_without_followup_request(monkeypatch) -> None:
    configure_bootstrap_secrets(monkeypatch, url="https://project.supabase.co")
    calls = 0

    class Response:
        status_code = 302

    def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        return Response()

    monkeypatch.setattr(module.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match=r"rejected the request \(302\)"):
        module._create_supabase_user(request(dry_run=False))

    assert calls == 1


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
