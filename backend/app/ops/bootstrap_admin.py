from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlmodel import Session, select

from app.core.config import validate_supabase_base_url
from app.db.session import engine
from app.models import Principal, PrincipalRole


@dataclass(frozen=True)
class BootstrapRequest:
    principal_id: UUID
    email: str
    display_name: str
    auth_user_id: UUID | None
    create_auth_user: bool
    dry_run: bool
    allow_loopback_auth_emulator: bool = False


def _create_supabase_user(request: BootstrapRequest) -> UUID:
    configured_url = os.environ.get("SUPABASE_URL", "")
    if (
        request.allow_loopback_auth_emulator
        and os.environ.get("ENVIRONMENT", "dev").strip().lower() == "production"
    ):
        raise RuntimeError(
            "The loopback auth emulator exception cannot be used in production."
        )
    try:
        url = validate_supabase_base_url(
            configured_url,
            allow_loopback_http=request.allow_loopback_auth_emulator,
        )
    except ValueError as error:
        raise RuntimeError("SUPABASE_URL is not safe for admin bootstrap.") from error

    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if not service_key or not password:
        raise RuntimeError(
            "SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and ADMIN_BOOTSTRAP_PASSWORD are required."
        )
    response = httpx.post(
        f"{url}/auth/v1/admin/users",
        headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        json={
            "email": request.email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": request.display_name},
        },
        timeout=30,
        follow_redirects=False,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Supabase Admin API rejected the request ({response.status_code}).")
    return UUID(response.json()["id"])


def bootstrap_admin(request: BootstrapRequest) -> UUID | None:
    with Session(engine) as session:
        principal = session.get(Principal, request.principal_id)
        if principal is None:
            raise RuntimeError("The requested existing Principal does not exist.")
        if principal.auth_user_id and request.auth_user_id not in {None, principal.auth_user_id}:
            raise RuntimeError("The Principal is already linked to a different Auth identity.")
        if request.auth_user_id:
            owner = session.exec(
                select(Principal).where(Principal.auth_user_id == request.auth_user_id)
            ).one_or_none()
            if owner and owner.id != principal.id:
                raise RuntimeError("The Auth identity is already linked to another Principal.")
        email_owner = session.exec(
            select(Principal).where(Principal.email == request.email.strip().lower())
        ).one_or_none()
        if email_owner and email_owner.id != principal.id:
            raise RuntimeError("The email is already linked to another Principal.")
        if request.dry_run:
            return request.auth_user_id or principal.auth_user_id

        auth_user_id = request.auth_user_id or principal.auth_user_id
        if auth_user_id is None:
            if not request.create_auth_user:
                raise RuntimeError("Provide --auth-user-id or explicitly use --create-auth-user.")
            auth_user_id = _create_supabase_user(request)
        principal.auth_user_id = auth_user_id
        principal.email = request.email.strip().lower()
        principal.display_name = " ".join(request.display_name.split())
        principal.role = PrincipalRole.admin
        session.add(principal)
        session.commit()
        return auth_user_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Link the existing Principal to one admin account.")
    parser.add_argument("--principal-id", type=UUID, required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--auth-user-id", type=UUID)
    parser.add_argument("--create-auth-user", action="store_true")
    parser.add_argument(
        "--allow-loopback-auth-emulator",
        action="store_true",
        help=(
            "Allow HTTP only for a literal localhost, 127.0.0.1, or ::1 auth "
            "emulator; prohibited in production."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    request = BootstrapRequest(**vars(args))
    bootstrap_admin(request)
    print("Admin bootstrap validation completed." if args.dry_run else "Admin account linked.")


if __name__ == "__main__":
    main()
