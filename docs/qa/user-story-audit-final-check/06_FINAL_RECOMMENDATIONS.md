# Final Recommendations

## Final Recommendation

The BA package is ready for implementation planning and QA test case generation.

Do not perform another BA remediation cycle unless product scope changes. The next useful step is implementation planning from the alignment list, followed by QA test-case authoring from the BA package.

## Top 5 Implementation Alignment Items

1. Remove or disable offline write queues and local mutation behavior for Profile, Food, and Diary writes.
2. Implement Food archive lifecycle with `is_active`, `archived_at`, active filtering, archive confirmation, and no hard delete.
3. Implement Diary D-021 contract: `log_mode`, mode-specific `quantity`, gram mode with `serving_grams`, snapshot `serving_multiplier`, and calculated totals.
4. Align validation and Arabic error/read-failure messages to `04`, `05`, and `06`.
5. Remove or constrain offline/sync UI/API/service-worker/cached-read behavior so it cannot act as v1 source-of-truth behavior.

## Top 5 QA Focus Areas

1. Online-only behavior: failed writes do not save locally, do not queue, and preserve visible input for retry.
2. Food lifecycle: duplicate active key, archive-only delete, archived Food hidden from active lists/Diary selection, old snapshots unchanged.
3. Diary correctness: serving vs gram logging, missing `serving_grams`, future date block, quantity-only edit, delete confirmation, stale entry handling.
4. Arabic UX: validation messages, read-failure copy, API error mapping, RTL mixed text, long food names.
5. Accessibility/mobile: icon accessible names, field error association, first invalid focus, dialog focus/escape/cancel, live regions, required viewports.

## Recommended Sequencing

1. Implementation planning from `docs/ba/11_REQUIREMENTS_GAPS.md` and `docs/qa/user-story-audit-final-check/05_FINAL_TRACEABILITY_AND_IMPLEMENTATION_ALIGNMENT.md`.
2. QA test case generation from `docs/ba/04_FIELD_DICTIONARY.md`, `05_VALIDATION_RULES.md`, `06_ERROR_MESSAGES.md`, `08_NEGATIVE_SCENARIOS.md`, `09_ACCEPTANCE_CRITERIA.md`, and `10_TRACEABILITY_MATRIX.md`.
3. Implementation in slices: online-only cleanup, Food archive/validation, Diary gram/edit/snapshot, UI messages/a11y/mobile, tests.
4. Final implementation QA after code changes.

## Do Not Add Yet

- Offline-first behavior.
- IndexedDB personal data source-of-truth behavior.
- Offline mutation queue or sync push/pull.
- Multi-profile/person switching.
- Profile reset/delete.
- Recipes, barcode scanning, public food database, brand/category/source fields unless scope changes.

## Limitations

- This audit did not run the app or execute tests.
- This audit did not inspect rendered UI screenshots.
- Current code alignment conclusions are based on static code evidence.
- The BA package is ready, but implementation remains materially incomplete against the BA.
