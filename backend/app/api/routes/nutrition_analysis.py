from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context, require_admin
from app.db.session import get_session
from app.schemas import (
    AnalysisEvaluateCommandV2,
    NutritionAnalysisMonitoringResponseV1,
    NutritionPatternAnalysisHistoryPageV2,
    NutritionPatternAnalysisResponseV2,
)
from app.services.pattern_analysis import (
    PatternAnalysisError,
    admin_monitoring,
    analysis_history_v2,
    current_analysis_v2,
    evaluate_analysis,
    exact_revision,
)

router = APIRouter(prefix="/progress/nutrition-analysis", tags=["nutrition-analysis"])
admin_router = APIRouter(prefix="/admin/nutrition-analysis", tags=["admin"])


def _error(error: PatternAnalysisError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message_ar": error.message_ar,
                "details": {},
                "request_id": str(uuid4()),
            }
        },
    )


def _unexpected_error(
    code: str = "INTERNAL_ERROR", message_ar: str = "تعذر إكمال الطلب."
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": code,
                "message_ar": message_ar,
                "details": {},
                "request_id": str(uuid4()),
            }
        },
    )


@router.get("/v2/current", response_model=NutritionPatternAnalysisResponseV2)
def current_v2(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        response = current_analysis_v2(session, principal)
        return JSONResponse(
            content=response.model_dump(mode="json"), headers={"ETag": response.etag}
        )
    except PatternAnalysisError as error:
        return _error(error)
    except Exception:
        return _unexpected_error()


@router.get("/v2/history", response_model=NutritionPatternAnalysisHistoryPageV2)
def history_v2(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        return analysis_history_v2(session, principal, limit, cursor)
    except PatternAnalysisError as error:
        return _error(error)
    except Exception:
        return _unexpected_error()


@router.get(
    "/v2/{analysis_id}/revisions/{revision}",
    response_model=NutritionPatternAnalysisResponseV2,
)
def revision_v2(
    analysis_id: UUID,
    revision: int,
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        response = exact_revision(session, principal, analysis_id, revision)
        return JSONResponse(
            content=response.model_dump(mode="json"), headers={"ETag": response.etag}
        )
    except PatternAnalysisError as error:
        return _error(error)
    except Exception:
        return _unexpected_error()


@router.post(
    "/v2/evaluate",
    response_model=NutritionPatternAnalysisResponseV2,
    responses={200: {"model": NutritionPatternAnalysisResponseV2}},
)
def evaluate_v2(
    command: AnalysisEvaluateCommandV2,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    if_match: str = Header(alias="If-Match"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        response, status_code, replayed = evaluate_analysis(
            session, principal, command, idempotency_key, if_match
        )
        headers = {"ETag": response.etag}
        if replayed:
            headers["Idempotent-Replayed"] = "true"
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(mode="json"),
            headers=headers,
        )
    except PatternAnalysisError as error:
        return _error(error)
    except Exception:
        return _unexpected_error("ANALYSIS_EVALUATION_FAILED", "تعذر إنشاء التحليل. حاول مرة أخرى.")


def _retired_v1() -> JSONResponse:
    return JSONResponse(
        status_code=410,
        content={
            "error": {
                "code": "NOVA_RETIREMENT_V1_ENDPOINT_RETIRED",
                "message_ar": "هذا الإصدار من تحليل النمط الغذائي لم يعد نشطًا.",
                "details": {},
                "request_id": str(uuid4()),
            }
        },
    )


@router.get("/current", include_in_schema=False)
def current_v1_retired():
    return _retired_v1()


@router.get("/history", include_in_schema=False)
def history_v1_retired():
    return _retired_v1()


@router.get("/{analysis_id}/revisions/{revision}", include_in_schema=False)
def revision_v1_retired(analysis_id: UUID, revision: int):
    del analysis_id, revision
    return _retired_v1()


@router.post("/evaluate", include_in_schema=False)
def evaluate_v1_retired():
    return _retired_v1()


@admin_router.get("/monitoring", response_model=NutritionAnalysisMonitoringResponseV1)
def monitoring(
    iso_week: str = Query(pattern=r"^\d{4}-W\d{2}$"),
    _admin: PrincipalContext = Depends(require_admin),
    session: Session = Depends(get_session),
):
    try:
        return admin_monitoring(session, iso_week)
    except PatternAnalysisError as error:
        return _error(error)
    except Exception:
        return _unexpected_error()
