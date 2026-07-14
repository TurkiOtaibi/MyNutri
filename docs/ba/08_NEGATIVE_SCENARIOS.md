# Negative and Edge Scenarios

This file lists required v1 negative and edge behavior after D-001 through D-023.

## Auth and Permissions

| Scenario | Expected behavior | Status | Evidence / decisions |
|---|---|---|---|
| Missing bearer token calls protected API | API returns 401. | Confirmed | `require_single_user` |
| Invalid bearer token calls protected API | API returns 401. | Confirmed | `require_single_user` |
| UI receives 401 | Show `تعذر الوصول. تحقق من صلاحية الدخول.` and do not present stale/queued data as saved. | Required / UI alignment needed | D-013 |
| Empty configured token in dev | API allows requests. | Confirmed | `require_single_user` |

## Profile

| Scenario | Expected behavior | Status |
|---|---|---|
| Profile not created | `/profile` returns 404; frontend shows `أدخل بياناتك لحساب الأهداف اليومية.` when the missing-profile state loads successfully. | Confirmed / UI alignment needed |
| Profile load fails | Show `تعذر تحميل الملف الشخصي. تحقق من الاتصال وحاول مرة أخرى.` and do not treat cached personal profile data as current. | Required by D-022 |
| Future birth date | Reject with `تاريخ الميلاد لا يمكن أن يكون في المستقبل.` | Required |
| Age below 10 | Reject with `العمر يجب أن يكون 10 سنوات أو أكثر.` | Required |
| Age above 100 | Reject with `العمر يجب ألا يتجاوز 100 سنة.` | Required |
| Height below 100 or above 250 | Reject with min/max Arabic error. | Required |
| Weight below 20 or above 300 | Reject with min/max Arabic error. | Required |
| Protein/kg outside 1.0-3.0 | Reject with min/max Arabic error. | Required |
| Fat percentage outside 0.15-0.40 | Reject with min/max Arabic error. | Required |
| API unreachable during profile save | Do not save locally; do not queue; keep the same visible input in the form until the user edits it, resets it, retries successfully, or navigates away; show write connection error. | Required / current code needs alignment |
| Server validation rejects profile with known fields | Show field-level errors beside affected fields; do not queue. | Required |
| Server validation rejects profile with unknown/form-level error | Show `راجع الحقول المظللة ثم حاول مرة أخرى.`; do not queue. | Required |
| User expects multiple profiles/person switching | Treat as Future Scope; v1 remains one Profile model. | Future Scope per D-016 |
| User requests profile reset/delete | Not supported in v1; user corrects data by editing existing profile fields. | Out of scope per D-017 |

## Current Foods - D-024/D-025

These scenarios supersede older Food scenarios that depend on archive/inactive state, `is_active`, `archived_at`, Active/Archived filters, `serving_label`, or `serving_grams` as Food source-of-truth fields.

| Scenario | Expected behavior | Status |
|---|---|---|
| User expects a large inline Add Food form on `/foods` | Not shown; Add Food is on `/foods/new`. | Required by D-024 |
| User opens `/foods/new` | Add Food page shows grouped sections and no delete action. | Required by D-024 |
| User opens `/foods/:id/edit` | Edit page reuses Add Food structure in edit mode. | Required by D-024 |
| Empty current Food catalog | Show empty state with Add Food action to `/foods/new`. | Required |
| Search no matches | Show no-results state; do not show deleted Foods. | Required |
| Food name blank or whitespace-only | Block save with required Arabic message. | Required |
| Nutrition basis missing/invalid | Block save with invalid-select Arabic message. | Required |
| Default unit type missing/invalid | Block save with invalid-select Arabic message. | Required |
| Unit amount blank/non-number/<=0 | Block save with required/invalid/min Arabic message. | Required |
| Unit basis missing/invalid | Block save with invalid-select Arabic message. | Required |
| Optional nutrient blank | Allow save; store as null/unknown. | Required |
| Optional nutrient negative | Block save with `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.` | Required by D-026 |
| Optional nutrient above D-026 max | Block save with `القيمة الغذائية الإضافية أعلى من الحد المسموح.` | Required by D-026 |
| `fiber_g > carb_g` | Block save with `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.` | Required |
| `added_sugar_g > sugar_g` when both are provided | Block save with `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.` | Required by D-026 |
| `saturated_fat_g > fat_g` | Block save with `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.` | Required by D-026 |
| `trans_fat_g > fat_g` | Block save with `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.` | Required by D-026 |
| `saturated_fat_g + trans_fat_g > fat_g` when all are provided | Block save with `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.` | Required by D-026 |
| First invalid optional nutrient is inside collapsed section | Expand Optional nutrients section and focus the first invalid field. | Required by D-026 |
| Current catalog exact duplicate | Block save with duplicate Arabic message using normalized `name + nutrition_basis + default_unit_type + unit_amount + unit_basis`. | Required |
| Duplicate of deleted Food | Allow creation because deleted Foods no longer exist in the catalog. | Required |
| Delete tapped accidentally | Confirmation dialog opens; cancel/Escape makes no change. | Required |
| Confirm Food delete | Permanently hard delete after successful API response; remove from list, search, and future Diary selection. | Required |
| Delete API fails | Food remains visible; no local delete is queued; show write/network/server error. | Required |
| Food deleted before edit submit | Reject with stale Food message and do not update locally. | Required by D-023/D-025 |
| Food deleted before Diary log submit | Reject with stale Food message and do not create a local Diary entry. | Required by D-023/D-025 |
| Deleted Food used by old Diary entries | Historical Diary display and totals remain through snapshot. | Required |
| Active/Archived filter appears | Defect; archive filters are not v1 requirements. | Required by D-025 |
| `is_active` or `archived_at` appears in Food UI/API requirements | Defect in BA/implementation planning; those fields are superseded by D-025. | Required by D-025 |
| Long Food name in list/card | Show up to two lines then truncate with ellipsis; no action overlap or horizontal scroll. | Required per D-020 |
| HTML/script in Food text | Store/display as plain text only; never execute or render as markup. | Required security/a11y baseline |

