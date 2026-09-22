# Current field dictionary and validation summary

Status: supporting requirements. Backend schemas and database constraints are executable authority.

## Principal

| Field | Required | Rule |
|---|---:|---|
| `id` | Yes | Durable UUID ownership key |
| `auth_user_id` | No | Unique Supabase subject when linked/provisioned |
| `email` | No | Unique case-insensitively when present; maximum 320 |
| `display_name` | No | Maximum 120 |
| `role` | Yes | `user` or `admin`; never accepted from browser metadata |
| `status` | Yes | `active` or `disabled` |

## Profile input

| Field | Required | Current rule |
|---|---:|---|
| `sex` | Yes | `male` or `female`; immutable after first successful Profile save |
| `birth_date` | Yes | Valid Gregorian date; Profile age 10–100 on effective date remains. Labs separately requires age >=18 on each test date; a DOB change cannot invalidate stored adult history |
| `height_cm` | Yes | Finite, 100–250 |
| `weight_kg` | Yes | Finite, 20–300 |
| `activity_level` | Yes | `sedentary`, `light`, `moderate`, `active`, `very_active` |
| `goal` | Yes | `cut`, `maintain`, `bulk` |
| `selected_cut_intensity` | Yes | `0.15`, `0.20`, or `0.25` |
| `protein_per_kg` | Yes | Finite, 1–3; default 1.2 |
| `fat_pct` | Yes | Finite, 0.15–0.40; sex-aware default 0.25/0.30 |

## TargetPlan

`id`, `principal_id`, `profile_id`, `effective_from`, `revision`,
`calculation_document`, and `created_at` are required. Revision is positive and unique
per `(principal_id, effective_from, revision)`. The calculation document is a JSON
object containing object-valued `target_result`. Rows are immutable.

## Food

Required identity/measurement fields are `name`, `primary_category`, `subcategory`,
`nutrition_basis`, `default_unit_type`, `unit_amount`, `unit_basis`, core calories and
macros, `nutrition_data_source`, and creator metadata. Name is trimmed/collapsed and
limited to 120 characters. `brand` is optional up to 80, `notes` up to 500, and
`ingredients` is optional text.

- `nutrition_basis` is `per_100g` or `per_100ml` and must agree with `unit_basis` (`g` or `ml`).
- `unit_amount` is finite and greater than 0, maximum 2000.
- calories: 0–3000; protein/fat: 0–300; carbohydrates: 0–500.
- Optional nutrients are null or finite/nonnegative and obey their Backend per-field maxima.
- Fiber cannot exceed carbohydrate; added sugar cannot exceed sugar; saturated/trans fat individually and together cannot exceed fat.
- `primary_category` and `subcategory` are required Registry-valid pairs.
- Duplicate identity is normalized name plus nutrition/default-unit basis and amount.
- No active/archive/status or uncategorized field exists.

## DiaryEntry

| Field | Required | Rule |
|---|---:|---|
| `id` | Yes | Client UUID supports safe replay |
| `principal_id` | Yes | Derived from authenticated Principal |
| `entry_date` | Yes | Any valid Diary date, including future |
| `food_id` | Yes | Existing global Food; deletion cascades entry removal |
| `target_plan_id` | No | Same-owner canonical plan for date, otherwise null |
| `quantity` | Yes | Finite and greater than zero |
| `recorded_unit_type` | Yes | Captured consumed-unit type |
| `recorded_unit_amount` | Yes | Captured finite positive unit amount |
| `recorded_unit_basis` | Yes | `g` or `ml` |
| `recorded_unit_label` | No | Captured label, maximum 80 |
| `meal_type` | Yes | `breakfast`, `lunch`, `dinner`, `snack`, or `unspecified` |

No nutrition snapshot, target provenance, day status, or day version is persisted.

## Exact governed destructive Food copy

- Title: `حذف الطعام؟`
- Body: `سيتم حذف هذا الطعام نهائيًا، كما سيتم حذف جميع سجلات اليوميات المرتبطة به لجميع المستخدمين. لا يمكن التراجع عن هذا الإجراء.`
- Buttons: `إلغاء` / `حذف نهائي`

## LabResult entered facts

| Field | Rule |
|---|---|
| `id` | Server UUID |
| `principal_id` | Derived authenticated owner; never a write input |
| `test_key` | Approved catalog key; immutable |
| `test_date` | Valid Gregorian DATE, no later than server Riyadh today; age >=18 |
| `entered_value` | Explicit finite nonnegative decimal string; unscaled NUMERIC storage |
| `entered_unit` | Unit supported by this catalog test |
| `created_at`, `updated_at` | Backend timestamps; update activity is distinct from test date |

