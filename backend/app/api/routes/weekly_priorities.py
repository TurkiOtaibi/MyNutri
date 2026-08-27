from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.db.session import get_session
from app.schemas import (
    BehaviorGoalCommandResponseV1,
    BehaviorGoalCommandV1,
    BehaviorGoalCurrentResponseV1,
    BehaviorGoalHistoryPageV1,
    Plan033ErrorResponseV1,
    WeeklyPriorityResultV1,
)
from app.services.weekly_priorities import (
    WeeklyPriorityError,
    command_goal,
    current_goal,
    current_recommendation,
    goal_history,
)


def _validation_error() -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message_ar": "تحقق من بيانات الطلب.",
                "details": {},
                "request_id": str(uuid4()),
            }
        },
    )


class Plan033Route(APIRoute):
    def get_route_handler(self):
        route_handler = super().get_route_handler()

        async def stable_validation_handler(request: Request):
            try:
                return await route_handler(request)
            except RequestValidationError:
                return _validation_error()

        return stable_validation_handler


priority_router = APIRouter(
    prefix="/progress/weekly-priorities",
    tags=["weekly-priorities"],
    route_class=Plan033Route,
)
goal_router = APIRouter(
    prefix="/progress/behavior-goals", tags=["behavior-goals"], route_class=Plan033Route
)
_ERROR_RESPONSES = {
    400: {"model": Plan033ErrorResponseV1, "description": "Invalid command identity"},
    404: {"model": Plan033ErrorResponseV1, "description": "Concealed owner-bound resource"},
    409: {"model": Plan033ErrorResponseV1, "description": "State, source, or version conflict"},
    422: {"model": Plan033ErrorResponseV1, "description": "Closed command validation error"},
    503: {"model": Plan033ErrorResponseV1, "description": "Feature or evidence unavailable"},
    500: {"model": Plan033ErrorResponseV1, "description": "Stable write failure"},
}


def _error(error: WeeklyPriorityError) -> JSONResponse:
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


def _unexpected() -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "GOAL_WRITE_FAILED",
                "message_ar": "تعذر حفظ الهدف. لم تُفقد بياناتك؛ حاول مجددًا.",
                "details": {},
                "request_id": str(uuid4()),
            }
        },
    )


@priority_router.get(
    "/current", response_model=WeeklyPriorityResultV1, responses=_ERROR_RESPONSES
)
def get_priority(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        result = current_recommendation(session, principal)
        return JSONResponse(content=result.model_dump(mode="json"), headers={"ETag": result.etag})
    except WeeklyPriorityError as error:
        return _error(error)
    except Exception:
        return _unexpected()


@goal_router.get(
    "/current", response_model=BehaviorGoalCurrentResponseV1, responses=_ERROR_RESPONSES
)
def get_goal(
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        return current_goal(session, principal)
    except WeeklyPriorityError as error:
        return _error(error)
    except Exception:
        return _unexpected()


@goal_router.get(
    "/history", response_model=BehaviorGoalHistoryPageV1, responses=_ERROR_RESPONSES
)
def get_goal_history(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        return goal_history(session, principal, limit, cursor)
    except WeeklyPriorityError as error:
        return _error(error)
    except Exception:
        return _unexpected()


@goal_router.post(
    "/{goal_id}/commands",
    response_model=BehaviorGoalCommandResponseV1,
    responses=_ERROR_RESPONSES,
)
def post_goal_command(
    goal_id: UUID,
    command: BehaviorGoalCommandV1,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    principal: PrincipalContext = Depends(get_principal_context),
    session: Session = Depends(get_session),
):
    try:
        response, status_code, replayed = command_goal(
            session, principal, goal_id, command, idempotency_key
        )
        headers = {
            "ETag": response.goal.etag,
            "Access-Control-Expose-Headers": "ETag, Idempotent-Replayed",
        }
        if replayed:
            headers["Idempotent-Replayed"] = "true"
        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(mode="json"),
            headers=headers,
        )
    except WeeklyPriorityError as error:
        return _error(error)
    except Exception:
        return _unexpected()
