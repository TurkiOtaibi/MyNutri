from fastapi import APIRouter, Depends

from app.core.auth import PrincipalContext, get_principal_context
from app.schemas import AccountResponse

router = APIRouter(prefix="/account", tags=["account"])


@router.get("/me", response_model=AccountResponse)
def current_account(
    principal: PrincipalContext = Depends(get_principal_context),
) -> AccountResponse:
    if principal.auth_user_id is None:
        raise RuntimeError("Authenticated Supabase account is not linked.")
    return AccountResponse(
        principal_id=principal.principal_id,
        auth_user_id=principal.auth_user_id,
        email=principal.email,
        display_name=principal.display_name,
        role=principal.role,
        status="active",
    )
