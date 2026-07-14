# Field Validation Audit

Sources:
- `docs/ba/04_FIELD_DICTIONARY.md`
- `docs/ba/05_VALIDATION_RULES.md`
- `docs/ba/06_ERROR_MESSAGES.md`
- `backend/app/schemas.py`
- `backend/app/models.py`
- `frontend/components/ProfilePage.tsx`
- `frontend/components/FoodsPage.tsx`
- `frontend/components/DiaryPage.tsx`

## Overall Verdict

Field coverage is mostly strong in BA. Required/optional status, types, v1 ranges, system fields, core placeholders, error placement, and Arabic messages are documented.

Remaining BA weakness:
The Diary gram-mode fields are not tied to a final API/storage contract, and read-failure error copy is not exact. Some acceptance criteria still rely on generic min/max messages instead of field-specific expected text.

## Field Coverage by Entity

| Entity/form | BA field coverage | Current code alignment | QA readiness |
|---|---|---|---|
| Profile | Strong: types, required status, defaults, ranges, enums, messages. | Code ranges are looser/different; future birth date and age bounds missing. | Ready for QA design; implementation alignment required. |
| Food | Strong: core/optional nutrients, duplicate key, net carbs, archive fields, ranges, placeholder for `serving_label`. | Archive fields, max ranges, duplicate check, `fiber_g <= carb_g`, and product label for `serving_grams` missing. | Mostly ready for QA design. |
| DiaryEntry | Medium: serving fields, future date, active food, gram mode, snapshot, edit restrictions defined. | Gram mode missing; API schema only has `quantity`; update schema allows date/food changes. | Not final for gram-mode API tests. |
| API/system | Medium: auth header, sync fields Future Scope, online-only rules. | Sync fields and IndexedDB code still active. | Ready as implementation alignment audit. |

## Key Field/Validation Gaps

| Gap ID | Area | Severity | Evidence | Issue | Recommended BA fix |
|---|---|---|---|---|---|
| FV-001 | Diary gram fields | High | `04_FIELD_DICTIONARY.md`, `backend/app/schemas.py`, `frontend/lib/types.ts` | `log_mode` and `grams` are required by BA but final API/storage mapping is not decided. | Add a contract decision for serving vs gram payload and stored fields. |
| FV-002 | Network read errors | High | `06_ERROR_MESSAGES.md`, `US-NETWORK-READ-001` | Exact Arabic read-failure message is missing. | Add read-specific message separate from failed-write copy. |
| FV-003 | Field-specific min/max messages | Medium | `05_VALIDATION_RULES.md`, `06_ERROR_MESSAGES.md` | Generic min/max messages are defined, but no field-specific messages for values like height, calories, grams. | Either confirm generic copy is acceptable for all ranges or define field-specific copy. |
| FV-004 | Accepted character rules | Medium | `04_FIELD_DICTIONARY.md` | Food text allows "common punctuation" but does not list exact punctuation set. | Define exact allowed punctuation or mark broader Unicode text accepted with escaped rendering. |
| FV-005 | Mobile input hints | Medium | `04_FIELD_DICTIONARY.md`, `09_ACCEPTANCE_CRITERIA.md` | Numeric fields use type/control but do not specify mobile keyboard/inputmode expectations. | Add mobile keyboard guidance for numeric/date fields if required for QA. |
| FV-006 | Stale entity validation | Medium | `08_NEGATIVE_SCENARIOS.md`, code routes | Archived/stale food edit and already-deleted diary entry behavior are covered only by generic 404 mapping. | Add explicit stale edit/delete criteria for Food and Diary. |

## Backend/Frontend/BA Validation Mismatch

| Field/rule | BA rule | Current backend/frontend evidence | Alignment |
|---|---|---|---|
| Profile height | 100-250 | Backend `gt=0`; frontend `min=1` | Needs alignment |
| Profile weight | 20-300 | Backend `gt=0`; frontend `min=1` | Needs alignment |
| Protein/kg | 1.0-3.0 | Backend/frontend 1.6-2.2 | Needs alignment |
| Fat pct | 0.15-0.40 | Backend/frontend 0.2-0.3 | Needs alignment |
| Birth date | not future, age 10-100 | No backend age/future validation | Needs alignment |
| Food max values | D-012 ranges | Backend has minimums only | Needs alignment |
| Food text trimming/max | trim, max length, normalize | Backend min length only | Needs alignment |
| `fiber_g <= carb_g` | required | Not enforced; net carbs can be negative | Needs alignment |
| Duplicate food | active duplicate blocked | No duplicate check | Needs alignment |
| Food archive fields | `is_active`, `archived_at` | Not in model/migration/schema | Needs alignment |
| Diary future date | blocked | Schema accepts any date | Needs alignment |
| Diary serving quantity | 0.01-50 | Backend `gt=0`; no max | Needs alignment |
| Diary grams | 1-5000 with `serving_grams` | No field/API behavior | Needs alignment and BA contract fix |

## Error Message Audit

| Message area | BA status | Risk |
|---|---|---|
| Required field | Defined in Arabic | Ready. |
| Invalid number | Defined in Arabic | Ready. |
| Below/above min/max | Generic Arabic copy defined | Testable if generic copy is accepted. |
| Duplicate food | Defined in Arabic | Ready. |
| Fiber greater than carbs | Defined in Arabic | Ready. |
| Missing serving grams | Defined in Arabic | Ready after gram contract. |
| Future diary date | Defined in Arabic | Ready. |
| Unauthorized/server/API write failure | Defined in Arabic | Mostly ready. |
| API read failure | Not exact | High gap. |
| Food and Diary confirmation dialogs | Defined in Arabic | Ready. |
