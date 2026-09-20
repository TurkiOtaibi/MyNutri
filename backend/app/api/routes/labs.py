"""Authorized Labs HTTP contracts and a private, sanitized failure boundary."""

from dataclasses import asdict
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import SkipValidation
from sqlmodel import Session
from starlette.exceptions import HTTPException
from starlette.types import Message, Receive, Scope, Send

from app.core.auth import PrincipalContext, get_principal_context
from app.db.session import get_session
from app.labs.catalog import get_catalog
from app.labs.types import Catalog
from app.models import PrincipalRole
from app.schemas import (
    LabCatalogResponse,
    LabCreateReceipt,
    LabCreateRequest,
    LabErrorResponse,
    LabOverviewResponse,
    LabResultPatch,
    LabResultResponse,
    LabTestDetailResponse,
)
from app.services import labs as service
from app.services.labs_errors import LabValidationError, field_error, validate_labs_payload

logger = logging.getLogger(__name__)
ERROR_RESPONSES = {409: {"model": LabErrorResponse}, 422: {"model": LabErrorResponse}}


class LabsRoute(APIRoute):
    """Cover dependencies, decoding, endpoint and response serialization without logging facts."""

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Labs returns materialized JSON/204 responses, never streams. Retain the
        # existing message/bytes objects (no body copy) until yielded dependencies
        # close, so a cleanup failure cannot expose a traceback or a false success.
        messages: list[Message] = []

        async def retain(message: Message) -> None:
            messages.append(message)

        try:
            await super().handle(scope, receive, retain)
        except HTTPException as error:
            response = JSONResponse(
                status_code=error.status_code, content={"detail": error.detail},
                headers={**(error.headers or {}), "Cache-Control": "no-store"},
            )
            await response(scope, receive, send)
        except Exception as error:
            logger.error("Labs request failed: %s", type(error).__name__)
            response = JSONResponse(
                status_code=500, content={"detail": "Internal Server Error"},
                headers={"Cache-Control": "no-store"},
            )
            await response(scope, receive, send)
        else:
            for message in messages:
                await send(message)

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def private_handler(request: Request) -> Response:
            try:
                response = await handler(request)
            except LabValidationError as error:
                response = JSONResponse(
                    status_code=error.status_code,
                    content={"detail": [item.model_dump() for item in error.errors]},
                )
            except RequestValidationError as error:
                # FastAPI's default envelope echoes input/JSON fragments and Pydantic context.
                response = JSONResponse(status_code=422, content={"detail": [
                    {
                        "loc": list(item["loc"]),
                        "msg": "راجع الحقول المحددة ثم حاول مرة أخرى.",
                        "type": item["type"],
                    }
                    for item in error.errors()
                ]})
            except HTTPException as error:
                response = JSONResponse(
                    status_code=error.status_code, content={"detail": error.detail},
                    headers=error.headers,
                )
            except Exception as error:
                # Never pass exception text, exc_info, request URLs/IDs, or SQL parameters.
                logger.error("Labs request failed: %s", type(error).__name__)
                response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
            response.headers["Cache-Control"] = "no-store"
            return response

        return private_handler


router = APIRouter(prefix="/labs", tags=["labs"], route_class=LabsRoute, responses=ERROR_RESPONSES)


def _require_writer(principal: PrincipalContext) -> None:
    # Services still recheck authoritative role/status under the shared Principal lock.
    if principal.role == PrincipalRole.admin:
        raise LabValidationError(403, [field_error("LAB_READ_ONLY")])


@router.get("/catalog", response_model=LabCatalogResponse)
def read_catalog(
    _principal: PrincipalContext = Depends(get_principal_context),
    catalog: Catalog = Depends(get_catalog),
) -> LabCatalogResponse:
    return LabCatalogResponse(
        medical_rules_version=catalog.version,
        categories=[asdict(category) for category in catalog.categories],
        panels=[asdict(panel) for panel in catalog.panels],
        tests=[service.project_catalog_test(test) for test in catalog.tests.values()],
    )


@router.get("", response_model=LabOverviewResponse)
def read_overview(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
    catalog: Catalog = Depends(get_catalog),
) -> LabOverviewResponse:
    return service.read_labs(session, principal.principal_id, principal.role == PrincipalRole.admin, catalog)


@router.get("/tests/{test_key}", response_model=LabTestDetailResponse)
def read_test(
    test_key: str,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
    catalog: Catalog = Depends(get_catalog),
) -> LabTestDetailResponse:
    return service.read_lab_test(
        session, principal.principal_id, test_key, principal.role == PrincipalRole.admin, catalog,
    )


@router.post("/results", response_model=LabCreateReceipt, status_code=201, responses={
    201: {"headers": {"Idempotent-Replayed": {"schema": {"type": "string", "enum": ["true", "false"]}}}},
})
def add_results(
    payload: Annotated[SkipValidation[LabCreateRequest], Body()],
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
    catalog: Catalog = Depends(get_catalog),
) -> LabCreateReceipt:
    _require_writer(principal)
    receipt, replayed = service.create_results(
        session, principal, validate_labs_payload(LabCreateRequest, payload), idempotency_key, catalog,
    )
    response.headers["Idempotent-Replayed"] = "true" if replayed else "false"
    return receipt


@router.patch("/results/{result_id}", response_model=LabResultResponse)
def edit_result(
    result_id: UUID,
    payload: Annotated[SkipValidation[LabResultPatch], Body()],
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
    catalog: Catalog = Depends(get_catalog),
) -> LabResultResponse:
    _require_writer(principal)
    return service.update_result(
        session, principal, result_id, validate_labs_payload(LabResultPatch, payload), catalog,
    )


@router.delete("/results/{result_id}", status_code=204)
def remove_result(
    result_id: UUID,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
) -> Response:
    _require_writer(principal)
    service.delete_result(session, principal, result_id)
    return Response(status_code=204)
