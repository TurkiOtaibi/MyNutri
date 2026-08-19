from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context, require_admin
from app.db.session import get_session
from app.schemas import (
    AnalysisEvaluateCommandV1,
    NutritionAnalysisMonitoringResponseV1,
    NutritionPatternAnalysisHistoryPageV1,
    NutritionPatternAnalysisResponseV1,
)
from app.services.pattern_analysis import (
    PatternAnalysisError,
    admin_monitoring,
    analysis_history,
    current_analysis,
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


@router.get("/current", response_model=NutritionPatternAnalysisResponseV1)
def current(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        response = current_analysis(session, principal)
        return JSONResponse(
            content=response.model_dump(mode="json"), headers={"ETag": response.etag}
        )
    except PatternAnalysisError as error:
        return _error(error)
    except Exception:
        return _unexpected_error()


@router.get("/history", response_model=NutritionPatternAnalysisHistoryPageV1)
def history(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        return analysis_history(session, principal, limit, cursor)
    except PatternAnalysisError as error:
        return _error(error)
    except Exception:
        return _unexpected_error()


@router.get(
    "/{analysis_id}/revisions/{revision}",
    response_model=NutritionPatternAnalysisResponseV1,
)
def revision(
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
    "/evaluate",
    response_model=NutritionPatternAnalysisResponseV1,
    responses={200: {"model": NutritionPatternAnalysisResponseV1}},
)
def evaluate(
    command: AnalysisEvaluateCommandV1,
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
