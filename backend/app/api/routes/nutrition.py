from fastapi import APIRouter, Depends, Header, Response

from app.core.auth import PrincipalContext, get_principal_context
from app.nutrition_rules.manifest import registry_response, rules_manifest_hash

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/registry", response_model=None)
def read_registry(
    response: Response,
    if_none_match: str | None = Header(default=None),
    principal: PrincipalContext = Depends(get_principal_context),
) -> dict[str, object] | Response:
    del principal
    manifest_hash = rules_manifest_hash()
    etag = f'"{manifest_hash}"'
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=300, must-revalidate"
    if if_none_match in {etag, manifest_hash}:
        return Response(
            status_code=304,
            headers={"ETag": etag, "Cache-Control": response.headers["Cache-Control"]},
        )
    return registry_response()
