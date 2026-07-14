# Error Messages

myNutri is Arabic-first. Exact Arabic copy below is required before implementation and QA test case generation.

## Field-Level Messages

| Scenario | Arabic message | Placement | Accessibility |
|---|---|---|---|
| Required field | `ظ‡ط°ط§ ط§ظ„ط­ظ‚ظ„ ظ…ط·ظ„ظˆط¨.` | Under field | Associate with field using `aria-describedby`; set `aria-invalid=true`. |
| Invalid number | `ط£ط¯ط®ظ„ ط±ظ‚ظ…ظ‹ط§ طµط­ظٹط­ظ‹ط§.` | Under field | Associate with field. |
| Below minimum | `ط§ظ„ظ‚ظٹظ…ط© ط£ظ‚ظ„ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.` | Under field | Associate with field. |
| Above maximum | `ط§ظ„ظ‚ظٹظ…ط© ط£ط¹ظ„ظ‰ ظ…ظ† ط§ظ„ط­ط¯ ط§ظ„ظ…ط³ظ…ظˆط­.` | Under field | Associate with field. |
| Invalid date | `ط£ط¯ط®ظ„ طھط§ط±ظٹط®ظ‹ط§ طµط­ظٹط­ظ‹ط§.` | Under field | Associate with field. |
| Future birth date | `طھط§ط±ظٹط® ط§ظ„ظ…ظٹظ„ط§ط¯ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† ظٹظƒظˆظ† ظپظٹ ط§ظ„ظ…ط³طھظ‚ط¨ظ„.` | Under birth date | Associate with field. |
| Age below 10 | `ط§ظ„ط¹ظ…ط± ظٹط¬ط¨ ط£ظ† ظٹظƒظˆظ† 10 ط³ظ†ظˆط§طھ ط£ظˆ ط£ظƒط«ط±.` | Under birth date | Associate with field. |
| Age above 100 | `ط§ظ„ط¹ظ…ط± ظٹط¬ط¨ ط£ظ„ط§ ظٹطھط¬ط§ظˆط² 100 ط³ظ†ط©.` | Under birth date | Associate with field. |
| Future diary date | `ظ„ط§ ظٹظ…ظƒظ† طھط³ط¬ظٹظ„ ظٹظˆظ…ظٹط§طھ ط¨طھط§ط±ظٹط® ظ…ط³طھظ‚ط¨ظ„ظٹ.` | Under diary date | Associate with field. |
| Duplicate current catalog Food | `هذا الطعام موجود مسبقًا بنفس الوحدة.` | Under food name or form-level near food identity fields | Associate with `name`, `nutrition_basis`, `default_unit_type`, `unit_amount`, and `unit_basis`. |
| Fiber greater than carbs | `ط§ظ„ط£ظ„ظٹط§ظپ ظ„ط§ ظٹظ…ظƒظ† ط£ظ† طھظƒظˆظ† ط£ظƒط¨ط± ظ…ظ† ط§ظ„ظƒط±ط¨ظˆظ‡ظٹط¯ط±ط§طھ.` | Under fiber field | Associate with fiber field. |
| Gram mode unavailable for selected Food | `لا يمكن التسجيل بالجرام لهذا الطعام لأن بيانات الوحدة أو أساس القيم الغذائية غير مكتملة.` | Under gram mode/quantity | Associate with gram mode control and the selected Food. |
| Invalid select option | `ط§ط®طھط± ظ‚ظٹظ…ط© طµط­ظٹط­ط©.` | Under select | Associate with field. |
| Optional nutrient negative value | `القيمة الغذائية الإضافية لا يمكن أن تكون أقل من 0.` | Under the optional nutrient field | Associate with the invalid optional nutrient field. |
| Optional nutrient above maximum | `القيمة الغذائية الإضافية أعلى من الحد المسموح.` | Under the optional nutrient field | Associate with the invalid optional nutrient field. |
| D-026 fiber greater than carbs | `الألياف لا يمكن أن تكون أكبر من الكربوهيدرات.` | Under fiber field | Associate with fiber field. |
| Added sugar greater than sugar | `السكر المضاف لا يمكن أن يكون أكبر من إجمالي السكر.` | Under added sugar field | Associate with added sugar field. |
| Saturated fat greater than fat | `الدهون المشبعة لا يمكن أن تكون أكبر من إجمالي الدهون.` | Under saturated fat field | Associate with saturated fat field. |
| Trans fat greater than fat | `الدهون المتحولة لا يمكن أن تكون أكبر من إجمالي الدهون.` | Under trans fat field | Associate with trans fat field. |
| Saturated plus trans fat greater than total fat | `مجموع الدهون المشبعة والمتحولة لا يمكن أن يكون أكبر من إجمالي الدهون.` | Under trans fat field or form-level near fat fields | Associate with saturated fat, trans fat, and fat fields. |

