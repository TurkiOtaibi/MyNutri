"""Owner-scoped Labs transactions and durable create receipts."""

from datetime import date
from hashlib import sha256
import json
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.core.calendar import age_on, database_calendar_date
from app.labs.interpretation import chart_zones, interpret, resolve_rule
from app.labs.numbers import (
    _terminating_text,
    normalize_decimal_text,
    parse_entered_decimal,
    to_canonical,
)
from app.labs.types import Catalog, TestDefinition, Zone
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
from app.schemas import (
    LabCreateReceipt,
    LabCreateRequest,
    LabFieldError,
    LabStatus,
    LabStatusZone,
    LabResultResponse,
    LabEligibility,
    LabCatalogTest,
    LabOverviewItem,
    LabOverviewResponse,
    LabChartZoneSegment,
    LabTestDetailResponse,
)
from app.services.errors import resource_not_found
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

        created_at = utcnow()
        rows = [
            LabResult(
                principal_id=principal.principal_id,
                test_key=row.test_key,
                test_date=payload.test_date,
                entered_value=parse_entered_decimal(row.entered_value),
                entered_unit=row.entered_unit,
                created_at=created_at,
                updated_at=created_at,
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


def _status(code: str, catalog: Catalog) -> LabStatus:
    metadata = catalog.statuses[code]
    return LabStatus(code=code, label_ar=metadata.label_ar, tone=metadata.tone)


def _zones(zones: tuple[Zone, ...], catalog: Catalog) -> list[LabStatusZone]:
    def boundary(value):
        if value is None:
            return None
        text = _terminating_text(value)
        if text is None:
            raise ValueError("Approved reference boundaries must be finite decimals")
        return text

    return [
        LabStatusZone(
            status=_status(zone.status, catalog),
            low=boundary(zone.low),
            high=boundary(zone.high),
            low_inclusive=zone.low_inclusive,
            high_inclusive=zone.high_inclusive,
        )
        for zone in zones
    ]


def project_result(row, profile, catalog: Catalog) -> LabResultResponse:
    """Interpret captured facts only; also usable after a mutation has committed."""
    result = interpret(
        catalog.tests[row.test_key],
        row.entered_value,
        row.entered_unit,
        profile.birth_date,
        profile.sex,
        row.test_date,
        catalog.version,
    )
    return LabResultResponse(
        id=row.id,
        test_key=row.test_key,
        test_date=row.test_date,
        entered_value=format(row.entered_value, "f"),
        entered_unit=row.entered_unit,
        created_at=row.created_at,
        updated_at=row.updated_at,
        display_value=result.display_value,
        display_unit=result.display_unit,
        display_is_approximate=result.display_is_approximate,
        status=_status(result.status_code, catalog),
        age_years=result.rule.age_years,
        reference_zones=_zones(result.rule.zones, catalog),
        medical_rules_version=catalog.version,
    )


def _read_snapshot(session: Session, principal_id: UUID, test_key: str | None = None):
    # Select immutable scalar Rows, not ORM identities: an existing Session may
    # hold stale or dirty Profile/results. One statement supplies one MVCC snapshot.
    ownership = LabResult.principal_id == Principal.id
    if test_key is not None:
        ownership = ownership & (LabResult.test_key == test_key)
    statement = (
        select(
            Principal.id.label("owner_id"),
            Profile.birth_date,
            Profile.sex,
            LabResult.id,
            LabResult.test_key,
            LabResult.test_date,
            LabResult.entered_value,
            LabResult.entered_unit,
            LabResult.created_at,
            LabResult.updated_at,
        )
        .select_from(Principal)
        .outerjoin(Profile, Profile.principal_id == Principal.id)
        .outerjoin(LabResult, ownership)
        .where(Principal.id == principal_id)
        .order_by(LabResult.test_key, LabResult.test_date.desc())
    )
    with session.no_autoflush:
        rows = session.exec(statement).all()
    if not rows:
        raise resource_not_found()
    profile = rows[0] if rows[0].birth_date is not None else None
    return profile, [row for row in rows if row.id is not None] if profile else []


def _eligibility(profile, today: date, read_only: bool) -> LabEligibility:
    if read_only:
        return LabEligibility(allowed=False, reason="read_only")
    if profile is None:
        return LabEligibility(allowed=False, reason="profile_required")
    if age_on(profile.birth_date, today) < 18:
        return LabEligibility(allowed=False, reason="adult_only")
    return LabEligibility(allowed=True)


def project_catalog_test(test: TestDefinition) -> LabCatalogTest:
    return LabCatalogTest(
        test_key=test.key,
        name_ar=test.name_ar,
        name_en=test.name_en,
        abbreviation=test.abbreviation,
        primary_category=test.primary_category,
        measurement=test.measurement,
        specimen_context=test.specimen_context,
        default_input_unit=test.default_input_unit,
        canonical_unit=test.canonical_unit,
        supported_units=list(test.supported_units),
        fasting_assumption=test.fasting_assumption,
        panels=list(test.panels),
    )


def read_labs(
    session: Session,
    principal_id: UUID,
    read_only: bool,
    catalog: Catalog,
) -> LabOverviewResponse:
    today = database_calendar_date(session)
    profile, rows = _read_snapshot(session, principal_id)
    grouped = {}
    for row in rows:
        grouped.setdefault(row.test_key, []).append(row)
    return LabOverviewResponse(
        items=[
            LabOverviewItem(
                test_key=key,
                latest=project_result(history[0], profile, catalog),
                last_updated_at=max(row.updated_at for row in history),
            )
            for key, history in grouped.items()
        ],
        eligibility=_eligibility(profile, today, read_only),
        server_today=today,
        medical_rules_version=catalog.version,
        read_only=read_only,
    )


def read_lab_test(
    session: Session,
    principal_id: UUID,
    test_key: str,
    read_only: bool,
    catalog: Catalog,
) -> LabTestDetailResponse:
    test = catalog.tests.get(test_key)
    if test is None:
        raise resource_not_found()
    today = database_calendar_date(session)
    profile, rows = _read_snapshot(session, principal_id, test_key)
    results = [project_result(row, profile, catalog) for row in rows]
    reference_at = results[0].test_date if results else today
    # Reference availability depends on demographics, separately from permission
    # to write. An administrator still sees the adult Profile's reference zones.
    reference = (
        _zones(resolve_rule(test, profile.birth_date, profile.sex, reference_at).zones, catalog)
        if profile is not None and age_on(profile.birth_date, reference_at) >= 18
        else []
    )
    segments = (
        chart_zones(test, profile.birth_date, profile.sex, rows[-1].test_date, rows[0].test_date)
        if rows
        else ()
    )
    return LabTestDetailResponse(
        test=project_catalog_test(test),
        results=results,
        chart_zones=[
            LabChartZoneSegment(
                from_date=segment.from_date,
                to_date_exclusive=segment.to_date_exclusive,
                age_min=segment.age_min,
                zones=_zones(segment.zones, catalog),
            )
            for segment in segments
        ],
        reference_at_date=reference_at,
        reference_zones=reference,
        eligibility=_eligibility(profile, today, read_only),
        server_today=today,
        medical_rules_version=catalog.version,
        read_only=read_only,
    )
