# Current field dictionary and validation summary

Status: supporting requirements. Backend schemas and database constraints are executable authority.

## Principal

| Field | Required | Rule |
|---|---:|---|
| `id` | Yes | Durable UUID ownership key |
| `auth_user_id` | Historical compatibility | Historical identity link only; no admission authority; scrubbed by local deletion |
| `retired_auth_user_id` | Historical compatibility | Historical unique retired identity; never admitted or relinked |
| `identity_requested_at` | Historical compatibility | Historical provisioning metadata; no current external creation lease |
| `sessions_valid_after` | Historical compatibility | Historical JWT cutoff column; current admission uses internal session revocation/expiry |
| `username` / `normalized_username` | New internal accounts | Immutable 3–32 ASCII letters/digits/`.`/`_`/`-`; lowercase normalized uniqueness; scrubbed on deletion so a new Principal may reuse it (BR-USM-022/023/025/036/043; #112 and 27 October PO decision) |
| `last_login_at` | No | Actual successful internal login time; nullable for never-login/legacy accounts; shown as «آخر دخول» (BR-USM-013; #112) |
| `is_locked` (Admin response) | Yes | Derived normal-user internal lock flag, not lifecycle status; false for Admin; «مقفل» badge/filter (BR-USM-006/014; #112) |
| `email` | No | Unique case-insensitively when present; maximum 320; erased on deleted tombstone |
| `display_name` | No | Maximum 120; erased on deleted tombstone |
| `role` | Yes | `user` or `admin`; never accepted from browser metadata or account-management input; partial unique index permits at most one Admin |
| `status` | Yes | CURRENT lifecycle: `provisioning`, `active`, `disabled`, `deleting`, `deleted`; internal lock behavior is separate, stored as `failed_login_count` and `locked_at` in #110 (27 October 2026) (17 October 2026; BR-AUT-011, BR-USM-006/014) |
| creation idempotency key | For Admin creation | Internal creation stores it atomically with the active Principal; a matching replay returns that account. Legacy provisioning creates no new identity and cannot resume provider creation (BR-USM-025/049; #112) |

These account-lifecycle fields are implemented in the forward lifecycle revision;
Production activation remains a separate release action.
Admin creates a normal user with immutable username, display name, and an initial password (#112; BR-USM-022/023/025/036).
Admin may edit display name, reset internal passwords while revoking every session, and enable/disable. Legacy-only reset is refused; username, legacy email and role
cannot be changed through the product. Raw passwords are input-only and never stored,
logged, or returned; internal accounts store only a scrypt hash (#110; 27 October 2026; BR-AUT-001/017, BR-USM-030/033). Unknown and non-active legacy identities receive the
existing `401 INVALID_CREDENTIAL`. `deleting` remains locked out and Admin-visible
as incomplete until a retry reaches the scrubbed `deleted` tombstone. A
`provisioning` account may be deleted through the same local purge and tombstone operation. Global
Foods retain creator/updater Principal IDs; their attribution is not displayed to any role, including a deleted-user label. (17 October 2026 FOD decision, BR-FOD-021; already implemented, unchanged by issue #100.)
The irreversible-delete confirmation requires the Admin to type the target
user's username; only a legacy account without username uses the retained email confirmation. A mismatch prevents submission (#112; BR-USM-038/042).

## CURRENT fields versus APPROVED TARGET

CURRENT in #113: authentication uses only internal username/password and opaque bearer sessions. The browser persists only the session token in localStorage; passwords remain in memory and no auth cookies are used. Initial-password change and Profile password change are current; forgotten passwords go to the Admin. Supabase Auth/JWT admission, provider creation/reset/deletion, reconciliation and runtime Auth configuration are removed. Legacy-only accounts cannot log in; retained identity columns and the existing legacy deletion confirmation are historical compatibility, not an authentication path; #114 clears them only on selected legacy-user tombstones. New users are created atomically by immutable username. The 28 October 2026 Product Owner decision supersedes the earlier all-test-account deletion/Admin recreation target. CURRENT repository migration #114 selects only `role='user' AND password_hash IS NULL AND status <> 'deleted'`, purges their private data and retains scrubbed tombstones. The Admin and every internal-credential account retain all data; already-deleted Principals and every Food row/attribution ID remain unchanged. Production execution remains an APPROVED TARGET requiring the release procedure in V2 06/07; repository implementation does not prove deployment or authorize further actions. Authority: final 17 October 2026 AUT/USM decisions; 27 October #110/#112 decisions; issues #110–#113 and #128 (BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-022/030/033/036/043).

CURRENT #113 removes Supabase Auth; internal login has no email, MFA or self-service recovery. Legacy stored email/display and deletion confirmation remain compatibility behavior; #114 clears stored fields only for selected legacy users. Only initial Admin-set passwords require a forced change; reset passwords allow immediate login. Five consecutive failures lock an account, successful login resets the counter, Admin reset alone unlocks a user and signs out every device, and the single Admin unlocks automatically after 30 minutes. Own-password change requires the correct current password and signs out other devices. Backend minimum length is 8. (17 October 2026 final AUT/USM decisions; BR-AUT-004/007–012, BR-PRF-024–026, BR-USM-023/030/033.)

## CURRENT login/Profile and Admin username copy

Strings below follow the final BRD requirements approved **17 October 2026** and the [27 October deletion-copy decision](https://github.com/TurkiOtaibi/MyNutri/issues/112#issuecomment-6437936388). Login/session/Profile strings are CURRENT in #111 and Admin username-management strings in #112. Legacy accounts without usernames retain clearly marked email display/confirmation fallback where applicable before the selective #114 purge. Older «فتح القفل», «تم فتح قفل الحساب.» and «نسيت كلمة المرور؟ تواصل مع المشرف.» remain superseded (BR-AUT-003/011, BR-USM-030).

| Context | CURRENT | APPROVED TARGET exact copy | BRD authority (17 October 2026) |
|---|---|---|---|
| Login / account identity | اسم المستخدم | اسم المستخدم | BR-AUT-001, BR-USM-022/054 |
| Required username | أدخل اسم المستخدم. | أدخل اسم المستخدم. | BR-AUT-004 |
| Admin search | ابحث بالاسم أو اسم المستخدم... | ابحث بالاسم أو اسم المستخدم... | BR-USM-005 |
| Immutable login identifier | لا يمكن تغيير اسم المستخدم بعد إنشاء الحساب. | لا يمكن تغيير اسم المستخدم بعد إنشاء الحساب. | BR-USM-023/036 |
| Duplicate identity | اسم المستخدم هذا مستخدم بالفعل. | اسم المستخدم هذا مستخدم بالفعل. | BR-USM-025 |
| Delete confirmation identifier | اكتب اسم المستخدم لتأكيد الحذف النهائي. | اكتب اسم المستخدم لتأكيد الحذف النهائي. | BR-USM-038; Product Owner, 27 October 2026, issue #112 comment |
| Delete mismatch | اسم المستخدم المدخل لا يطابق هذا الحساب. | اسم المستخدم المدخل لا يطابق هذا الحساب. | BR-USM-042 |
| No account / forgotten password | ليس لديك حساب أو نسيت كلمة المرور؟ تواصل مع المشرف. | ليس لديك حساب أو نسيت كلمة المرور؟ تواصل مع المشرف. | BR-AUT-003/012 |
| Password hint | استخدم 8 أحرف على الأقل. | استخدم 8 أحرف على الأقل. | BR-AUT-007, BR-PRF-024, BR-USM-023 |
| Backend minimum-length failure | كلمة المرور قصيرة. استخدم 8 أحرف على الأقل. | كلمة المرور قصيرة. استخدم 8 أحرف على الأقل. | BR-AUT-004, BR-PRF-025, BR-USM-023 |
| General login failure | تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى. | تعذر إكمال الطلب. تحقق من البيانات وحاول مرة أخرى. | BR-AUT-005 |
| Connection failure | تعذر الاتصال بالخادم. حاول مرة أخرى. | تعذر الاتصال بالخادم. حاول مرة أخرى. | BR-AUT-005 |
| User lock | تم قفل الحساب بعد 5 محاولات دخول فاشلة. تواصل مع المشرف لفتحه. | تم قفل الحساب بعد 5 محاولات دخول فاشلة. تواصل مع المشرف لفتحه. | BR-AUT-011 |
| Admin lock | تم قفل الحساب بعد 5 محاولات دخول فاشلة. حاول مرة أخرى بعد 30 دقيقة. | تم قفل الحساب بعد 5 محاولات دخول فاشلة. حاول مرة أخرى بعد 30 دقيقة. | BR-AUT-011 |
| Locked badge/filter | مقفل | مقفل | BR-USM-006/014 |
| Disabled admission | حسابك موقوف. تواصل مع المشرف. | حسابك موقوف. تواصل مع المشرف. | BR-AUT-010/015 |
| Expired session | انتهت جلستك. سجّل الدخول مرة أخرى. | انتهت جلستك. سجّل الدخول مرة أخرى. | BR-AUT-015 |
| Initial / own change title | تغيير كلمة المرور | تغيير كلمة المرور | BR-AUT-007, BR-PRF-024 |
| Current password | كلمة المرور الحالية | كلمة المرور الحالية | BR-PRF-024/026 |
| New password | كلمة المرور الجديدة | كلمة المرور الجديدة | BR-AUT-007, BR-PRF-024, BR-USM-030 |
| Initial save | حفظ كلمة المرور | حفظ كلمة المرور | BR-AUT-007 |
| Own change action | تغيير كلمة المرور | تغيير كلمة المرور | BR-PRF-024 |
| Own change success | تم تغيير كلمة المرور. | تم تغيير كلمة المرور. | BR-PRF-025 |
| Current-password mismatch | كلمة المرور الحالية غير صحيحة. | كلمة المرور الحالية غير صحيحة. | BR-PRF-025/026 |
| Admin reset warning | سيخرج المستخدم من كل أجهزته. | سيخرج المستخدم من كل أجهزته. | BR-USM-030 |

## CURRENT sex correction — issue #109

Only an Admin can correct another active/disabled user with a saved Profile; all
other private fields remain read-only (17 October 2026; BR-PRF-006, BR-USM-032/061).

| Action | Approved copy | Authority |
|---|---|---|
| Correction | تصحيح الجنس | BR-USM-032 |
| Warning | تصحيح الجنس يغيّر حساب الأهداف وتقييم نتائج التحاليل. | BR-USM-032 |
| Success / failure | تم حفظ تغييرات المستخدم. / تعذر حفظ تغييرات المستخدم. حاول مرة أخرى. | BR-USM-034 |

## CURRENT account-management Arabic copy


The retained email-based account-management copy below belongs to the CURRENT implementation; the target replacements are in the adjacent table. This is not evidence of production activation. (17 October 2026 AUT/USM decisions; BR-AUT-001, BR-USM-022/023/025/038/042; issue #100.)

| Context | Approved exact Arabic string |
|---|---|
| Account-management heading | إدارة المستخدمين |
| Create action | إضافة مستخدم |
| Display-name field | الاسم المعروض |
| Initial-password field | كلمة المرور الأولية |
| Provisioning status | قيد الإنشاء |
| Active status | نشط |
| Disabled status | معطّل |
| Creation retry action | إعادة محاولة الإنشاء |
| Create submit | إنشاء المستخدم |
| Edit action | تعديل المستخدم |
| Save edit | حفظ التغييرات |
| Password-reset action | إعادة تعيين كلمة المرور |
| New-password field | كلمة المرور الجديدة |
| Enable action | تفعيل المستخدم |
| Disable action | تعطيل المستخدم |
| Permanent-delete action | حذف المستخدم نهائيًا |
| Irreversible-delete dialog title | حذف المستخدم نهائيًا؟ |
| Irreversible-delete dialog body | سيُحذف حساب هذا المستخدم وجميع بياناته الخاصة نهائيًا. لا يمكن التراجع عن هذا الإجراء. |
| Delete confirmation instruction | اكتب البريد الإلكتروني للمستخدم لتأكيد الحذف النهائي. |
| Delete confirmation mismatch | اسم المستخدم المدخل لا يطابق هذا الحساب. |
| Incomplete-deletion status | حذف غير مكتمل |
| Incomplete-deletion explanation (17 October 2026 final USM requirements, BR-USM-040; already implemented) | تعذر إكمال حذف المستخدم. لا يستطيع الدخول الآن، ويمكنك إعادة المحاولة. |
| Deletion retry action | إعادة محاولة الحذف |
| Retired Food-attribution label; not displayed to any role (17 October 2026, BR-FOD-021) | مستخدم محذوف |
| Admin self-mutation rejection | لا يمكن تعطيل حساب المشرف أو حذفه أو تغيير دوره. |
| Second-Admin rejection | لا يمكن إنشاء مشرف آخر. |
| Duplicate-email rejection | اسم المستخدم هذا مستخدم بالفعل. |
| Incomplete-create explanation | تعذر إكمال إنشاء المستخدم. أعد المحاولة. |
| Edit failure | تعذر حفظ تغييرات المستخدم. حاول مرة أخرى. |
| Enable/disable failure | تعذر تحديث حالة المستخدم. حاول مرة أخرى. |
| Network/unreachable server (any action) | تعذر الاتصال بالخادم. حاول مرة أخرى. |
| Password-reset failure | تعذر إعادة تعيين كلمة المرور. حاول مرة أخرى. |
| Weak/rejected password (create or reset) | كلمة المرور غير مقبولة. اختر كلمة مرور أقوى وحاول مرة أخرى. |
| Create success | تم إنشاء المستخدم. |
| Edit success | تم حفظ تغييرات المستخدم. |
| Password-reset success | تمت إعادة تعيين كلمة المرور. |
| Enable/disable success | تم تحديث حالة المستخدم. |
| Permanent-delete success | تم حذف المستخدم نهائيًا. |

The following 3 strings were added with Product Owner approval on 2026-10-02
for the merged Admin Users list (issues #91 and #93).

| Context | Approved exact Arabic string |
|---|---|
| Password hint (create, reset and creation retry) | استخدم 8 أحرف على الأقل. |
| Email cannot be changed note (create) | لا يمكن تغيير اسم المستخدم بعد إنشاء الحساب. |
| User details section-links label (accessible name) | أقسام الصفحة |

## Profile input

| Field | Required | Current rule |
|---|---:|---|
| `sex` | Yes | `male` or `female`; owner-locked after first successful save, with the sole Admin correction exception (17 October 2026; BR-PRF-006, BR-USM-032/061; #109) |
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
- Duplicate identity is normalized name and normalized brand plus nutrition/default-unit basis and amount. Both name and brand are case-folded, trimmed, and have repeated whitespace collapsed; absent or blank brand normalizes to an empty string. Different brands may share a name and serving definition, with the BR-FOD-029 name warning; true duplicates remain rejected, per the Product Owner decision of 25 October 2026 implementing BR-FOD-029.
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
PATCH requires date/value/unit and `expected_updated_at` from the result shown when
the edit dialog opened. A changed version returns 409 before any replacement;
DELETE physically removes the owned result.
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
| `LAB_RESULT_CHANGED` | تغيّرت هذه النتيجة منذ فتحها. راجع قيمها الحالية قبل تعديلها مجددًا. |
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


## CURRENT internal authentication fields (#110)

Username identity is 3–32 ASCII English letters, digits, `.`, `_`, or `-`, with a unique lowercase normalized value. Passwords use standard-library scrypt with a random per-password salt; sessions use opaque random bearer tokens in the Authorization header, store only SHA-256 token hashes on the backend, and use no cookies; the browser persists only the raw session token in localStorage (#111). The Product Owner approved the 30-day sliding inactivity expiry for #111 on 27 October 2026. Existing accounts retain null internal credentials unless the explicitly authorized existing-Admin attach command is run. These details replace the former “to be decided in issue #110” placeholders. (Product Owner decisions of 17 and 27 October 2026; issue #110 and its comments; BR-AUT-001/004/005/007/008/010/011/017, BR-PRF-024–026, BR-USM-030/033.)

`Principal` adds nullable `username`, unique `normalized_username`, secret `password_hash`, `locked_at` and `last_login_at`; `must_change_password` defaults false and `failed_login_count` defaults zero. `AuthSession` stores only the token hash and Principal/creation/last-use/expiry/revocation fields. The API never returns the stored password hash or session token hash. The raw session token is returned only on successful issuance. Governed failure/change/lock texts above are used by the backend and login/Profile browser UI (#111); username-based Admin UI remains pending #112.
