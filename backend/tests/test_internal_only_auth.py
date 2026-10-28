"""Issue #113 removal boundary: no provider admission or configuration required."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import Settings, validate_runtime_configuration
from app.db.preflight import verify_database_compatibility
from app.db.session import get_session
from app.main import app
from app.models import Principal, PrincipalRole


@pytest.mark.migration
@pytest.mark.parametrize("with_internal_credentials", [False, True])
def test_jwt_is_rejected_for_legacy_and_internal_accounts(
    labs_postgresql_database, monkeypatch, with_internal_credentials
):
    from app.core.credentials import hash_password
    from datetime import datetime, timezone
    import base64
    import hashlib
    import hmac
    import json

    identity = uuid4()
    with Session(labs_postgresql_database.engine) as session:
        row = Principal(auth_user_id=identity, email="synthetic@example.test")
        if with_internal_credentials:
            row.username = row.normalized_username = "internal"
            row.password_hash = hash_password("synthetic-password")
        session.add(row)
        session.commit()

    def encoded(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=")

    now = int(datetime.now(timezone.utc).timestamp())
    signed = encoded({"alg": "HS256", "typ": "JWT"}) + b"." + encoded({
        "sub": str(identity), "iat": now, "exp": now + 600,
        "aud": "authenticated", "amr": [{"method": "password", "timestamp": now}],
    })
    token = (signed + b"." + base64.urlsafe_b64encode(
        hmac.new(b"synthetic-test-key", signed, hashlib.sha256).digest()
    ).rstrip(b"=")).decode()

    def no_network(*args, **kwargs):
        raise AssertionError("Admission must not fetch provider keys or make network requests")

    monkeypatch.setattr("httpx.HTTPTransport.handle_request", no_network)

    def sessions():
        with Session(labs_postgresql_database.engine) as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    try:
        with TestClient(app) as client:
            response = client.get("/account/me", headers={"Authorization": "Bearer " + token})
            assert response.status_code == 401
            assert response.json()["detail"]["code"] == "INVALID_CREDENTIAL"
            assert response.headers["cache-control"] == "no-store"
            assert token not in response.text
    finally:
        app.dependency_overrides.clear()


@pytest.mark.migration
def test_production_preflight_rejects_legacy_only_admin(labs_postgresql_database):
    with Session(labs_postgresql_database.engine) as session:
        session.add(Principal(auth_user_id=uuid4(), role=PrincipalRole.admin))
        session.commit()
    with pytest.raises(RuntimeError, match="No active authenticated admin"):
        verify_database_compatibility(
            labs_postgresql_database.engine,
            Settings(environment="production", database_url=labs_postgresql_database.url),
        )


def test_runtime_configuration_requires_no_external_auth_settings():
    validate_runtime_configuration(Settings(environment="production"))
    assert not any("jwks" in field or "jwt" in field for field in Settings.model_fields)
