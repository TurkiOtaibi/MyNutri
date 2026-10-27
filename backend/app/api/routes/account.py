from fastapi import APIRouter, Depends, Response

from app.core.auth import PrincipalContext, get_principal_context
from app.core.calendar import diary_calendar_authority
from app.schemas import AccountResponse, CalendarAuthorityResponse

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/me", response_model=AccountResponse)
def current_account(
    response: Response,
    principal: PrincipalContext = Depends(get_principal_context),
) -> AccountResponse:
    response.headers["Cache-Control"] = "no-store"
    return AccountResponse(
        principal_id=principal.principal_id,
        auth_user_id=principal.auth_user_id,
        email=principal.email,
        display_name=principal.display_name,
        role=principal.role,
        status="active",
        username=principal.username,
        must_change_password=principal.must_change_password,
    )


@router.get("/calendar", response_model=CalendarAuthorityResponse)
def current_calendar(
    _principal: PrincipalContext = Depends(get_principal_context),
) -> CalendarAuthorityResponse:
    authority = diary_calendar_authority()
    return CalendarAuthorityResponse(
        current_diary_date=authority.current_diary_date,
        calendar_timezone=authority.calendar_timezone,
        next_rollover_at=authority.next_rollover_at,
    )
