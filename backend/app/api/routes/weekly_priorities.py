from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.core.auth import PrincipalContext, get_principal_context
from app.db.session import get_session
from app.schemas import (
    BehaviorGoalCommandResponseV1,
    BehaviorGoalCommandV1,
    BehaviorGoalCurrentResponseV1,
    BehaviorGoalHistoryPageV1,
    WeeklyPriorityResultV1,
)
from app.services.weekly_priorities import (
    WeeklyPriorityError,
    command_goal,
    current_goal,
    current_recommendation,
    goal_history,
)

priority_router = APIRouter(prefix="/progress/weekly-priorities", tags=["weekly-priorities"])
goal_router = APIRouter(prefix="/progress/behavior-goals", tags=["behavior-goals"])


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


@priority_router.get("/current", response_model=WeeklyPriorityResultV1)
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


@goal_router.get("/current", response_model=BehaviorGoalCurrentResponseV1)
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


@goal_router.get("/history", response_model=BehaviorGoalHistoryPageV1)
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


@goal_router.post("/{goal_id}/commands", response_model=BehaviorGoalCommandResponseV1)
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
