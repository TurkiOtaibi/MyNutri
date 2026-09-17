# myNutri documentation authority

This repository deliberately keeps a small current documentation set. Git history,
Alembic migrations, pull requests, CI runs, executable tests, and visual-regression
baselines are the historical record; deleted reports and screenshots are not current
implementation authority.

## Read first

1. [V2 scope and decisions](product/v2/01_V2_SCOPE_AND_DECISIONS.md)
2. [Current architecture and data model](product/v2/11_CURRENT_ARCHITECTURE_AND_DATA_MODEL.md)
3. [Authentication and role model](product/v2/02_AUTH_AND_ROLE_MODEL.md)
4. [Authorization matrix](product/v2/03_AUTHORIZATION_MATRIX.md)
5. [Shared Food catalog](product/v2/04_SHARED_FOOD_CATALOG.md)
6. [Target Plan date-effective model](product/v2/09_TARGET_PLAN_DATE_EFFECTIVE_MODEL.md)
7. [Nutrition rules, safety, and Registry](product/v2/12_NUTRITION_RULES_SAFETY_AND_REGISTRY.md)

## Domain and operations authority

- [Food taxonomy](product/v2/05_FOOD_TAXONOMY_V2.md) owns stable taxonomy keys and Arabic labels.
- [Data migration and cutover](product/v2/06_DATA_MIGRATION_AND_CUTOVER.md) owns the live migration topology and schema-transition boundaries.
- [Release and rollback runbook](product/v2/07_RELEASE_AND_ROLLBACK_RUNBOOK.md) owns deployment, verification, and recovery procedure.
- The generated OpenAPI document, Backend schemas, Alembic chain, tests, and CI are executable contracts. When prose and an executable contract disagree, stop and resolve the drift; do not silently choose one.

## Supporting requirements

- [Executive summary](ba/00_EXECUTIVE_SUMMARY.md)
- [Field dictionary](ba/04_FIELD_DICTIONARY.md)
- [User stories and acceptance](ba/07_USER_STORIES.md)
- [Traceability matrix](ba/10_TRACEABILITY_MATRIX.md)

The BA package summarizes current requirements. Product and architecture authority
remains in the V2 documents above.

## Retired architecture

Day Logging Status, the Target Plan lifecycle, semantic Nutrition versions, legacy
Target snapshots/Profile fallback, Food Archive/Restore, a separate Admin Food UI,
the Sync shell, `Food*V3` public names, dual-shape `GET /foods`, uncategorized
compatibility, and `/admin/foods` are absent. Historical descriptions are available
through Git history only and must not be treated as current behavior.

## Governance rule

Only the 17 Markdown files listed by `docs/tools/validate_authoritative_docs.py`
belong in the current documentation estate. Run that validator after any documentation,
route, entity, contract, or migration-head change.
