"""Create, attach credentials to, or reset the sole Admin; no password arguments."""

import argparse
import getpass
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.credentials import hash_password, normalize_username
from app.db.session import engine
from app.models import Principal, PrincipalRole, PrincipalStatus
from app.services.internal_auth import revoke_sessions


def manage_admin(
    session: Session, action: str, username: str, password: str, now: datetime
) -> None:
    normalized = normalize_username(username)
    encoded = hash_password(password)
    row = session.exec(
        select(Principal)
        .where(Principal.role == PrincipalRole.admin)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    if action == "create":
        if row is not None:
            raise ValueError("An Admin already exists; refusing to create a second Admin.")
        row = Principal(
            username=username,
            normalized_username=normalized,
            password_hash=encoded,
            role=PrincipalRole.admin,
            must_change_password=True,
        )
    elif action == "attach":
        if row is None or row.status != PrincipalStatus.active:
            raise ValueError("The active Admin was not found.")
        if any(
            value is not None
            for value in (row.username, row.normalized_username, row.password_hash)
        ):
            raise ValueError("The Admin already has internal credentials; refusing to replace them.")
        row.username = username
        row.normalized_username = normalized
        row.password_hash = encoded
        row.must_change_password = False
    elif action == "reset":
        if (
            row is None
            or row.normalized_username != normalized
            or row.status != PrincipalStatus.active
        ):
            raise ValueError("The active internal Admin was not found.")
        row.password_hash = encoded
        row.must_change_password = False
        row.failed_login_count = 0
        row.locked_at = None
        row.sessions_valid_after = now.replace(microsecond=0) + timedelta(seconds=1)
        revoke_sessions(session, row.id, now)
    else:
        raise ValueError("Unknown Admin operation.")
    row.updated_at = now
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("Admin operation conflicts with an existing account.") from None


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # Do not echo an accidentally supplied password argument.
        self.exit(
            2, "Invalid arguments. Use --help; passwords must be prompted or read from stdin.\n"
        )


def main() -> None:
    parser = SafeArgumentParser(description="Create, attach, or reset the single internal Admin.")
    parser.add_argument("action", choices=("create", "attach", "reset"))
    parser.add_argument("--username", required=True)
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read one password line from stdin instead of an interactive hidden prompt.",
    )
    args = parser.parse_args()
    password = (
        sys.stdin.readline(258).rstrip("\r\n")
        if args.password_stdin
        else getpass.getpass("Password: ")
    )
    try:
        with Session(engine) as session:
            manage_admin(session, args.action, args.username, password, datetime.now(timezone.utc))
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    print("Admin operation completed.")


if __name__ == "__main__":
    main()
