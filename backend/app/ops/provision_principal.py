from __future__ import annotations

import argparse
from uuid import UUID

from sqlalchemy import inspect, text
from sqlmodel import Session

from app.db.session import engine
from app.models import Principal, PrincipalStatus


def provision_principal(principal_id: UUID) -> None:
    if "principal" not in inspect(engine).get_table_names():
        raise RuntimeError("Principal schema is absent; apply 0004_principal_expand first.")

    with Session(engine) as session:
        existing = session.get(Principal, principal_id)
        other_count = session.connection().execute(
            text("SELECT count(*) FROM principal WHERE id <> :principal_id").bindparams(
                principal_id=principal_id
            )
        ).scalar_one()
        if other_count:
            raise RuntimeError("A different Principal already exists; provisioning is ambiguous.")
        if existing is None:
            session.add(Principal(id=principal_id, status=PrincipalStatus.active))
        elif existing.status != PrincipalStatus.active:
            raise RuntimeError("The requested Principal exists but is disabled.")
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision the confirmed deployment Principal.")
    parser.add_argument("--principal-id", required=True, type=UUID)
    args = parser.parse_args()
    provision_principal(args.principal_id)
    print(f"Principal {args.principal_id} is provisioned and active.")


if __name__ == "__main__":
    main()
