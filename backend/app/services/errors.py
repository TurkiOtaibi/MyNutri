from fastapi import HTTPException, status


def resource_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "RESOURCE_NOT_FOUND", "message_ar": "المورد غير موجود."},
    )
