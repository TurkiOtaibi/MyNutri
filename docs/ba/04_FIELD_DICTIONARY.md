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
| `sex` | Yes | `male` or `female` |
| `birth_date` | Yes | Valid Gregorian date; age 10–100 on effective date |
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
