"""Labs domain errors; routes keep the field-specific detail envelope."""

from app.schemas import LabFieldError


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
