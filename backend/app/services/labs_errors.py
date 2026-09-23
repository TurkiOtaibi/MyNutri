"""Labs domain errors; routes keep the field-specific detail envelope."""

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.schemas import LabFieldError

ModelT = TypeVar("ModelT", bound=BaseModel)


MESSAGES = {
    "LAB_PROFILE_REQUIRED": "أكمل بيانات الملف الشخصي قبل إضافة نتائج التحاليل.",
    "LAB_ADULT_REQUIRED": "يمكن إضافة نتائج أُجريت عند عمر 18 سنة فأكثر فقط.",
    "LAB_DATE_FUTURE": "لا يمكن اختيار تاريخ في المستقبل.",
    "LAB_DECIMAL_INVALID": "أدخل قيمة رقمية صريحة غير سالبة.",
    "LAB_VALUE_TOO_LONG": "تتجاوز القيمة حد التخزين المسموح.",
    "LAB_UNIT_UNSUPPORTED": "اختر وحدة مدعومة لهذا التحليل.",
    "LAB_TEST_UNSUPPORTED": "هذا التحليل غير مدعوم.",
    "LAB_DUPLICATE": "توجد نتيجة لهذا التحليل في التاريخ المحدد.",
    "LAB_BATCH_EMPTY": "أدخل نتيجة واحدة على الأقل.",
    "LAB_READ_ONLY": "التحاليل متاحة للمشرف للقراءة فقط.",
    "LAB_IDEMPOTENCY_CONFLICT": "تغيّرت بيانات عملية سبق إرسالها بالمفتاح نفسه.",
    "LAB_RESULT_CHANGED": "تغيّرت هذه النتيجة منذ فتحها. راجع قيمها الحالية قبل تعديلها مجددًا.",
    "INVALID_IDEMPOTENCY_KEY": "مفتاح الطلب غير صالح.",
    "INVALID_CREDENTIAL": "بيانات الدخول غير صالحة.",
}


def field_error(
    code: str,
    field: str | None = None,
    *,
    index: int | None = None,
    test_key: str | None = None,
) -> LabFieldError:
    loc: list[str | int] = ["body"]
    if field == "Idempotency-Key":
        loc = ["header", field]
    else:
        if index is not None:
            loc.extend(["results", index])
        if field is not None:
            loc.append(field)
    return LabFieldError(
        loc=loc, field=field, test_key=test_key, code=code, msg=MESSAGES[code], type=code
    )


class LabValidationError(Exception):
    def __init__(self, status_code: int, errors: list[LabFieldError]) -> None:
        super().__init__("Labs validation failed")
        self.status_code = status_code
        self.errors = errors


# Structural checks deliberately precede mutable catalog/Profile validation in services.
def validate_labs_payload(schema: type[ModelT], payload: Any) -> ModelT:
    """Keep full field locations without echoing entered values or validation context."""
    try:
        return schema.model_validate(payload)
    except ValidationError as error:
        details = []
        for item in error.errors(include_input=False, include_context=False, include_url=False):
            loc = ["body", *item["loc"]]
            field = next((part for part in reversed(item["loc"]) if isinstance(part, str)), None)
            error_type = item["type"]
            if error_type in MESSAGES:
                code, message = error_type, MESSAGES[error_type]
            elif error_type == "extra_forbidden":
                code = "NON_AUTHORITATIVE_FIELD"
                message = "هذا الحقل يحدده الخادم ولا يقبله من العميل."
            else:
                code, message = "invalid", "راجع الحقول المحددة ثم حاول مرة أخرى."
            test_key = None
            nested = item["loc"]
            if (len(nested) >= 2 and nested[0] == "results" and isinstance(nested[1], int)
                    and isinstance(payload, dict) and isinstance(payload.get("results"), list)):
                row = payload["results"][nested[1]]
                if isinstance(row, dict) and isinstance(row.get("test_key"), str):
                    test_key = row["test_key"]
            details.append(LabFieldError(
                loc=loc, field=field, test_key=test_key,
                code=code, msg=message, type=error_type,
            ))
        raise LabValidationError(422, details) from None
