from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)

REQUIRED_MESSAGE = "هذا الحقل مطلوب."
INVALID_NUMBER_MESSAGE = "أدخل رقمًا صحيحًا."
BELOW_MIN_MESSAGE = "القيمة أقل من الحد المسموح."
ABOVE_MAX_MESSAGE = "القيمة أعلى من الحد المسموح."
INVALID_SELECT_MESSAGE = "اختر قيمة صحيحة."
VALIDATION_MESSAGE = "راجع الحقول المحددة ثم حاول مرة أخرى."

FOOD_NAME_REQUIRED_MESSAGE = "اسم الطعام مطلوب."
DUPLICATE_FOOD_MESSAGE = "هذا الطعام موجود مسبقًا بنفس الوحدة."
OPTIONAL_NUTRIENT_NEGATIVE_MESSAGE = "القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0."
OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE = "القيمة الغذائية الإضافية أعلى من الحد المسموح."
FIBER_GT_CARBS_MESSAGE = "الألياف لا يمكن أن تكون أكبر من الكربوهيدرات."
ADDED_SUGAR_GT_SUGAR_MESSAGE = "السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر."
SATURATED_FAT_GT_FAT_MESSAGE = "الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون."
TRANS_FAT_GT_FAT_MESSAGE = "الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون."
SATURATED_TRANS_GT_FAT_MESSAGE = (
    "مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون."
)

REQUIRED_FOOD_FIELDS = {
    "name",
    "nutrition_basis",
    "default_unit_type",
    "unit_amount",
    "unit_basis",
    "calories",
    "protein_g",
    "carb_g",
    "fat_g",
    "food_category_key",
}

NUMERIC_FOOD_FIELDS = {
    "unit_amount",
    "calories",
    "protein_g",
    "carb_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "added_sugar_g",
    "saturated_fat_g",
    "trans_fat_g",
    "sodium_mg",
    "cholesterol_mg",
    "potassium_mg",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "zinc_mg",
    "selenium_mcg",
    "vitamin_d_mcg",
    "vitamin_b12_mcg",
    "vitamin_c_mg",
    "vitamin_a_mcg",
    "vitamin_a_rae_mcg",
    "folate_mcg",
    "folate_dfe_mcg",
    "vitamin_k_mcg",
    "iodine_mcg",
}

SELECT_FOOD_FIELDS = {
    "nutrition_basis",
    "default_unit_type",
    "unit_basis",
    "food_kind",
    "food_category_key",
    "grain_type",
    "baked_good_type",
    "grain_starch_type",
    "type",
    "source_type",
    "classification",
    "data_status",
}
AUTHORITATIVE_OWNER_FIELDS = {"principal_id", "owner_id", "user_id"}

CUSTOM_MESSAGE_CODES = {
    ABOVE_MAX_MESSAGE: "above_max",
    FOOD_NAME_REQUIRED_MESSAGE: "required",
    OPTIONAL_NUTRIENT_NEGATIVE_MESSAGE: "optional_nutrient_below_min",
    OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE: "optional_nutrient_above_max",
    FIBER_GT_CARBS_MESSAGE: "fiber_gt_carbs",
    ADDED_SUGAR_GT_SUGAR_MESSAGE: "added_sugar_gt_sugar",
    SATURATED_FAT_GT_FAT_MESSAGE: "saturated_fat_gt_fat",
    TRANS_FAT_GT_FAT_MESSAGE: "trans_fat_gt_fat",
    SATURATED_TRANS_GT_FAT_MESSAGE: "saturated_trans_gt_fat",
    DUPLICATE_FOOD_MESSAGE: "duplicate_food",
    "اسم مصدر البيانات الغذائية مطلوب لنوع المصدر المحدد.": "source_name_required",
    "نوع مصدر المكونات مطلوب عند إدخال المكونات.": "ingredients_source_required",
    "اسم مصدر المكونات مطلوب لنوع المصدر المحدد.": "ingredients_source_name_required",
    "مجموعة غذائية غير معتمدة.": "invalid_food_group",
    "النوع الفرعي مطلوب وغير متوافق مع المجموعة الغذائية.": "invalid_food_group_subtype",
    "هذه المجموعة لا تقبل نوعًا فرعيًا.": "food_group_subtype_not_allowed",
    "فئة الطعام غير معتمدة.": "invalid_food_category",
    "نوع المخبوزات مطلوب لفئة المخبوزات.": "required_category_detail",
    "نوع الحبوب مطلوب لفئة المخبوزات.": "required_category_detail",
    "نوع الحبوب والنشويات غير متاح لفئة المخبوزات.": "unrelated_category_detail",
    "نوع الحبوب أو النشويات مطلوب لهذه الفئة.": "required_category_detail",
    "نوع الحبوب مطلوب لفئة الحبوب والنشويات.": "required_category_detail",
    "نوع المخبوزات غير متاح لفئة الحبوب والنشويات.": "unrelated_category_detail",
    "تفاصيل الحبوب والمخبوزات غير متاحة لفئة الطعام المحددة.": "unrelated_category_detail",
    "لا يمكن تكرار المجموعة الغذائية للطعام نفسه.": "duplicate_food_group",
    "مجموع مساهمات المجموعات الغذائية لا يمكن أن يتجاوز 100.": "food_group_total_exceeded",
    "لا يمكن تكرار السمة التحليلية.": "duplicate_analytical_trait",
    "سمة تحليلية غير معتمدة.": "invalid_analytical_trait",
    "الحالة غير المعروفة لا تقبل مساهمات غذائية.": "unknown_group_status_with_contributions",
    "اكتمال التصنيف غير المعروف لا يقبل مساهمات غذائية.": "unknown_group_completeness_with_contributions",
    "التصنيف الجزئي يتطلب مساهمة غذائية واحدة على الأقل.": "partial_group_data_requires_contribution",
    "الحالة المؤكدة لا تقبل مساهمة تقديرية.": "known_group_data_contains_estimate",
    "الحالة التقديرية تتطلب مساهمة تقديرية واحدة على الأقل.": "estimated_group_data_requires_estimate",
}

