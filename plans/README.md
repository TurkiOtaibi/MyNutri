# مستشار improvement plans

This directory contains the five default implementation plans produced by the `improve` skill's deep, read-only audit on 2026-07-21.

Audit baseline: `a91ba09` (`main`)

The audit did not modify application source. At planning time, `frontend/debug-diary.png` and `skills-lock.json` were already untracked; they are not part of these plans and must not be committed accidentally.

## Execution order

| Order | Plan | Priority | Effort | Risk | Status | Dependencies |
|---:|---|---|---|---|---|---|
| 1 | [Isolate browser query state and account identity](001-isolate-session-query-state.md) | P1 | M | MED | DONE — exact head `7aca71f` passed CI #74 and two clean reviews; PR #21 ready for review | None |
| 1H | [Plan 001 Post-Merge Stabilization — Authoritative Diary Date](001a-authoritative-diary-date-hotfix.md) | P0 | M | MED | DONE — exact head `f188f67` passed CI #82 and two clean reviews; Draft PR #25 remains unmerged | Plan 001 merged; blocks Plan 002 continuation until PR #25 merges and new main CI passes |
| 2 | [Make Diary Snapshot v3 capture atomic with Food writes](002-make-diary-snapshots-atomic.md) | P1 | M | MED | DONE — updated scope at exact head `bc8ce5b1` passed CI #88 (7/7 PostgreSQL) and two clean reviews; PR #22 Ready | None |
| 3 | [Keep admin monitoring GETs strictly read-only](003-keep-admin-gets-read-only.md) | P1 | M | MED | DONE — exact head `fb7747b6` passed CI #92 and two CLEAN reviews; PR #23 Ready | Plans 001 and 002 merged |
| 4 | [Bound and singleflight unknown-`kid` JWKS refreshes](004-bound-jwks-refreshes.md) | P1 | M | MED | DONE — exact head `5390a67f` passed CI #101 and two CLEAN reviews; PR #27 Ready and unmerged | None |
| 5 | [Preserve cut intensity and expose Profile safety decisions](005-complete-profile-cut-safety-ux.md) | P1 | M | MED | TODO — Arabic safety copy approved and frozen in [H03 decision](../docs/product/nutrition-quality-expansion/20_H03_APPROVED_ARABIC_SAFETY_MESSAGES.md) | Product/content approval gate complete; Plans 1–4 merged |

## Dependency notes

The plans have no hard code dependency. Plans 1–4 can be delivered independently. Plan 5 has a non-code prerequisite: the Product Owner and an Arabic content reviewer must freeze the two exact safety strings in a product-owned decision artifact before implementation starts. After that approval, run Plan 5 after Plan 1 when practical so Profile end-to-end tests start from the corrected session-remount behavior. The listed order otherwise addresses the cross-account browser boundary first, then data integrity and authorization semantics, authentication availability, and the user-facing Profile workflow.

## Executor rules

- Execute one plan per branch and pull request. Do not combine these plans unless the reviewer explicitly approves a changed scope.
- Before editing, run the plan's drift command against `a91ba09`. Re-read every in-scope file that changed since the audit and adapt the implementation without weakening the stated invariant.
- Preserve unrelated working-tree changes. Do not add `frontend/debug-diary.png` or `skills-lock.json` merely because they are present.
- Follow each plan's STOP conditions. A STOP condition is a request for a design or product decision, not permission to improvise around it.
- Add tests before or with the implementation, run focused verification first, then the relevant full suite.
- Keep commits conventional and scoped, following recent repository history (for example, `fix(auth): ...` or `fix(diary): ...`).
- Status values are `TODO`, `IN PROGRESS`, `DONE`, `BLOCKED` (with a reason), and `REJECTED` (with a rationale). Update this index only on the branch that implements that plan.

## Why these five

These were selected because repository evidence supports a concrete failure mode, impact is high, the remediation boundary is clear, and the result can be verified deterministically:

1. A root-long-lived React Query client and uncorrelated account request can expose or render the previous browser user's private state after account switching.
2. Diary snapshots read a mutable Food parent and its child rows in separate statements without a shared lock, allowing a concurrent Food edit to create a hybrid snapshot.
3. Admin monitoring GETs call TargetPlan lifecycle advancement and commit another user's plan changes despite the documented read-only authorization contract.
4. Attacker-controlled unknown JWT key IDs can cause repeated synchronous JWKS refreshes; the current library client has no application-level cooldown or singleflight.
5. Profile editing drops a stored 15% or 25% cut preference back to 20%, while the UI suppresses authoritative safety, cap, and warning information already returned by the backend.

## Findings intentionally not promoted into the default five

The following validated opportunities remain useful backlog candidates, but were ranked below the five plans above:

- Make Diary date authority use Riyadh/backend time instead of the browser timezone.
- Reject protocol-relative and normalized cross-origin login return paths.
- Paginate Food autocomplete and bound recent-food history instead of downloading full collections.
- Protect dirty Profile and Food drafts from background query refreshes and all navigation paths.
- Correct PWA document/RSC caching and offline fallback behavior.
- Stabilize the Diary modal focus trap across local state changes.
- Calculate week progress dots from each day's own target.
- Handle password-reset provider errors without misleading success state.
- Consolidate the large, repeated global stylesheet with visual-regression coverage.
- Verify production security headers before deciding whether Next.js must supply them.

## Findings considered and rejected as defects

- Browser bearer-token use is the approved Supabase email/password architecture; no Service Role credential was found in frontend code.
- `AdminGuard` is not treated as an authorization boundary; the backend still enforces admin and ownership checks.
- The service worker does not currently cache personal API responses. Its confirmed issue is shell/RSC handling, not API-data persistence.
- Serving-based nutrition calculation is display-only; persisted Diary truth remains backend-owned.
- Nullable optional nutrients preserve `null`; no confirmed null-to-zero mutation was found.
- Direct gram/ml Diary logging is explicitly deferred by the product documents.
- Food trait/group suggestions remain user-reviewed assistance rather than authoritative calculation input.
- No dangerous HTML, `eval`, or browser-storage credential sink was found.
- `npm audit --omit=dev --audit-level=high` reported no production dependency vulnerabilities at the audit baseline.

## Baseline verification notes

- Backend audit baseline: `python -m ruff check .` passed; `python -m pytest -q` reported 122 passed and 8 skipped.
- Frontend production dependency audit reported zero vulnerabilities.
- Frontend typecheck was not certified locally because the existing `node_modules` was incomplete. Each frontend executor must run `npm ci` before treating typecheck/build results as evidence.
- PostgreSQL-specific concurrency behavior cannot be certified by SQLite. Plans 2 and 3 identify the disposable database gate explicitly.
