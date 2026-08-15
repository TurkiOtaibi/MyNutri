# Documentation authority map

Use this page before changing myNutri. Documents lower in the list cannot override documents above them. When two approved current artifacts conflict, stop and ask the Product Owner to reconcile them; do not choose the more convenient rule.

## 1. Current product and architecture authority

- [V2 scope and decisions](product/v2/01_V2_SCOPE_AND_DECISIONS.md) defines the authenticated, multi-principal product boundary.
- [Authentication and role model](product/v2/02_AUTH_AND_ROLE_MODEL.md), [authorization matrix](product/v2/03_AUTHORIZATION_MATRIX.md), and [shared Food catalog](product/v2/04_SHARED_FOOD_CATALOG.md) govern identity, permissions, and catalog ownership.
- [Food Taxonomy V2](product/v2/05_FOOD_TAXONOMY_V2.md) and [data migration and cutover](product/v2/06_DATA_MIGRATION_AND_CUTOVER.md) govern the V2 schema transition.
- [Nutrition decision register and scope freeze](product/nutrition-quality-expansion/PRODUCT_DECISION_REGISTER_AND_SCOPE_FREEZE_v1.1.md) and the [Wave 1 freeze index](product/nutrition-quality-expansion/12_WAVE1_FREEZE_INDEX.md) govern the frozen nutrition-quality expansion. Follow their own approval and supersession links. Other files in that family are decision history, review, or approval evidence unless one of these controlling indexes incorporates them.
- [BA product decisions](ba/13_PRODUCT_DECISIONS.md) are authoritative only where a later approved V2 or nutrition artifact has not superseded them. The rest of the [BA package](ba/) is supporting requirements and traceability evidence; validate each claim against the approved decisions above because older files retain superseded single-user and offline assumptions.

## 2. Operations and release authority

- [V2 release and rollback runbook](product/v2/07_RELEASE_AND_ROLLBACK_RUNBOOK.md) governs release gates, deployment order, environment boundaries, smoke checks, and rollback.
- Repository configuration, lockfiles, migrations, and CI are executable authority for the revision being changed. If they disagree with prose, stop and reconcile the documentation instead of silently bypassing the executable gate.

## 3. Evidence and supporting records

- [Implementation reports](implementation/) record what was built and verified; they are historical evidence, not permission to change current behavior.
- [QA and audit reports](qa/) record historical coverage, gaps, and verdicts; later approved decisions take precedence.
- [UI/UX reports and evidence](ui-ux/) document historical reviewed presentation and accessibility behavior; confirm current acceptance against newer approved artifacts.
- [Foods analysis](FOODS_PAGE_ANALYSIS.md), [Foods features](FOODS_PAGE_FEATURES.md), and [Foods user stories](FOODS_PAGE_USER_STORIES.md) are supporting historical feature records. Resolve conflicts through the authorities above.

## 4. Historical archives — never implementation authority

- [Superseded system plan](1-SYSTEM-PLAN.md)
- [Superseded architecture](2-ARCHITECTURE-SERVICES.md)
- [Superseded Claude Code prompts](CLAUDE_CODE_PROMPTS.md)
- [Superseded historical decision register](product/nutrition-quality-expansion/02_SUPERSEDED_HISTORICAL_DECISIONS.md)

Historical material exists for traceability. Never copy its single-user, role-free, offline-first, Dexie, or sync assumptions into current work.

## Conflict escalation

1. Identify the exact conflicting passages and their approval/version status.
2. Stop implementation that depends on the conflict.
3. Ask the Product Owner for a recorded decision.
4. Update or supersede the losing artifact before resuming implementation.

Every new authoritative document must be linked here. Every superseded document must show a first-screen caution banner that points back here.
