"""Stage fresh CI databases through the same Admin prerequisite as a real cutover.

This helper is never used by deployment. Production requires an operator-owned
Admin and the release runbook; no migration condition is bypassed here.
"""

import argparse
from datetime import datetime, timezone
import secrets

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from app.core.config import get_settings
from app.db.session import engine
from app.models import Principal
from app.ops.internal_admin import manage_admin


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-admin", action="store_true")
    args = parser.parse_args()
    url = make_url(get_settings().database_url)
    if url.host not in {"localhost", "127.0.0.1", "::1"} or not (
        (url.database or "").startswith(("mynutri_test_", "mynutri_e2e_"))
    ):
        raise RuntimeError("Bootstrap requires an explicitly disposable loopback database.")
    if inspect(engine).get_table_names():
        raise RuntimeError("Bootstrap requires a fresh empty disposable database.")
    config = Config("alembic.ini")
    command.upgrade(config, "a1d9b7f23645")
    with Session(engine) as session:
        manage_admin(session, "create", "MigrationBootstrap", secrets.token_urlsafe(32),
                     datetime.now(timezone.utc))
        bootstrap = session.exec(select(Principal)).one()
        bootstrap_id = bootstrap.id
    command.upgrade(config, "head")
    if not args.keep_admin:
        with Session(engine) as session:
            # This exact synthetic actor has no private rows or Food attribution.
            bootstrap = session.get(Principal, bootstrap_id)
            session.delete(bootstrap)
            session.commit()
    print("Disposable database bootstrap completed.")


if __name__ == "__main__":
    main()
