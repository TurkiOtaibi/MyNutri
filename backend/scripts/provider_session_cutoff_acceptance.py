"""Exercise Admin reset against disposable loopback Supabase Auth and FastAPI."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import httpx
import jwt
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlmodel import Session

from app.core.auth import AuthClaims, get_token_verifier, latest_authentication_time
from app.core.config import get_settings, validate_supabase_base_url
from app.db.session import engine
from app.main import app
from app.models import Principal, PrincipalRole
from app.services.admin_auth import SupabaseAdminClient


def main() -> None:
    if os.environ.get("PROVIDER_ACCEPTANCE_DISPOSABLE") != "mynutri-plan020-provider-ci":
        raise RuntimeError("Provider acceptance requires the named disposable CI stack.")
    settings = get_settings()
    provider_url = validate_supabase_base_url(settings.supabase_url, allow_loopback_http=True)
    if not provider_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise RuntimeError("Provider acceptance requires loopback Auth.")
    if make_url(settings.database_url).host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Provider acceptance requires disposable loopback Postgres.")
    public_key = os.environ["PROVIDER_ACCEPTANCE_PUBLIC_KEY"]
    service_key = settings.supabase_service_role_key
    if service_key is None:
        raise RuntimeError("Provider acceptance requires a local Admin credential.")
    gateway = SupabaseAdminClient(
        base_url=provider_url,
        service_key=service_key.get_secret_value(),
        timeout_seconds=settings.supabase_admin_http_timeout_seconds,
        allow_loopback_http=True,
    )
    admin_id, user_id = uuid4(), uuid4()
    admin_email, user_email = f"cutoff-admin-{admin_id}@example.test", f"cutoff-user-{user_id}@example.test"
    admin_password, user_password, new_password = (
        f"Admin-{uuid4()}!Aa1", f"User-{uuid4()}!Aa1", f"New-{uuid4()}!Aa1"
    )
    created_ids = []
    principal_ids = []
    try:
        gateway.create_user(admin_id, admin_email, admin_password)
        created_ids.append(admin_id)
        gateway.create_user(user_id, user_email, user_password)
        created_ids.append(user_id)
        with Session(engine) as session:
            admin = Principal(auth_user_id=admin_id, email=admin_email, display_name="Local Admin", role=PrincipalRole.admin)
            user = Principal(auth_user_id=user_id, email=user_email, display_name="Local User")
            session.add_all([admin, user])
            session.commit()
            principal_ids.extend([admin.id, user.id])
            target_id = user.id

        def sign_in(email: str, password: str) -> dict:
            response = httpx.post(
                f"{provider_url}/auth/v1/token?grant_type=password",
                headers={"apikey": public_key},
                json={"email": email, "password": password}, timeout=10,
            )
            assert response.status_code == 200, "Local provider sign-in failed."
            return response.json()

        admin_session = sign_in(admin_email, admin_password)
        user_session = sign_in(user_email, user_password)
        user_claims = jwt.decode(user_session["access_token"], options={"verify_signature": False})
        assert latest_authentication_time(user_claims.get("amr")) is not None, "Local provider omitted authentication time."

        # The isolated CLI may sign with its legacy HS256 key; production
        # verification remains asymmetric. Verify the local signature here.
        if jwt.get_unverified_header(user_session["access_token"])["alg"] == "HS256":
            signing_secret = os.environ["PROVIDER_ACCEPTANCE_JWT_SECRET"]

            class LocalProviderVerifier:
                def verify(self, token: str) -> AuthClaims:
                    claims = jwt.decode(
                        token, signing_secret, algorithms=["HS256"],
                        audience=settings.supabase_jwt_audience,
                        issuer=settings.expected_supabase_issuer,
                        options={"require": ["exp", "iss", "aud", "sub", "iat"]},
                    )
                    return AuthClaims(
                        UUID(claims["sub"]), claims.get("email"), None,
                        latest_authentication_time(claims.get("amr")),
                    )

            app.dependency_overrides[get_token_verifier] = LocalProviderVerifier
        try:
            with TestClient(app) as client:
                def admission(token: str) -> int:
                    return client.get("/account/me", headers={"Authorization": f"Bearer {token}"}).status_code

                assert admission(user_session["access_token"]) == 200
                reset = client.put(
                    f"/admin/accounts/{target_id}/password",
                    json={"new_password": new_password},
                    headers={"Authorization": f"Bearer {admin_session['access_token']}"},
                )
                assert reset.status_code == 204, "Admin password reset failed."
                refreshed = httpx.post(
                    f"{provider_url}/auth/v1/token?grant_type=refresh_token",
                    headers={"apikey": public_key},
                    json={"refresh_token": user_session["refresh_token"]}, timeout=10,
                )
                if refreshed.status_code == 200:
                    assert admission(refreshed.json()["access_token"]) == 401
                else:
                    assert 400 <= refreshed.status_code < 500, "Unexpected provider refresh failure."
                assert admission(user_session["access_token"]) == 401
        finally:
            app.dependency_overrides.pop(get_token_verifier, None)
    finally:
        cleanup_failed = False
        for auth_id in reversed(created_ids):
            try:
                gateway.delete_user(auth_id)
            except Exception:
                cleanup_failed = True
        try:
            with Session(engine) as session:
                for principal_id in principal_ids:
                    row = session.get(Principal, principal_id)
                    if row is not None:
                        session.delete(row)
                session.commit()
        except Exception:
            cleanup_failed = True
        if cleanup_failed:
            raise RuntimeError("Provider acceptance cleanup could not be certified.")


if __name__ == "__main__":
    main()
