# Open Questions

## Product Owner

1. Should `docs/ba` become the canonical BA source of truth, replacing root-level analysis files?
2. Is multi-person/profile support in v1, or should the current single-profile implementation remain the v1 scope?
3. Should used foods be archived/inactive while unused foods are hard deleted, or should all food deletes become archive/inactive?
4. Should archived foods participate in duplicate-food checks?
5. What exact rule defines an exact duplicate food: name + serving label + serving grams only, or more fields?
6. Is gram-based diary logging required before serious personal use, or can serving-only logging remain v1?
7. Should future diary dates be allowed?
8. Should future birth dates be blocked?
9. Should profile deletion/reset be supported?
10. Should diary entry edit be exposed in the UI since the backend supports it?

## Engineering

11. What field should represent food lifecycle: `is_active`, `archived_at`, `deleted_at`, or another design?
12. Should `serving_grams` be renamed to `serving_weight_g` in product/API language, or kept as-is?
13. Should duplicate prevention be implemented as service validation only or also a normalized database constraint?
14. What max values should be enforced for food nutrients, profile height/weight, and diary quantity?
15. Should test coverage include both SQLite test DB and PostgreSQL-specific migration behavior?
16. How should existing IndexedDB/sync code be removed, disabled, or hidden for v1 so no offline write behavior remains?
17. Should the optional installable shell keep a service worker for shell assets only, or should the service worker be removed entirely for v1?
18. What exact API-unreachable error handling pattern should be shared by Profile, Foods, Diary, and Week views?

## UX / UI / Accessibility

19. What are the exact Arabic field-level validation messages?
20. Should delete confirmation be a dialog, inline confirmation, or undo snackbar?
21. Should diary delete also require confirmation?
22. How should empty/loading/error/no-results/connection-error states differ on Profile, Foods, and Diary?
23. Should fixed install or connection-error widgets reserve safe-area padding on iPhone/mobile web?
24. What accessible names should be used for icon-only buttons?
25. Should validation focus move to the first invalid field?
26. Should long food names truncate, wrap, or show tooltip/detail expansion?

## QA

27. Should QA generate tests from current implemented behavior or from planned root Foods decisions when they conflict?
28. Which browsers/devices are in scope for mobile/responsive acceptance?
29. Which online network-error cases must be automated: API down, 401, 404, 422, timeout, and generic 5xx?
30. Should existing sync tests be kept as future-scope regression tests or removed from v1 QA runs?

## Resolved by Product Decision

The following questions are resolved for v1:

- Offline-first is removed from v1.
- Frontend must not queue local mutations after network or validation failure.
- Sync conflicts, rejected sync operations, pending sync states, and stale cache behavior are Future Scope.
- Local cached personal nutrition data must not be treated as v1 source of truth.
- QA should replace offline/sync v1 expectations with online network-error tests.

## Recommended Next Step

1. Product review of this BA package.
2. Resolve questions 2, 3, 4, 6, 10, 16, 17, 18, and 19 before implementation planning.
3. Run the QA user-story coverage auditor against `docs/ba`.
4. Convert approved stories into implementation tasks.