## Form-Level and API Messages

| Scenario | Arabic message | Placement | Behavior |
|---|---|---|---|
| Network/API unreachable during write | `طھط¹ط°ط± ط§ظ„ط§طھطµط§ظ„ ط¨ط§ظ„ط®ط§ط¯ظ…. ظ„ظ… ظٹطھظ… ط­ظپط¸ ط§ظ„طھط؛ظٹظٹط±ط§طھ.` | Form/page error region | Preserve visible input in the same form state until the user edits it, resets it, retries successfully, or navigates away; do not save locally; do not queue. |
| Unauthorized / 401 | `طھط¹ط°ط± ط§ظ„ظˆطµظˆظ„. طھط­ظ‚ظ‚ ظ…ظ† طµظ„ط§ط­ظٹط© ط§ظ„ط¯ط®ظˆظ„.` | Page/form error region | Do not show stale data as saved. |
| Not found / 404 | `ط§ظ„ط¹ظ†طµط± ط؛ظٹط± ظ…ظˆط¬ظˆط¯. ط­ط¯ظ‘ط« ط§ظ„طµظپط­ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Page/form error region | Prompt refresh or return to list. |
| Validation / 422 | `ط±ط§ط¬ط¹ ط§ظ„ط­ظ‚ظˆظ„ ط§ظ„ظ…ط¸ظ„ظ„ط© ط«ظ… ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Form-level plus field errors | Map known field details to those fields; unknown or form-level details use this form-level message. |
| Server error / 5xx | `ط­ط¯ط« ط®ط·ط£ ظپظٹ ط§ظ„ط®ط§ط¯ظ…. ط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Page/form error region | Preserve visible input in the same form state for write forms. |
| Stale food | `ظ‡ط°ط§ ط§ظ„ط·ط¹ط§ظ… ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظ‚ط§ط¦ظ…ط© ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Form/page error region | Do not save locally; refresh current catalog Foods before retry. |
| Food changed before diary submit | `طھظ… طھط؛ظٹظٹط± ط¨ظٹط§ظ†ط§طھ ط§ظ„ط·ط¹ط§ظ… ظ‚ط¨ظ„ ط§ظ„ط­ظپط¸. ط­ط¯ظ‘ط« ط§ظ„ط¨ظٹط§ظ†ط§طھ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Form/page error region | Do not create a diary entry unless the API returns a successful snapshot from current server data. |
| Stale diary entry | `ظ‡ط°ط§ ط§ظ„ط³ط¬ظ„ ظ„ظ… ظٹط¹ط¯ ظ…طھط§ط­ظ‹ط§. ط­ط¯ظ‘ط« ط§ظ„ظٹظˆظ…ظٹط§طھ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Form/page error region | Do not update/delete locally; refresh the Diary day before retry. |
| Duplicate submit while pending | `ط§ظ„ط·ظ„ط¨ ظ‚ظٹط¯ ط§ظ„ظ…ط¹ط§ظ„ط¬ط©. ط§ظ†طھط¸ط± ط­طھظ‰ ظٹظƒطھظ…ظ„.` | Form/action area | Disable the submit/confirm action while pending and send one API request only. |
| Save success | `طھظ… ط§ظ„ط­ظپط¸.` | Non-blocking status | Only after successful API response. |
| Food permanent delete success | `تم حذف الطعام نهائيًا.` | Non-blocking status | Only after successful API response. |
| Diary entry created | `طھظ… طھط³ط¬ظٹظ„ ط§ظ„ظˆط¬ط¨ط©.` | Non-blocking status | Only after successful API response. |
| Diary entry updated | `طھظ… طھط­ط¯ظٹط« ط§ظ„ظƒظ…ظٹط©.` | Non-blocking status | Only after successful API response. |
| Diary entry deleted | `طھظ… ط­ط°ظپ ط§ظ„ط³ط¬ظ„.` | Non-blocking status | Only after successful API response. |

Forbidden v1 messages:
- `طھظ… ط­ظپط¸ ط§ظ„طھط¹ط¯ظٹظ„ ظ…ط­ظ„ظٹظ‹ط§ ظˆط³ظٹط²ط§ظ…ظ† ط¹ظ†ط¯ ط§ظ„ط§طھطµط§ظ„.`
- `طھظ… ط­ظپط¸ ط§ظ„ط·ط¹ط§ظ… ظ…ط­ظ„ظٹظ‹ط§ ظˆط³ظٹط²ط§ظ…ظ† ط¹ظ†ط¯ ط§ظ„ط§طھطµط§ظ„.`
- `طھظ… طھط³ط¬ظٹظ„ ط§ظ„ظˆط¬ط¨ط© ظ…ط­ظ„ظٹظ‹ط§ ظˆط³ظٹطھظ… ط±ظپط¹ظ‡ط§ ط¹ظ†ط¯ ط§ظ„ط§طھطµط§ظ„.`
- Any message that implies offline write queue or later sync.

