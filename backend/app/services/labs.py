"""Owner-scoped Labs transactions and durable create receipts."""

from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import age_on, database_calendar_date
from app.labs.numbers import normalize_decimal_text, parse_entered_decimal, to_canonical
from app.labs.types import Catalog
from app.models import (
    IdempotencyRecord,
    IdempotencyState,
    LabResult,
    Principal,
    PrincipalRole,
    PrincipalStatus,
    Profile,
    utcnow,
)
from app.schemas import LabCreateReceipt, LabCreateRequest, LabFieldError
from app.services.labs_errors import LabValidationError, field_error


CREATE_OPERATION = "lab_results.create.v1"


def canonical_request_hash(payload: LabCreateRequest) -> str:
    document = {
        "operation": CREATE_OPERATION,
        "hash_schema": 1,
        "test_date": payload.test_date.isoformat(),
        "results": sorted(
            [
                {
                    "test_key": row.test_key,
                    "entered_value": normalize_decimal_text(row.entered_value),
                    "entered_unit": row.entered_unit,
                }
                for row in payload.results
            ],
            key=lambda row: (row["test_key"], row["entered_unit"], row["entered_value"]),
        ),
    }
    return sha256(
        json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _duplicate_errors(
    session: Session,
    owner_id: UUID,
    payload: LabCreateRequest,
) -> list[LabFieldError]:
    existing = set(
        session.exec(
            select(LabResult.test_key).where(
                LabResult.principal_id == owner_id,
                LabResult.test_date == payload.test_date,
                LabResult.test_key.in_([row.test_key for row in payload.results]),
            )
        ).all()
    )
    return [
        field_error("LAB_DUPLICATE", "test_key", index=index, test_key=row.test_key)
        for index, row in enumerate(payload.results)
        if row.test_key in existing
    ]


def create_results(
    session: Session,
    principal: PrincipalContext,
    payload: LabCreateRequest,
    idempotency_key: str,
    catalog: Catalog,
) -> tuple[LabCreateReceipt, bool]:
    """Commit entered facts and one permanent receipt under the shared owner lock."""
    try:
        if (
            not isinstance(idempotency_key, str)
            or not 1 <= len(idempotency_key) <= 128
            or not all(0x21 <= ord(character) <= 0x7E for character in idempotency_key)
        ):
            raise LabValidationError(
                422, [field_error("INVALID_IDEMPOTENCY_KEY", "Idempotency-Key")]
            )
        request_hash = canonical_request_hash(payload)
        actor = session.exec(
            select(Principal)
            .where(Principal.id == principal.principal_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one_or_none()
        if actor is None or actor.status != PrincipalStatus.active:
            raise LabValidationError(401, [field_error("INVALID_CREDENTIAL")])
        if actor.role == PrincipalRole.admin:
            raise LabValidationError(403, [field_error("LAB_READ_ONLY")])

        record = session.exec(
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.principal_id == principal.principal_id,
                IdempotencyRecord.operation == CREATE_OPERATION,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
            .execution_options(populate_existing=True)
        ).one_or_none()
        if record is not None:
            if record.request_hash != request_hash or record.state != IdempotencyState.completed:
                raise LabValidationError(
                    409, [field_error("LAB_IDEMPOTENCY_CONFLICT", "Idempotency-Key")]
                )
            receipt = LabCreateReceipt.model_validate(record.response_document)
            session.rollback()
            return receipt, True

        profile = session.exec(
            select(Profile)
            .where(
                Profile.principal_id == principal.principal_id,
            )
            .execution_options(populate_existing=True)
        ).one_or_none()
        errors: list[LabFieldError] = []
        if profile is None:
            errors.append(field_error("LAB_PROFILE_REQUIRED"))
        elif age_on(profile.birth_date, payload.test_date) < 18:
            errors.append(field_error("LAB_ADULT_REQUIRED", "test_date"))
        if payload.test_date > database_calendar_date(session):
            errors.append(field_error("LAB_DATE_FUTURE", "test_date"))
        seen = set()
        for index, row in enumerate(payload.results):

            def issue(code: str, field: str) -> None:
                errors.append(field_error(code, field, index=index, test_key=row.test_key))

            if row.test_key in seen:
                issue("LAB_DUPLICATE", "test_key")
            seen.add(row.test_key)
            test = catalog.tests.get(row.test_key)
            if test is None:
                issue("LAB_TEST_UNSUPPORTED", "test_key")
            elif row.entered_unit not in test.supported_units:
                issue("LAB_UNIT_UNSUPPORTED", "entered_unit")
            else:
                try:
                    to_canonical(test, parse_entered_decimal(row.entered_value), row.entered_unit)
                except ValueError:
                    issue("LAB_DECIMAL_INVALID", "entered_value")
        errors.extend(_duplicate_errors(session, principal.principal_id, payload))
        if errors:
            raise LabValidationError(
                409 if any(e.code == "LAB_DUPLICATE" for e in errors) else 422, errors
            )

        rows = [
            LabResult(
                principal_id=principal.principal_id,
                test_key=row.test_key,
                test_date=payload.test_date,
                entered_value=parse_entered_decimal(row.entered_value),
                entered_unit=row.entered_unit,
            )
            for row in payload.results
        ]
        session.add_all(rows)
        session.flush()
        receipt = LabCreateReceipt(result_ids=[row.id for row in rows])
        session.add(
            IdempotencyRecord(
                principal_id=principal.principal_id,
                operation=CREATE_OPERATION,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                state=IdempotencyState.completed,
                response_status=201,
                response_document=receipt.model_dump(mode="json"),
                resource_type="lab_result_set",
                resource_id=None,
                completed_at=utcnow(),
                expires_at=None,
            )
        )
        session.commit()
        return receipt, False
    except IntegrityError as error:
        session.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint == "uq_lab_result_principal_test_date":
            # The failed transaction is already rolled back. Read only owner-scoped
            # conflicts through a separate short-lived session for precise locations.
            with Session(session.get_bind()) as check:
                errors = _duplicate_errors(check, principal.principal_id, payload)
            if errors:
                raise LabValidationError(409, errors) from error
        elif constraint == "uq_idempotency_scope":
            raise LabValidationError(
                409, [field_error("LAB_IDEMPOTENCY_CONFLICT", "Idempotency-Key")]
            ) from error
        raise
    except Exception:
        session.rollback()
        raise
