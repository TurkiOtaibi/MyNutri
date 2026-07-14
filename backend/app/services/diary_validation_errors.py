from typing import Any, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_diary_payload(schema: type[ModelT], payload: dict[str, Any]) -> ModelT:
    try:
        return schema.model_validate(payload)
    except ValidationError as error:
        details = []
        for item in error.errors():
            field = next((part for part in reversed(item.get("loc", ())) if isinstance(part, str)), None)
            error_type = str(item.get("type", "value_error"))
            if field == "meal_type":
                message = "اختر قسم وجبة صحيحًا."
                code = "invalid_meal_type"
            elif field == "quantity":
                message = "أدخل كمية صحيحة بين 0.01 و50."
                code = "invalid_quantity"
            elif field == "entry_date":
                message = "لا يمكن تسجيل يوميات بتاريخ مستقبلي."
                code = "invalid_entry_date"
            else:
                message = "راجع الحقول المحددة ثم حاول مرة أخرى."
                code = "invalid"
            details.append(
                {
                    "loc": ["body", field] if field else ["body"],
                    "field": field,
                    "code": code,
                    "msg": message,
                    "type": error_type,
                }
            )
        raise HTTPException(status_code=422, detail=details) from error
