# Foods v1 Automation Mapping

Source: `FOODS_TEST_CASES_REGENERATED.csv` (153 cases)
Execution: `FOODS-AUTO-001` against local PostgreSQL `mynutri_dev`
Artifacts: `frontend/test-results/` and `frontend/playwright-report/`

| Test case ID | Automated | Playwright test file | Playwright test name | Status | Reason if Manual Required | Notes |
|---|---|---|---|---|---|---|
| FOOD-TC-001 | Yes | frontend/e2e/foods/navigation.spec.ts | [FOOD-TC-001] @p0 navigates list, add, details, and edit routes | Passed |  |  |
| FOOD-TC-002 | Yes | frontend/e2e/foods/navigation.spec.ts | [FOOD-TC-002] @p0 add page has save/cancel/back and no delete | Passed |  |  |
| FOOD-TC-003 | Yes | frontend/e2e/foods/navigation.spec.ts | [FOOD-TC-003] @p0 list page does not contain the Add Food form | Passed |  |  |
| FOOD-TC-004 | Yes | frontend/e2e/foods/navigation.spec.ts | [FOOD-TC-004] @p1 edit reuses grouped Add Food structure | Passed |  |  |
| FOOD-TC-005 | Partial | frontend/e2e/foods/navigation.spec.ts | [FOOD-TC-005] @p1 @mobile standalone pages fit a 360px viewport | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-006 | Yes | frontend/e2e/foods/navigation.spec.ts | [FOOD-TC-006] @p1 cancel returns without saving | Passed |  |  |
| FOOD-TC-007 | Yes | frontend/e2e/foods/navigation.spec.ts | [FOOD-TC-007] @p0 unauthorized Foods read exposes no catalog data | Passed |  |  |
| FOOD-TC-008 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-008] @p0 desktop table shows approved columns | Passed |  |  |
| FOOD-TC-009 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-009] @p0 @mobile mobile uses cards with core Food values | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-010 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-010] @p1 main list omits optional micronutrients | Passed |  |  |
| FOOD-TC-011 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-011] @p1 @mobile long names clamp to two lines without overflow | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-012 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-012] @p0 list has no archive/status UI | Passed |  |  |
| FOOD-TC-013 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-013] @p0 hard-deleted Food is absent from list | Passed |  |  |
| FOOD-TC-014 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-014] @p0 saved Food exposes View, Edit, and Delete actions | Passed |  |  |
| FOOD-TC-015 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-015] @p0 current Food appears in future Diary selection | Passed |  |  |
| FOOD-TC-016 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-016] @p1 mixed Arabic/English list text remains RTL-readable | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-017 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-017] @p0 search finds matching current Food | Passed |  |  |
| FOOD-TC-018 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-018] @p0 search finds matching current Food | Passed |  |  |
| FOOD-TC-019 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-019] @p1 search finds matching current Food | Passed |  |  |
| FOOD-TC-020 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-020] @p0 search finds matching current Food | Passed |  |  |
| FOOD-TC-021 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-021] @p1 search trims whitespace | Passed |  |  |
| FOOD-TC-022 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-022] @p0 no-results state is shown | Passed |  |  |
| FOOD-TC-023 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-023] @p1 clearing search restores full catalog | Passed |  |  |
| FOOD-TC-024 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-024] @p0 deleted Food is absent from search | Passed |  |  |
| FOOD-TC-025 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-025] @p0 search read failure shows Arabic error | Passed |  |  |
| FOOD-TC-026 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-026] @p1 @mobile search remains usable at 360px | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-027 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-027] @p0 loading state is visible while Foods request is pending | Passed |  |  |
| FOOD-TC-028 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-028] @p0 empty catalog state links to Add Food | Passed |  |  |
| FOOD-TC-029 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-029] @p1 no-results differs from empty catalog state | Passed |  |  |
| FOOD-TC-030 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-030][FOOD-TC-031] @p0 @p1 read failure clears after fresh retry | Passed |  |  |
| FOOD-TC-031 | Yes | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-030][FOOD-TC-031] @p0 @p1 read failure clears after fresh retry | Passed |  |  |
| FOOD-TC-032 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-032][FOOD-TC-131] @p0 detail read failure shows exact Arabic error | Passed |  |  |
| FOOD-TC-033 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-033] @p0 edit read failure prevents editable form | Passed |  |  |
| FOOD-TC-034 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-034] @p1 @mobile state messages do not overflow | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-035 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-035] @p1 @a11y read failure is exposed as an alert | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-036 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-036] @p0 creates a valid per_100g Food | Passed |  |  |
| FOOD-TC-037 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-037] @p0 creates a valid per_100ml Food | Passed |  |  |
| FOOD-TC-038 | Partial | frontend/e2e/foods/create.spec.ts | [FOOD-TC-038] @p1 form has the approved grouped sections | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-039 | Partial | frontend/e2e/foods/create.spec.ts | [FOOD-TC-039] @p1 optional nutrients are collapsed by default | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-040 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-040] @p0 blank optional nutrients do not block save | Passed |  |  |
| FOOD-TC-041 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-041] @p0 duplicate click submits one create request | Passed |  |  |
| FOOD-TC-042 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-042] @p0 network failure preserves the draft and creates no Food | Passed |  |  |
| FOOD-TC-043 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-043] @p0 structured API field error maps to the Food name | Passed |  |  |
| FOOD-TC-044 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-044] @p1 server failure preserves entered data | Passed |  |  |
| FOOD-TC-045 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-045] @p0 unauthorized create is not treated as saved | Passed |  |  |
| FOOD-TC-046 | Partial | frontend/e2e/foods/create.spec.ts | [FOOD-TC-046] @p1 @mobile Add Food is usable at 390px | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-047 | Yes | frontend/e2e/foods/create.spec.ts | [FOOD-TC-047] @p0 source of truth is per-100 and no legacy serving fields appear | Passed |  |  |
| FOOD-TC-048 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-048] @p0 required field shows associated Arabic error | Passed |  |  |
| FOOD-TC-049 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-049] @p0 API rejects missing nutrition_basis with Arabic field error | Passed |  |  |
| FOOD-TC-050 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-050] @p0 required field shows associated Arabic error | Passed |  |  |
| FOOD-TC-051 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-051] @p0 required field shows associated Arabic error | Passed |  |  |
| FOOD-TC-052 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-052] @p0 required field shows associated Arabic error | Passed |  |  |
| FOOD-TC-053 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-053] @p0 required field shows associated Arabic error | Passed |  |  |
| FOOD-TC-054 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-054] @p0 API rejects missing default_unit_type with Arabic field error | Passed |  |  |
| FOOD-TC-055 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-055] @p0 required field shows associated Arabic error | Passed |  |  |
| FOOD-TC-056 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-056] @p0 API rejects missing unit_basis with Arabic field error | Passed |  |  |
| FOOD-TC-057 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-057] @p1 accepts an Arabic Food name | Passed |  |  |
| FOOD-TC-058 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-058] @p0 trims and collapses Food name whitespace | Passed |  |  |
| FOOD-TC-059 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-059] @p1 enforces Food name max 120 | Failed |  | BUG-FOODS-AUTO-002: automated assertion failed; see run report and retained artifacts. |
| FOOD-TC-060 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-060] @p0 script-like text never executes | Passed |  |  |
| FOOD-TC-061 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-061] @p0 accepts calories zero and max boundaries | Passed |  |  |
| FOOD-TC-062 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-062] @p0 rejects calories negative, malformed, and above max | Passed |  |  |
| FOOD-TC-063 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-063] @p0 accepts protein_g zero and max boundaries | Passed |  |  |
| FOOD-TC-064 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-064] @p0 rejects protein_g negative, malformed, and above max | Passed |  |  |
| FOOD-TC-065 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-065] @p0 accepts carb_g zero and max boundaries | Passed |  |  |
| FOOD-TC-066 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-066] @p0 rejects carb_g negative, malformed, and above max | Passed |  |  |
| FOOD-TC-067 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-067] @p0 accepts fat_g zero and max boundaries | Passed |  |  |
| FOOD-TC-068 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-068] @p0 rejects fat_g negative, malformed, and above max | Passed |  |  |
| FOOD-TC-069 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-069] @p0 rejects tampered nutrition_basis | Passed |  |  |
| FOOD-TC-070 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-070] @p0 rejects tampered default_unit_type | Passed |  |  |
| FOOD-TC-071 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-071] @p0 validates unit amount boundaries and decimal | Passed |  |  |
| FOOD-TC-072 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-072] @p0 rejects tampered unit_basis | Passed |  |  |
| FOOD-TC-073 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-073] @p2 validates brand language and max length | Failed |  | BUG-FOODS-AUTO-003: automated assertion failed; see run report and retained artifacts. |
| FOOD-TC-074 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-074] @p2 validates category language and max length | Failed |  | BUG-FOODS-AUTO-004: automated assertion failed; see run report and retained artifacts. |
| FOOD-TC-075 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-075] @p2 blank optional text is allowed and HTML stays inert | Passed |  |  |
| FOOD-TC-076 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-076] @p1 validates optional fiber_g blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-077 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-077] @p1 validates optional sugar_g blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-078 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-078] @p1 validates optional added_sugar_g blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-079 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-079] @p1 validates optional saturated_fat_g blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-080 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-080] @p1 validates optional trans_fat_g blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-081 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-081] @p1 validates optional cholesterol_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-082 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-082] @p1 validates optional sodium_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-083 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-083] @p1 validates optional potassium_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-084 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-084] @p1 validates optional calcium_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-085 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-085] @p1 validates optional iron_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-086 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-086] @p1 validates optional magnesium_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-087 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-087] @p1 validates optional zinc_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-088 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-088] @p1 validates optional vitamin_d_mcg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-089 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-089] @p1 validates optional vitamin_b12_mcg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-090 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-090] @p1 validates optional vitamin_c_mg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-091 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-091] @p1 validates optional vitamin_a_mcg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-092 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-092] @p1 validates optional folate_mcg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-093 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-093] @p1 validates optional vitamin_k_mcg blank, zero, max, negative, and above max | Passed |  |  |
| FOOD-TC-094 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-094] @p0 rejects fiber greater than carbs | Passed |  |  |
| FOOD-TC-095 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-095] @p0 rejects added sugar greater than total sugar | Passed |  |  |
| FOOD-TC-096 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-096] @p1 permits added sugar when total sugar is blank | Passed |  |  |
| FOOD-TC-097 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-097] @p0 rejects saturated fat greater than fat | Passed |  |  |
| FOOD-TC-098 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-098] @p0 rejects trans fat greater than fat | Passed |  |  |
| FOOD-TC-099 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-099] @p0 rejects saturated plus trans fat greater than total fat | Passed |  |  |
| FOOD-TC-100 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-100] @p1 invalid optional nutrient opens section and associates error | Passed |  |  |
| FOOD-TC-101 | Yes | frontend/e2e/foods/duplicate.spec.ts | [FOOD-TC-101] @p0 blocks exact duplicate and shows Arabic error | Passed |  |  |
| FOOD-TC-102 | Yes | frontend/e2e/foods/duplicate.spec.ts | [FOOD-TC-102] @p0 normalizes spaces and English case for duplicate key | Passed |  |  |
| FOOD-TC-103 | Yes | frontend/e2e/foods/duplicate.spec.ts | [FOOD-TC-103] @p1 brand and category do not change duplicate identity | Passed |  |  |
| FOOD-TC-104 | Yes | frontend/e2e/foods/duplicate.spec.ts | [FOOD-TC-104] @p0 deleted Food can be created again | Passed |  |  |
| FOOD-TC-105 | Yes | frontend/e2e/foods/duplicate.spec.ts | [FOOD-TC-105] @p0 edit cannot collide with another Food | Passed |  |  |
| FOOD-TC-106 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-106] @p0 edit form loads current values | Passed |  |  |
| FOOD-TC-107 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-107] @p0 valid edit saves and appears in details | Passed |  |  |
| FOOD-TC-108 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-108] @p1 unchanged edit remains valid | Passed |  |  |
| FOOD-TC-109 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-109] @p0 invalid edit is blocked and persisted Food is unchanged | Passed |  |  |
| FOOD-TC-110 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-110] @p0 failed edit preserves input | Passed |  |  |
| FOOD-TC-111 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-111] @p0 unauthorized edit is rejected | Passed |  |  |
| FOOD-TC-112 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-112] @p0 stale deleted Food cannot be edited | Passed |  |  |
| FOOD-TC-113 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-113] @p1 conflict response preserves edit draft | Passed |  |  |
| FOOD-TC-114 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-114] @p1 cancel edit persists no changes | Passed |  |  |
| FOOD-TC-115 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-115] @p0 old Diary snapshot does not change after Food edit | Passed |  |  |
| FOOD-TC-116 | Partial | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-116] @p1 @mobile edit supports RTL mixed text without overflow | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-117 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-117] @p1 cross-field-invalid edit is blocked | Passed |  |  |
| FOOD-TC-118 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-118] @p0 confirmation dialog shows Food name and permanent wording | Passed |  |  |
| FOOD-TC-119 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-119] @p0 cancel closes dialog and keeps Food | Passed |  |  |
| FOOD-TC-120 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-120] @p0 confirm permanently deletes Food | Passed |  |  |
| FOOD-TC-121 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-121] @p0 deleted Food disappears from future Diary selection | Passed |  |  |
| FOOD-TC-122 | Yes | frontend/e2e/foods/snapshot.spec.ts | [FOOD-TC-122] @p0 historical Diary entry survives Food hard delete | Passed |  |  |
| FOOD-TC-123 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-123] @p0 failed delete keeps Food and queues nothing | Passed |  |  |
| FOOD-TC-124 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-124] @p1 repeated confirm sends one delete request | Failed |  | BUG-FOODS-AUTO-001: automated assertion failed; see run report and retained artifacts. |
| FOOD-TC-125 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-125] @p0 delete uses no archive/inactive state | Passed |  |  |
| FOOD-TC-126 | Partial | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-126] @p0 @a11y dialog supports focus, Escape, and focus restoration | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-127 | Yes | frontend/e2e/foods/delete.spec.ts | [FOOD-TC-127] @p0 unauthorized delete leaves Food unchanged | Passed |  |  |
| FOOD-TC-128 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-128] @p0 details show full core, optional, and metadata values | Passed |  |  |
| FOOD-TC-129 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-129] @p1 details handle blank optional nutrients without errors | Passed |  |  |
| FOOD-TC-130 | Partial | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-130] @p1 long full name is visible on details | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-131 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-032][FOOD-TC-131] @p0 detail read failure shows exact Arabic error | Passed |  |  |
| FOOD-TC-132 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-132] @p0 deleted detail route shows not-found/read error | Passed |  |  |
| FOOD-TC-133 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-133] @p1 details expose Edit and Delete actions | Passed |  |  |
| FOOD-TC-134 | Yes | frontend/e2e/foods/details-edit.spec.ts | [FOOD-TC-134] @p0 unauthorized detail exposes no Food data | Passed |  |  |
| FOOD-TC-135 | Partial | frontend/e2e/foods/mobile-rtl-a11y.spec.ts | [FOOD-TC-135] @p1 @a11y field errors are associated with invalid inputs | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-136 | Partial | frontend/e2e/foods/mobile-rtl-a11y.spec.ts | [FOOD-TC-136] @p1 @a11y icon actions have contextual accessible names | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-137 | Yes | frontend/e2e/foods/online-only.spec.ts | [FOOD-TC-137] @p0 API read failure does not use local personal data | Passed |  |  |
| FOOD-TC-138 | Yes | frontend/e2e/foods/online-only.spec.ts | [FOOD-TC-138] @p0 failed write is not saved or queued offline | Passed |  |  |
| FOOD-TC-139 | Partial | frontend/e2e/foods/mobile-rtl-a11y.spec.ts | [FOOD-TC-139] @p1 @mobile required viewport matrix has no horizontal page overflow | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-140 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-140] @p2 renders a 200-Food catalog without broken layout | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-141 | Partial | frontend/e2e/foods/list-search-states.spec.ts | [FOOD-TC-141] @p1 unsupported archive/sort/filter controls are absent | Manual Required | Automated DOM/API/viewport assertions ran; real-device visual, browser-matrix, or assistive-technology confirmation remains manual. | Automated portion passed. |
| FOOD-TC-142 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-142] @p1 sugar_g is total sugar and legacy field is not user-facing | Passed |  |  |
| FOOD-TC-143 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-143] @p1 accepts decimal calories | Passed |  |  |
| FOOD-TC-144 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-144] @p1 accepts decimal gram nutrients | Passed |  |  |
| FOOD-TC-145 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-145] @p1 accepts decimal minerals | Passed |  |  |
| FOOD-TC-146 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-146] @p1 accepts decimal vitamins | Passed |  |  |
| FOOD-TC-147 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-147] @p2 brand accepts Arabic, English, mixed text, and punctuation | Passed |  |  |
| FOOD-TC-148 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-148] @p2 category accepts Arabic, English, mixed text, and punctuation | Passed |  |  |
| FOOD-TC-149 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-149] @p2 validates notes language and max length | Failed |  | BUG-FOODS-AUTO-005: automated assertion failed; see run report and retained artifacts. |
| FOOD-TC-150 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-150] @p2 validates data_source language and max length | Failed |  | BUG-FOODS-AUTO-006: automated assertion failed; see run report and retained artifacts. |
| FOOD-TC-151 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-151] @p0 rejects tampered nutrition_basis | Passed |  |  |
| FOOD-TC-152 | Yes | frontend/e2e/foods/optional-nutrients.spec.ts | [FOOD-TC-152] @p1 structured optional nutrient errors identify the field | Passed |  |  |
| FOOD-TC-153 | Yes | frontend/e2e/foods/validation.spec.ts | [FOOD-TC-153] @p0 whitespace-only Food name is rejected with Arabic error | Passed |  |  |

## Totals

- CSV cases mapped: 153
- Fully automated: 135
- Partially automated: 18
- Manual-only/unmapped: 0
- CSV case outcomes: 129 Passed, 6 Failed, 18 Manual Required