## Read Failure Messages

| Read area | Arabic message | Placement | Behavior |
|---|---|---|---|
| General API/network read failure | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ط¨ظٹط§ظ†ط§طھ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Page error region | Do not display cached personal nutrition data as current. |
| Profile load failure | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ط§ظ„ظ…ظ„ظپ ط§ظ„ط´ط®طµظٹ. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Profile page error region | Keep existing visible form data only if it was already loaded in the active session; do not treat cached data as fresh. |
| Foods list load failure | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ‚ط§ط¦ظ…ط© ط§ظ„ط£ط·ط¹ظ…ط©. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Foods page error region | Show retry path and do not replace the failed read with cached source-of-truth data. |
| Food detail load failure | `طھط¹ط°ط± طھط­ظ…ظٹظ„ طھظپط§طµظٹظ„ ط§ظ„ط·ط¹ط§ظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Food detail/edit error region | Do not allow edit submit until fresh detail data is loaded. |
| Diary day load failure | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظٹظˆظ…ظٹط§طھ ظ‡ط°ط§ ط§ظ„ظٹظˆظ…. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Diary day error region | Do not show cached day totals as current. |
| Weekly summary load failure | `طھط¹ط°ط± طھط­ظ…ظٹظ„ ظ…ظ„ط®طµ ط§ظ„ط£ط³ط¨ظˆط¹. طھط­ظ‚ظ‚ ظ…ظ† ط§ظ„ط§طھطµط§ظ„ ظˆط­ط§ظˆظ„ ظ…ط±ط© ط£ط®ط±ظ‰.` | Weekly summary error region | Do not show cached weekly totals as current. |

## Food Delete Confirmation Dialog - D-025

This section controls v1 Food delete copy and supersedes older Food archive confirmation copy.

| Element | Arabic copy |
|---|---|
| Dialog title | `ط­ط°ظپ ط§ظ„ط·ط¹ط§ظ…` |
| Body | `ط³ظٹطھظ… ط­ط°ظپ {food_name} ظ†ظ‡ط§ط¦ظٹظ‹ط§ ظ…ظ† ظƒطھط§ظ„ظˆط¬ ط§ظ„ط£ط·ط¹ظ…ط©. ط³طھط¨ظ‚ظ‰ ط§ظ„ظٹظˆظ…ظٹط§طھ ط§ظ„ط³ط§ط¨ظ‚ط© ظƒظ…ط§ ظ‡ظٹ ظ„ط£ظ†ظ‡ط§ طھط³طھط®ط¯ظ… ظ†ط³ط®ط© ط؛ط°ط§ط¦ظٹط© ظ…ط­ظپظˆط¸ط©.` |
| Confirm button | `ط­ط°ظپ ط§ظ„ط·ط¹ط§ظ…` |
| Cancel button | `ط¥ظ„ط؛ط§ط،` |
| Success message | `طھظ… ط­ط°ظپ ط§ظ„ط·ط¹ط§ظ….` |

Dialog behavior:
- Shows the Food name.
- Clearly states deletion is permanent.
- Explains existing Diary entries remain unchanged because they use saved nutrition snapshots.
- Cancel or Escape makes no changes.
- Confirm deletes permanently only after successful API response.
- Failed delete does not hide the Food locally and does not queue a mutation.
- Dialog is keyboard accessible.
- Focus returns to a safe place after closing.
- No typing Food name is required in v1.

## Food Labels and Sections - D-024/D-025

| UI element | English | Arabic |
|---|---|---|
| Default unit | `Default unit` | `ط§ظ„ظˆط­ط¯ط© ط§ظ„ط§ظپطھط±ط§ط¶ظٹط©` |
| Unit amount | `Unit amount` | `ظ…ظ‚ط¯ط§ط± ط§ظ„ظˆط­ط¯ط©` |
| Unit basis | `Unit basis` | `ط£ط³ط§ط³ ط§ظ„ظˆط­ط¯ط©` |
| Optional nutrients section | `Optional nutrients` | `ط§ظ„ظ‚ظٹظ… ط§ظ„ط؛ط°ط§ط¦ظٹط© ط§ظ„ط¥ط¶ط§ظپظٹط©` |

## Legacy Delete / Archive Confirmation Dialog

The legacy archive copy below is retained for traceability only. It is superseded by D-025 and must not be used for v1 Food deletion.

| Element | Arabic copy |
|---|---|
| Dialog title | `ط£ط±ط´ظپط© ط§ظ„ط·ط¹ط§ظ…` |
| Body | `ط³ظٹطھظ… ط£ط±ط´ظپط© {food_name} ظˆط¥ط®ظپط§ط¤ظ‡ ظ…ظ† ط§ظ„ط§ط®طھظٹط§ط± ظ„ط§ط­ظ‚ظ‹ط§. ط³طھط¨ظ‚ظ‰ ط§ظ„ظٹظˆظ…ظٹط§طھ ط§ظ„ط³ط§ط¨ظ‚ط© ظƒظ…ط§ ظ‡ظٹ.` |
| Confirm button | `ط£ط±ط´ظپ ط§ظ„ط·ط¹ط§ظ…` |
| Cancel button | `ط¥ظ„ط؛ط§ط،` |

Dialog behavior:
- Shows food name.
- Explains archive and hidden-from-future-selection outcome.
- Cancel makes no changes.
- Legacy superseded by D-025: current v1 confirms permanent delete after successful API response.
- Dialog is keyboard accessible.
- Escape/cancel closes without change.
- Focus returns to a safe place after closing.
- No typing food name required in v1.

## Diary Delete Confirmation Dialog

| Element | Arabic copy |
|---|---|
| Dialog title | `ط­ط°ظپ ط³ط¬ظ„ ط§ظ„ظˆط¬ط¨ط©` |
| Body | `ط³ظٹطھظ… ط­ط°ظپ {food_name} ظ…ظ† ظٹظˆظ… {entry_date}. ط³ظٹطھظ… طھط­ط¯ظٹط« ط¥ط¬ظ…ط§ظ„ظٹ ط§ظ„ظٹظˆظ… ظˆط§ظ„ط£ط³ط¨ظˆط¹ ط¨ط¹ط¯ ط§ظ„ط­ط°ظپ.` |
| Confirm button | `ط­ط°ظپ ط§ظ„ط³ط¬ظ„` |
| Cancel button | `ط¥ظ„ط؛ط§ط،` |

Dialog behavior:
- Shows food name and entry date.
- Cancel makes no changes.
- Confirm deletes only after successful API response.
- Daily and weekly totals refresh after successful deletion.
- Dialog is keyboard accessible.
- Escape/cancel closes without change.
- Focus returns to a safe place after closing.
- No offline/local delete is allowed.

## Empty, Loading, and No-Results Messages

| State | Arabic message |
|---|---|
| Loading foods | `ط¬ط§ط±ظٹ طھط­ظ…ظٹظ„ ط§ظ„ط£ط·ط¹ظ…ط©.` |
| Empty food catalog | `ظ„ط§ طھظˆط¬ط¯ ط£ط·ط¹ظ…ط© ط¨ط¹ط¯. ط£ط¶ظپ ط£ظˆظ„ ط·ط¹ط§ظ… ظ„ظ„ط¨ط¯ط،.` |
| Food search no results | `ظ„ط§ طھظˆط¬ط¯ ظ†طھط§ط¦ط¬ ظ…ط·ط§ط¨ظ‚ط© ظ„ظ„ط¨ط­ط«.` |
| Loading diary | `ط¬ط§ط±ظٹ طھط­ظ…ظٹظ„ ط§ظ„ظٹظˆظ…ظٹط§طھ.` |
| Empty diary day | `ظ„ط§ طھظˆط¬ط¯ ظˆط¬ط¨ط§طھ ظ…ط³ط¬ظ„ط© ظ„ظ‡ط°ط§ ط§ظ„ظٹظˆظ….` |
| No foods for diary | `ط£ط¶ظپ ط·ط¹ط§ظ…ظ‹ط§ ط£ظˆظ„ظ‹ط§ ظ‚ط¨ظ„ طھط³ط¬ظٹظ„ ط§ظ„ظˆط¬ط¨ط§طھ.` |
| Loading profile | `ط¬ط§ط±ظٹ طھط­ظ…ظٹظ„ ط§ظ„ظ…ظ„ظپ.` |
| Missing profile | `ط£ط¯ط®ظ„ ط¨ظٹط§ظ†ط§طھظƒ ظ„ط­ط³ط§ط¨ ط§ظ„ط£ظ‡ط¯ط§ظپ ط§ظ„ظٹظˆظ…ظٹط©.` |

## Error Timing

| Error type | Trigger |
|---|---|
| Required fields | On submit, and on blur after the field has been touched. |
| Numeric min/max | On submit, and on blur/change after the field has a parseable numeric value. |
| Duplicate food | On save after normalized duplicate check. |
| Fiber greater than carbs | On submit and when both fields are available. |
| Gram mode unavailable | When gram mode is selected for a Food whose nutrition basis/default-unit data cannot support gram calculation. |
| API errors | After API response/failure. |
| Stale item | After API returns stale/not-found state for the submitted Food or Diary entry. |
| Duplicate submit | Immediately after a write request enters pending state. |
