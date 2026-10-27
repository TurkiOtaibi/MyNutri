"""Seed internal credentials only in an explicitly named disposable E2E database."""

import json
import os
import sys

from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from app.core.config import get_settings
from app.core.credentials import hash_password, normalize_username, verify_password
from app.db.session import engine
from app.models import Principal, PrincipalRole


def main() -> None:
    target = make_url(get_settings().database_url)
    expected = os.environ.get("PLAYWRIGHT_DISPOSABLE_DATABASE")
    if (
        target.get_backend_name() != "postgresql"
        or target.host not in {"127.0.0.1", "localhost"}
        or not expected
        or target.database != expected
        or not expected.startswith("mynutri_e2e_")
    ):
        raise ValueError("Internal E2E fixtures require the named disposable loopback database.")
    payload = json.load(sys.stdin)
    email, username, password = payload["email"], payload["username"], payload["password"]
    if not email.endswith("@example.test"):
        raise ValueError("Internal E2E fixtures require synthetic identities.")
    normalized = normalize_username(username)
    with Session(engine) as session:
        row = session.exec(select(Principal).where(Principal.email == email)).one_or_none()
        if row is None:
            row = Principal(
                email=email,
                display_name="مستخدم الاختبار",
                role=PrincipalRole.admin if email == "admin.e2e@example.test" else PrincipalRole.user,
            )
        if row.password_hash is not None:
            if row.normalized_username != normalized or not verify_password(password, row.password_hash):
                raise ValueError("Existing synthetic credentials differ; refusing to reset them.")
            return
        row.username = username
        row.normalized_username = normalized
        row.password_hash = hash_password(password)
        row.must_change_password = bool(payload.get("must_change_password", False))
        session.add(row)
        session.commit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Database driver exceptions and validation input may contain credentials.
        print("Internal E2E fixture setup failed; check disposable configuration and identity.", file=sys.stderr)
        raise SystemExit(1) from None