CATEGORY_DETAIL_ERROR_FIELDS = {
    "نوع المخبوزات مطلوب لفئة المخبوزات.": "baked_good_type",
    "نوع الحبوب مطلوب لفئة المخبوزات.": "grain_type",
    "نوع الحبوب والنشويات غير متاح لفئة المخبوزات.": "grain_starch_type",
    "نوع الحبوب أو النشويات مطلوب لهذه الفئة.": "grain_starch_type",
    "نوع الحبوب مطلوب لفئة الحبوب والنشويات.": "grain_type",
    "نوع المخبوزات غير متاح لفئة الحبوب والنشويات.": "baked_good_type",
    "تفاصيل الحبوب والمخبوزات غير متاحة لفئة الطعام المحددة.": "food_category_key",
}


def food_error_detail(
    field: str | None,
    code: str,
    message: str,
    error_type: str = "value_error",
) -> dict[str, Any]:
    loc = ["body", field] if field else ["body"]
    return {"loc": loc, "field": field, "code": code, "msg": message, "type": error_type}


def duplicate_food_detail() -> list[dict[str, Any]]:
    return [
        food_error_detail(
            "name", "duplicate_food", DUPLICATE_FOOD_MESSAGE, "value_error.duplicate_food"
        )
    ]


def validate_food_payload(schema: type[ModelT], payload: dict[str, Any]) -> ModelT:
    submitted_owner_fields = AUTHORITATIVE_OWNER_FIELDS.intersection(payload)
    if submitted_owner_fields:
        field = sorted(submitted_owner_fields)[0]
        raise HTTPException(
            status_code=422,
            detail=[
                food_error_detail(
                    field,
                    "non_authoritative_field",
                    "لا يمكن للعميل تحديد مالك السجل.",
                )
            ],
        )
    try:
        validated = schema.model_validate(payload)
    except ValidationError as error:
        raise food_validation_http_exception(error) from error
    if schema.__name__ == "FoodCreate":
        for field in ("food_category_key", "food_kind", "nutrition_source"):
            if field not in payload or payload[field] is None:
                raise HTTPException(
                    status_code=422,
                    detail=[food_error_detail(field, "required", REQUIRED_MESSAGE, "missing")],
                )
        if payload["food_kind"] == "unknown":
            raise HTTPException(
                status_code=422,
                detail=[
                    food_error_detail(
                        "food_kind",
                        "legacy_value_not_allowed",
                        "اختر نوع الطعام: بسيط أو مركب.",
                    )
                ],
            )
    return validated


def food_validation_http_exception(error: ValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=format_food_validation_errors(error))


def format_food_validation_errors(error: ValidationError) -> list[dict[str, Any]]:
    return [_format_error(item) for item in error.errors()]


def _format_error(item: dict[str, Any]) -> dict[str, Any]:
    field = _field_from_loc(item.get("loc", ()))
    error_type = str(item.get("type", "value_error"))
    raw_message = _clean_message(str(item.get("msg", VALIDATION_MESSAGE)))
    raw_input = item.get("input")

    if field in REQUIRED_FOOD_FIELDS and (error_type == "missing" or raw_input is None):
        return food_error_detail(field, "required", REQUIRED_MESSAGE, error_type)

    if field in SELECT_FOOD_FIELDS:
        if error_type == "missing":
            return food_error_detail(field, "required", REQUIRED_MESSAGE, error_type)
        return food_error_detail(field, "invalid_option", INVALID_SELECT_MESSAGE, error_type)

    if field in NUMERIC_FOOD_FIELDS:
        if error_type in {
            "float_parsing",
            "float_type",
            "int_parsing",
            "int_type",
            "decimal_parsing",
        }:
            return food_error_detail(field, "invalid_number", INVALID_NUMBER_MESSAGE, error_type)
        if error_type in {"greater_than", "greater_than_equal"}:
            return food_error_detail(field, "below_min", BELOW_MIN_MESSAGE, error_type)
        if error_type in {"less_than", "less_than_equal"}:
            return food_error_detail(field, "above_max", ABOVE_MAX_MESSAGE, error_type)

    custom_code = CUSTOM_MESSAGE_CODES.get(raw_message)
    if custom_code is not None:
        field = field or CATEGORY_DETAIL_ERROR_FIELDS.get(raw_message)
        return food_error_detail(field, custom_code, raw_message, error_type)

    if field:
        return food_error_detail(field, "invalid", VALIDATION_MESSAGE, error_type)
    return food_error_detail(None, "invalid", VALIDATION_MESSAGE, error_type)


def _field_from_loc(loc: Any) -> str | None:
    if not isinstance(loc, (list, tuple)):
        return None
    for part in reversed(loc):
        if isinstance(part, str) and part != "body":
            return part
    return None


def _clean_message(message: str) -> str:
    prefix = "Value error, "
    if message.startswith(prefix):
        return message[len(prefix) :]
    return message