## Legacy Foods

The legacy scenarios below are retained for traceability. If they conflict with D-024/D-025, the current scenarios above control v1 requirements.

## Foods

| Scenario | Expected behavior | Status |
|---|---|---|
| Empty current Food catalog | Show `لا توجد أطعمة بعد. أضف أول طعام للبدء.` | Required |
| Search no matches | Show `لا توجد نتائج مطابقة للبحث.` | Required |
| Foods list API load fails | Show `تعذر تحميل قائمة الأطعمة. تحقق من الاتصال وحاول مرة أخرى.` and do not treat cached Foods data as current. | Required by D-022 |
| Food detail API load fails | Show `تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.` and block edit submit until fresh detail data loads. | Required by D-022 |
| Food name blank or whitespace-only | Block save with required Arabic message. | Required |
| Required D-025 Food identity/default-unit field blank | Block save with required Arabic message. | Required |
| Text too long | Block save with max Arabic message. | Required |
| Required numeric blank/non-number | Block save with required/invalid-number Arabic message. | Required |
| Negative nutrient | Block save with min Arabic message. | Required |
| Nutrient above v1 max | Block save with max Arabic message. | Required |
| `unit_amount <= 0` | Reject with min Arabic message. | Required by D-025 |
| `fiber_g > carb_g` | Block save with `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.` | Required |
| Current-catalog exact duplicate | Block save with `هذا الطعام موجود مسبقًا بنفس الوحدة.` | Required by D-025 |
| Duplicate of permanently deleted food | Allow creation because deleted Foods no longer exist in the catalog. | Required by D-025 |
| Delete tapped accidentally | Confirmation dialog opens; cancel/Escape makes no change. | Required by D-025 |
| Confirm food delete | Permanently delete the Food from the catalog; hide from list/search/future Diary selection; do not create archive fields. | Required by D-025 |
| Delete API fails | Food remains visible; no local delete is queued; show write/network/server error. | Required by D-025 |
| Food deleted before edit submit | Reject with `هذا الطعام لم يعد متاحًا. حدّث القائمة وحاول مرة أخرى.` and do not update locally. | Required by D-023/D-025 |
| Food deleted before Diary log submit | Reject with `هذا الطعام لم يعد متاحًا. حدّث القائمة وحاول مرة أخرى.` and do not create a local Diary entry. | Required by D-023/D-025 |
| Food changed before Diary submit and API accepts | Snapshot uses server-confirmed Food values from the successful API response. | Required by D-023 |
| Food changed before Diary submit and API rejects | Show `تم تغيير بيانات الطعام قبل الحفظ. حدّث البيانات وحاول مرة أخرى.` and do not create a local Diary entry. | Required by D-023 |
| Deleted food used by Diary | Historical Diary nutrition remains through snapshot. | Required by D-025 |
| Long food name in list/card | Show up to two lines then truncate with ellipsis; do not overlap actions or cause horizontal scrolling. | Required per D-020 |
| HTML/script in food text | Store/display submitted text as plain text only; never execute or render it as markup. | Required security/a11y baseline |

## Diary