Owner/test/date is unique. Normalize Arabic digits/decimal separator, trim outer
space and redundant leading zeros, retain fractional trailing zeros. Plain decimal
grammar is `[0-9]+(?:\.[0-9]+)?`, at most 128 normalized characters including the
decimal point. No exponent, sign, inequality, qualitative value or medical maximum.
Canonical values must also be nonnegative. Status, references and canonical display
are derived, never stored facts. Numeric rules belong to the packaged Labs catalog.

## Labs request and response fields

Batch create takes shared `test_date` and nonempty `results[]` containing only
`test_key`, `entered_value`, `entered_unit`, with `Idempotency-Key`. It returns
`receipt_version` and `result_ids`; `Idempotent-Replayed` identifies an old success.
The ID-only receipt is durable, survives edit/delete, and has no medical snapshot.
PATCH accepts only date/value/unit; DELETE physically removes the owned result.
Read models distinguish entered facts from `display_value`, `display_unit`,
`display_is_approximate`, `status`, `reference`, `chart_zones`, and one current
`medical_rules_version`. Overview adds `eligibility`, `server_today`, `read_only`,
latest result by test date and `last_updated_at`; detail returns full history.

## Exact governed Labs error copy

| Code | Arabic message |
|---|---|
| `LAB_PROFILE_REQUIRED` | أكمل بيانات الملف الشخصي قبل إضافة نتائج التحاليل. |
| `LAB_ADULT_REQUIRED` | يمكن إضافة نتائج أُجريت عند عمر 18 سنة فأكثر فقط. |
| `LAB_DATE_FUTURE` | لا يمكن اختيار تاريخ في المستقبل. |
| `LAB_DECIMAL_INVALID` | أدخل قيمة رقمية صريحة غير سالبة. |
| `LAB_VALUE_TOO_LONG` | تتجاوز القيمة حد التخزين المسموح. |
| `LAB_UNIT_UNSUPPORTED` | اختر وحدة مدعومة لهذا التحليل. |
| `LAB_TEST_UNSUPPORTED` | هذا التحليل غير مدعوم. |
| `LAB_DUPLICATE` | توجد نتيجة لهذا التحليل في التاريخ المحدد. |
| `LAB_BATCH_EMPTY` | أدخل نتيجة واحدة على الأقل. |
| `LAB_READ_ONLY` | التحاليل متاحة للمشرف للقراءة فقط. |
| `LAB_IDEMPOTENCY_CONFLICT` | تغيّرت بيانات عملية سبق إرسالها بالمفتاح نفسه. |
| `PROFILE_SEX_IMMUTABLE` | لا يمكن تعديل الجنس بعد حفظ الملف الشخصي. |
| `LABS_ADULT_HISTORY_REQUIRED` | لا يمكن تعديل تاريخ الميلاد لأنه يجعل نتائج تحاليل مسجلة قبل عمر 18 سنة. |
| `RESOURCE_NOT_FOUND` | المورد غير موجود. |

## Exact governed Labs presentation copy

Navigation/actions: `التحاليل`, `إضافة نتائج`, `تحاليلك`, `كل التحاليل`, `إكمال الملف`,
`سيتم حفظ N نتائج`, `القيم المرجعية للنظام`,
`تفسير النظام لهذا التحليل يفترض عينة صائمة`, `للقراءة فقط`.
Delete prompt: `حذف نتيجة [التحليل] بتاريخ [التاريخ]؟`; buttons `حذف النتيجة` / `إلغاء`.
Initial create success: `تم حفظ النتائج.`; replay: `تم تأكيد نجاح عملية الحفظ السابقة.`
Ambiguous edit, matching readback: `تعذر تأكيد الحفظ، لكن النتيجة الحالية تطابق القيم التي أدخلتها. يمكنك إغلاق النافذة لمراجعتها.`
Ambiguous edit, differing readback: `النتيجة الحالية تختلف عن القيم التي أدخلتها. أغلق النافذة لمراجعتها قبل تعديلها مجددًا.`
These messages do not confirm PATCH success; current facts and the draft remain
separate, with GET-only reread and explicit close before editing again.

| Status | Arabic label |
|---|---|
| `low` | منخفض |
| `in_range` | ضمن النطاق |
| `high` | مرتفع |
| `normal` | طبيعي |
| `prediabetes_range` | نطاق ما قبل السكري |
| `diabetes_range` | نطاق السكري |
| `desirable` | مرغوب |
| `above_desirable` | أعلى من المرغوب |
| `borderline_high` | مرتفع حدّيًا |
| `very_high` | مرتفع جدًا |
| `acceptable` | مقبول |
| `deficient` | نطاق النقص |
| `inadequate` | غير كافٍ |
| `adequate_for_most` | كافٍ لمعظم الأشخاص |
| `borderline` | حدّي |
| `in_reference` | ضمن النطاق المرجعي |
