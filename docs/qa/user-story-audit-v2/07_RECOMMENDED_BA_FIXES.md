# Recommended BA Fixes

These are requirements-documentation fixes only. They are not implementation tasks.

## Priority Fixes

### BA-FIX-001 - Add Gram-Mode Diary Contract Decision

Severity: High
Related features: F-030, F-031, F-034
Related stories: `US-DIARY-GRAM-001`, `US-DIARY-EDIT-001`, `US-DIARY-INTEGRITY-001`

Add a decision that answers:
- What request payload is used for serving mode?
- What request payload is used for gram mode?
- Does the persisted entry store `log_mode`?
- Does it store `quantity`, `grams`, or both?
- Are calculated per-entry totals stored or recomputed from snapshot plus quantity?
- What exactly can be edited for gram-mode entries?

Suggested acceptance criteria:
- Given serving mode is selected
  When a diary entry is created
  Then the payload uses the serving-mode quantity contract and the snapshot freezes per-serving nutrition.
- Given gram mode is selected
  When a diary entry is created
  Then the payload uses the gram-mode quantity contract and the snapshot freezes calculated gram-mode nutrition.
- Given a gram-mode entry is edited
  When quantity changes
  Then only the gram quantity can change and food/date/snapshot identity remains unchanged.

### BA-FIX-002 - Add Exact Read Failure Arabic Copy

Severity: High
Related features: F-036, F-038, F-039
Related stories: `US-NETWORK-READ-001`, `US-ERROR-MAPPING-001`

Add exact Arabic copy for read failures in `06_ERROR_MESSAGES.md`.

The read-failure message must not say changes were not saved. It should say data could not be loaded or refreshed.

Suggested acceptance criteria:
- Given Profile, Foods, Diary, or Week data fails to load
  When the failure is due to timeout, network, or 5xx
  Then the read-failure Arabic message is shown and no cached personal data is treated as current.

### BA-FIX-003 - Tighten Ambiguous Acceptance Wording

Severity: Medium
Related stories: `US-A11Y-001`, `US-PROFILE-HAPPY-001`, `US-ERROR-MAPPING-001`

Replace or qualify:
- "where practical"
- "where possible"
- "D-013 applies"
- "matching Arabic message"
- "after a short delay"

Suggested approach:
Keep references to shared docs, but add minimum observable behavior in each critical story.

### BA-FIX-004 - Add Stale Entity and Duplicate Submit Criteria

Severity: Medium
Related features: Food edit/archive, Diary create/edit/delete, online writes

Add criteria for:
- Repeated taps while a write is pending.
- Food archived/unavailable after edit form opens.
- Diary entry already deleted before delete/edit response.
- 404 refresh-required behavior for stale item actions.

### BA-FIX-005 - Add Offline Page/Metadata Alignment Evidence

Severity: Medium
Related features: F-004, F-005, F-036, F-043, F-044

Add current-code evidence to requirements gaps:
- `frontend/app/offline/page.tsx`
- `frontend/app/layout.tsx` metadata description
- Profile/Food/Diary cached read fallbacks in page query functions

Reason:
These are current implementation alignment issues under online-only v1. They are not BA contradictions, but they should be visible before implementation planning.

### BA-FIX-006 - Add Health/Config Traceability Decision

Severity: Low
Related features: F-008, F-009

Either:
- Add technical stories for health/config, or
- Mark these as technical requirements that do not require user stories.

### BA-FIX-007 - Add Test Data Matrix

Severity: Medium
Related feature: F-042
Related story: `US-QA-001`

Add a QA-oriented matrix listing boundary values:
- Profile min/max and just-outside values.
- Food nutrient min/max and just-outside values.
- Diary serving/gram min/max and just-outside values.
- Duplicate normalization examples.
- Arabic/English/mixed long food names.
- API error examples: 401, 404, 422, timeout, 5xx.