| Scenario | Expected behavior | Status |
|---|---|---|
| No current catalog Foods exist | Disable submit and show `أضف طعامًا أولًا قبل تسجيل الوجبات.` | Required |
| Serving quantity below 0.01 or above 50 | Reject with min/max Arabic error. | Required |
| Gram quantity below 1 or above 5000 | Reject with min/max Arabic error. | Required |
| Quantity blank/non-number | Reject with required/invalid-number Arabic message. | Required |
| Missing or invalid `log_mode` | Reject with invalid-select Arabic message; allowed values are `servings` and `grams`. | Required by D-021 |
| Gram mode selected for Food without unambiguous gram-calculation data | Disable gram mode or show `لا يمكن التسجيل بالجرام لهذا الطعام لأن بيانات الوحدة أو أساس القيم الغذائية غير مكتملة.` | Required |
| Future entry date | Reject with `لا يمكن تسجيل يوميات بتاريخ مستقبلي.` | Required |
| API unreachable during Diary add/edit/delete | Do not create/update/delete locally; do not queue; keep visible input available for retry; show write error. | Required / current code needs alignment |
| Edit food/date/snapshot/log mode | Not allowed in v1 UI or edit payload. | Required by D-010 and D-021 |
| Edit quantity out of range | Reject with field-level Arabic error. | Required |
| Edit gram-mode quantity | Request payload is `{ quantity }`; original `log_mode`, food, date, and per-serving snapshot values remain unchanged. | Required by D-021 |
| Diary entry already deleted before edit/delete completes | Show `هذا السجل لم يعد متاحًا. حدّث اليوميات وحاول مرة أخرى.` and do not update/delete locally. | Required by D-023 |
| Delete Diary entry tapped accidentally | Confirmation dialog opens with food name/date; cancel/Escape makes no change. | Required per D-018 |
| Confirm Diary delete | Delete only after successful API response; daily and weekly totals refresh. | Required per D-018 |
| Delete Diary entry API fails | Entry remains visible, totals unchanged, and no local delete is queued. | Required |
| Duplicate submit during slow Diary add/edit/delete API response | Exactly one API request is sent; submit/confirm stays disabled or pending message is shown. | Required by D-023 |

## Weekly Summary

| Scenario | Expected behavior | Status |
|---|---|---|
| Week start passed as weekday | Normalize to Sunday. | Confirmed |
| No entries in week | Return/display seven days with zero totals. | Confirmed |
| Profile missing | Targets are null or prompt for profile. | Confirmed / UX alignment needed |
| Diary day load fails | Show `تعذر تحميل يوميات هذا اليوم. تحقق من الاتصال وحاول مرة أخرى.` and do not treat cached totals as source of truth. | Required by D-022 |
| Weekly summary load fails | Show `تعذر تحميل ملخص الأسبوع. تحقق من الاتصال وحاول مرة أخرى.` and do not treat cached totals as source of truth. | Required by D-022 |
| Week contains future days | Viewing is allowed; creating future entries remains blocked. | Required |

## Online Network Errors and Future Offline Scope

| Scenario | Expected behavior | Status |
|---|---|---|
| Backend/API unreachable on read | Show exact page-specific read failure copy; do not show cached personal data as authoritative. | Required by D-022 |
| Backend/API unreachable on write | Do not save locally; do not queue; keep the same visible input available for retry until user edits, resets, retries successfully, or navigates away. | Required by D-001/D-013 |
| Server validation rejects write with known fields | Show field errors beside affected fields; do not queue as offline mutation. | Required |
| Server validation rejects write with unknown/form-level error | Show `راجع الحقول المظللة ثم حاول مرة أخرى.`; do not queue as offline mutation. | Required |
| Duplicate submit while request pending | Send exactly one API request; disable action or show `الطلب قيد المعالجة. انتظر حتى يكتمل.` | Required by D-023 |
| Retry after failed request | Retry resubmits the current visible input; no offline/local queued mutation is used. | Required by D-023 |
| Pending mutations exist in current code | Must not be used as v1 behavior. | Future Scope / alignment item |
| Offline page, offline metadata, service-worker API caching, or cached-read fallback exists in current code | Document as Future Scope or implementation alignment; do not treat as v1 acceptance. | Required BA traceability |
| Sync push/pull | Not required for v1. | Future Scope |
| Conflict/concurrent offline edit | Not applicable to v1. | Future Scope |
| Stale cache behavior | Not applicable as v1 source of truth. | Future Scope |

## Mobile, RTL, Accessibility

| Scenario | Expected behavior | Status |
|---|---|---|
| 360px, 390px, 430px, 768px, desktop widths | No horizontal scrolling for standard use. | Required |
| iPhone Safari latest two iOS versions | Layout and forms usable. | Required |
| Android Chrome latest two major versions | Layout and forms usable. | Required |
| Desktop Chrome/Safari latest | Layout and forms usable. | Required |
| Keyboard opens on mobile form | Critical form actions and errors remain reachable. | Required |
| Icon-only buttons | Accessible names. | Required |
| Validation errors | Field-level, Arabic, accessible, focus first invalid visible field. | Required |
| First invalid field inside collapsed section | Open the section, then focus the invalid field. | Required by D-023 |
| Food permanent-delete or Diary delete dialog | Accessible name/description; initial focus on safest action; Escape/cancel closes without changes; focus returns after close. | Required |
| Async status | Loading/success uses `role="status"` or `aria-live="polite"`; errors/destructive statuses use `role="alert"` or equivalent. | Required |
| Mixed Arabic/English food text | Readable, no overlap with actions. | Required |
| Long Arabic/English food names in lists/cards | Two-line ellipsis; details/edit views show full name; no horizontal scrolling. | Required per D-020 |
