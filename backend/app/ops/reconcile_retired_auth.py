"""Idempotent full sweep of retired Supabase Auth identities."""

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine
from app.services.admin_auth import get_admin_auth_gateway
from app.services.admin_lifecycle import reconcile_all_retired


def main() -> None:
    gateway = get_admin_auth_gateway(get_settings())
    with Session(engine) as session:
        outcome = reconcile_all_retired(session, gateway)
    print(f"retired identity sweep: checked={outcome['checked']} failed={outcome['failed']}")
    if outcome["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
