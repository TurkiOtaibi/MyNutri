"""Validate myNutri's compact current documentation authority."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


APPROVED_MARKDOWN = frozenset(
    {
        "AGENTS.md",
        "README.md",
        "docs/README.md",
        "docs/product/v2/01_V2_SCOPE_AND_DECISIONS.md",
        "docs/product/v2/02_AUTH_AND_ROLE_MODEL.md",
        "docs/product/v2/03_AUTHORIZATION_MATRIX.md",
        "docs/product/v2/04_SHARED_FOOD_CATALOG.md",
        "docs/product/v2/05_FOOD_TAXONOMY_V2.md",
        "docs/product/v2/06_DATA_MIGRATION_AND_CUTOVER.md",
        "docs/product/v2/07_RELEASE_AND_ROLLBACK_RUNBOOK.md",
        "docs/product/v2/09_TARGET_PLAN_DATE_EFFECTIVE_MODEL.md",
        "docs/product/v2/11_CURRENT_ARCHITECTURE_AND_DATA_MODEL.md",
        "docs/product/v2/12_NUTRITION_RULES_SAFETY_AND_REGISTRY.md",
        "docs/ba/00_EXECUTIVE_SUMMARY.md",
        "docs/ba/04_FIELD_DICTIONARY.md",
        "docs/ba/07_USER_STORIES.md",
        "docs/ba/10_TRACEABILITY_MATRIX.md",
    }
)
EXPECTED_MODELS = frozenset(
    {"Principal", "Profile", "TargetPlan", "IdempotencyRecord", "LabResult", "Food", "DiaryEntry"}
)
EXPECTED_FOOD_OPERATIONS = {
    "/foods": {"get", "post"},
    "/foods/picker": {"get"},
    "/foods/{food_id}": {"get", "put", "delete"},
}
EXPECTED_TARGET_PLAN_OPERATIONS = {
    "/target-plans": {"get", "post"},
    "/target-plans/current": {"get"},
}
EXPECTED_LABS_OPERATIONS = {
    "/labs/catalog": {"get"},
    "/labs": {"get"},
    "/labs/tests/{test_key}": {"get"},
    "/labs/results": {"post"},
    "/labs/results/{result_id}": {"patch", "delete"},
    "/admin/users/{principal_id}/labs": {"get"},
    "/admin/users/{principal_id}/labs/tests/{test_key}": {"get"},
}
VALIDATOR_PATH = "docs/tools/validate_authoritative_docs.py"
EXPECTED_ALEMBIC_HEAD = "e8b7a42f6c31"
EXPECTED_LABS_KEYS = frozenset("""
hba1c total_cholesterol ldl_c hdl_c triglycerides wbc rbc hemoglobin hematocrit
platelets mcv mch mchc rdw neutrophils_abs neutrophils_pct lymphocytes_abs
lymphocytes_pct monocytes_abs monocytes_pct eosinophils_abs eosinophils_pct
basophils_abs basophils_pct mpv ferritin serum_iron tibc transferrin_saturation
vitamin_d_25oh vitamin_b12 vitamin_b6_plp zinc creatinine bun uric_acid sodium
potassium chloride bicarbonate calcium_total corrected_calcium magnesium alt ast
alp total_bilirubin albumin tsh free_t4 free_t3
""".split())
SPECIALIST_MESSAGE = (
    "لا يمكن حفظ هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، "
    "فاستشر أخصائي تغذية قبل اعتماده."
)
VERY_LOW_MESSAGE = (
    "لا يمكن حفظ هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن "
    "المعتمد في النظام."
)
FOOD_DELETE_MESSAGE = (
    "سيتم حذف هذا الطعام نهائيًا، كما سيتم حذف جميع سجلات اليوميات المرتبطة به لجميع "
    "المستخدمين. لا يمكن التراجع عن هذا الإجراء."
)

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ASSIGNMENT_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:`)?"
    r"((?:[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PRIVATE_KEY|API_KEY|SERVICE_ROLE_KEY))"
    r"|DATABASE_URL|PGPASSWORD)"
    r"(?:`)?\s*[:=]\s*([^\s#]+)"
)
SAFE_VALUE_RE = re.compile(
    r"^(?:$|<[^>]+>|\$\{[^}]+\}|your[-_].*|example.*|placeholder.*|redacted|\*+)$",
    re.IGNORECASE,
)
REVISION_RE = re.compile(
    r'^revision(?:\s*:\s*str)?\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)
DOWN_REVISION_RE = re.compile(
    r'^down_revision(?:\s*:\s*str\s*\|\s*None)?\s*=\s*(?:["\']([^"\']+)["\']|None)',
    re.MULTILINE,
)


@dataclass(frozen=True)
class Results:
    issues: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.issues


def _repo_files(root: Path) -> set[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }
    return {item.decode("utf-8") for item in completed.stdout.split(b"\0") if item}


def _link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0]


def _markdown_checks(root: Path, files: set[str], issues: list[str]) -> None:
    markdown = {name for name in files if name.lower().endswith(".md")}
    missing = sorted(APPROVED_MARKDOWN - markdown)
    extra = sorted(markdown - APPROVED_MARKDOWN)
    if missing:
        issues.append(f"approved Markdown missing: {', '.join(missing)}")
    if extra:
        issues.append(f"unapproved Markdown present: {', '.join(extra)}")

    approved_docs_estate = {
        name for name in APPROVED_MARKDOWN if name.startswith("docs/")
    } | {VALIDATOR_PATH}
    docs_estate = {name for name in files if name.startswith("docs/")}
    if VALIDATOR_PATH not in docs_estate:
        issues.append(f"documentation validator missing: {VALIDATOR_PATH}")
    unexpected_docs = sorted(docs_estate - approved_docs_estate)
    if unexpected_docs:
        issues.append(
            f"unapproved documentation artifact present: {', '.join(unexpected_docs)}"
        )

    evidence = sorted(
        name
        for name in files
        if name.startswith("docs/") and name.lower().endswith((".png", ".csv"))
    )
    if evidence:
        issues.append(f"documentation PNG/CSV evidence remains: {', '.join(evidence)}")

    mojibake = ("\ufffd", "ط§", "طھ", "ظ„", "ظٹ", "ظ…")
    for relative_name in sorted(APPROVED_MARKDOWN & markdown):
        source = root / relative_name
        text = source.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = _link_target(raw_target)
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith(("#", "mailto:")):
                continue
            destination = (source.parent / unquote(parsed.path)).resolve()
            try:
                destination.relative_to(root.resolve())
            except ValueError:
                issues.append(f"{relative_name}: link escapes repository: {target}")
                continue
            if not destination.exists():
                issues.append(f"{relative_name}: broken link: {target}")

        for match in ASSIGNMENT_RE.finditer(text):
            value = match.group(2).strip("`\"'")
            if not SAFE_VALUE_RE.fullmatch(value):
                line = text.count("\n", 0, match.start()) + 1
                issues.append(
                    f"{relative_name}:{line}: assigned value for {match.group(1)}"
                )
        for marker in mojibake:
            if marker in text:
                issues.append(f"{relative_name}: possible mojibake marker {marker!r}")


def _authority_content_checks(root: Path, issues: list[str]) -> None:
    required = {
        "docs/product/v2/04_SHARED_FOOD_CATALOG.md": (
            "GET /foods",
            "`/admin/foods` does not exist",
            FOOD_DELETE_MESSAGE,
        ),
        "docs/product/v2/11_CURRENT_ARCHITECTURE_AND_DATA_MODEL.md": (
            EXPECTED_ALEMBIC_HEAD,
            "There is no Day Logging Status",
            "target_plan.activate",
            "target_plan.replace",
        ),
        "docs/product/v2/12_NUTRITION_RULES_SAFETY_AND_REGISTRY.md": (
            "rules_manifest_hash",
            "preview_hash",
            SPECIALIST_MESSAGE,
            VERY_LOW_MESSAGE,
        ),
    }
    for relative_name, snippets in required.items():
        source = root / relative_name
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                issues.append(
                    f"{relative_name}: required current authority missing: {snippet}"
                )

    forbidden = (
        "FoodCreateV3",
        "FoodUpdateV3",
        "FoodResponseV3",
        "uncategorized_count",
        "__uncategorized__",
        "registry_schema_version",
        "calculation_engine_version",
        "nutrition_registry_version",
        "LegacyTargetTransitionSnapshot",
    )
    current_product_files = [
        name
        for name in APPROVED_MARKDOWN
        if name.startswith(("docs/product/", "docs/ba/"))
    ]
    for relative_name in current_product_files:
        source = root / relative_name
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                issues.append(
                    f"{relative_name}: retired contract token present: {token}"
                )


def _alembic_checks(root: Path, issues: list[str]) -> None:
    revisions: dict[str, str | None] = {}
    versions = root / "backend/alembic/versions"
    for path in versions.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        revision = REVISION_RE.search(text)
        if not revision:
            continue
        down_revision = DOWN_REVISION_RE.search(text)
        revisions[revision.group(1)] = down_revision.group(1) if down_revision else None
    heads = sorted(set(revisions) - {parent for parent in revisions.values() if parent})
    if heads != [EXPECTED_ALEMBIC_HEAD]:
        issues.append(
            f"Alembic heads are {heads!r}, expected {[EXPECTED_ALEMBIC_HEAD]!r}"
        )
    for relative_name in (
        "docs/product/v2/06_DATA_MIGRATION_AND_CUTOVER.md",
        "docs/product/v2/07_RELEASE_AND_ROLLBACK_RUNBOOK.md",
        "docs/product/v2/11_CURRENT_ARCHITECTURE_AND_DATA_MODEL.md",
    ):
        source = root / relative_name
        if source.is_file() and EXPECTED_ALEMBIC_HEAD not in source.read_text(
            encoding="utf-8"
        ):
            issues.append(f"{relative_name}: current Alembic head is not documented")


def _runtime_checks(root: Path, issues: list[str]) -> None:
    models_text = (root / "backend/app/models.py").read_text(encoding="utf-8")
    models = frozenset(
        re.findall(
            r"^class\s+(\w+)\(SQLModel,\s*table=True\):", models_text, re.MULTILINE
        )
    )
    if models != EXPECTED_MODELS:
        issues.append(
            f"runtime entities are {sorted(models)!r}, expected {sorted(EXPECTED_MODELS)!r}"
        )

    openapi = json.loads((root / "frontend/openapi.json").read_text(encoding="utf-8"))
    paths = openapi.get("paths", {})
    actual_food_operations = {
        path: {
            method
            for method in methods
            if method in {"get", "post", "put", "delete", "patch"}
        }
        for path, methods in paths.items()
        if path == "/foods" or path.startswith("/foods/")
    }
    if actual_food_operations != EXPECTED_FOOD_OPERATIONS:
        issues.append(
            f"Food OpenAPI operations are {actual_food_operations!r}, expected {EXPECTED_FOOD_OPERATIONS!r}"
        )
    actual_target_plan_operations = {
        path: {
            method
            for method in methods
            if method in {"get", "post", "put", "delete", "patch"}
        }
        for path, methods in paths.items()
        if path == "/target-plans" or path.startswith("/target-plans/")
    }
    if actual_target_plan_operations != EXPECTED_TARGET_PLAN_OPERATIONS:
        issues.append(
            "Target Plan OpenAPI operations are "
            f"{actual_target_plan_operations!r}, expected {EXPECTED_TARGET_PLAN_OPERATIONS!r}"
        )
    actual_labs_operations = {
        path: {method for method in methods
               if method in {"get", "post", "put", "delete", "patch", "options", "head", "trace"}}
        for path, methods in paths.items()
        if path == "/labs" or path.startswith("/labs/")
        or path.startswith("/admin/users/") and "/labs" in path
    }
    if actual_labs_operations != EXPECTED_LABS_OPERATIONS:
        issues.append(
            f"Labs OpenAPI operations are {actual_labs_operations!r}, "
            f"expected {EXPECTED_LABS_OPERATIONS!r}"
        )
    catalog_path = root / "backend/app/labs/catalog.v1.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        keys = [item["test_key"] for item in catalog["tests"]]
        categories = [item["key"] for item in catalog["categories"]]
        panels = [item["key"] for item in catalog["panels"]]
        if len(keys) != 51 or frozenset(keys) != EXPECTED_LABS_KEYS:
            issues.append("Labs catalog must contain exactly the 51 approved unique test keys")
        if len(categories) != 15 or len(set(categories)) != 15:
            issues.append("Labs catalog must contain exactly 15 unique categories")
        if len(panels) != 7 or len(set(panels)) != 7:
            issues.append("Labs catalog must contain exactly 7 unique panels")
    except (OSError, ValueError, KeyError, TypeError):
        issues.append("Labs catalog is missing or malformed")
    get_foods_schema = (
        paths.get("/foods", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    if get_foods_schema.get("$ref") != "#/components/schemas/FoodListResponse":
        issues.append("GET /foods is not documented by OpenAPI as FoodListResponse")
    schemas = openapi.get("components", {}).get("schemas", {})
    for retired in ("FoodCreateV3", "FoodUpdateV3", "FoodResponseV3"):
        if retired in schemas:
            issues.append(f"OpenAPI retired schema present: {retired}")
    for path in paths:
        if path.startswith("/admin/foods"):
            issues.append(f"retired Admin Food API present: {path}")
        if path.startswith("/sync"):
            issues.append(f"retired Sync API present: {path}")
    serialized_openapi = json.dumps(openapi, ensure_ascii=False)
    for retired in ("uncategorized_count", "__uncategorized__"):
        if retired in serialized_openapi:
            issues.append(f"retired Food compatibility contract present: {retired}")

    if (root / "frontend/app/admin/foods/page.tsx").exists():
        issues.append("retired /admin/foods frontend page exists")
    proxy = root / "frontend/proxy.ts"
    if proxy.is_file() and "/admin/foods" in proxy.read_text(encoding="utf-8"):
        issues.append("retired /admin/foods proxy behavior exists")

    profile_model = (root / "frontend/features/profile/profile-model.ts").read_text(
        encoding="utf-8"
    )
    for message in (SPECIALIST_MESSAGE, VERY_LOW_MESSAGE):
        if message not in profile_model:
            issues.append(
                "governed Arabic nutrition safety copy differs from executable frontend"
            )


def _validate_documentation_estate(
    root: Path, *, runtime_checks: bool = True
) -> Results:
    issues: list[str] = []
    files = _repo_files(root)
    _markdown_checks(root, files, issues)
    _authority_content_checks(root, issues)
    if runtime_checks:
        _alembic_checks(root, issues)
        _runtime_checks(root, issues)
    return Results(tuple(issues))


def _print_results(results: Results) -> None:
    print(f"documentation validation: {'PASS' if results.ok else 'FAIL'}")
    print(f"issues: {len(results.issues)}")
    for issue in results.issues:
        print(f"  {issue}")


def _write_fixture(root: Path) -> None:
    for relative_name in APPROVED_MARKDOWN:
        path = root / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Current\n", encoding="utf-8")
    (root / "docs/product/v2/04_SHARED_FOOD_CATALOG.md").write_text(
        "# Food\n\nGET /foods\n\n`/admin/foods` does not exist\n\n"
        + FOOD_DELETE_MESSAGE,
        encoding="utf-8",
    )
    (root / "docs/product/v2/11_CURRENT_ARCHITECTURE_AND_DATA_MODEL.md").write_text(
        f"# Architecture\n\n{EXPECTED_ALEMBIC_HEAD}\n\nThere is no Day Logging Status\n\n"
        "target_plan.activate target_plan.replace\n",
        encoding="utf-8",
    )
    (root / "docs/product/v2/12_NUTRITION_RULES_SAFETY_AND_REGISTRY.md").write_text(
        f"# Nutrition\n\nrules_manifest_hash preview_hash\n\n{SPECIALIST_MESSAGE}\n\n{VERY_LOW_MESSAGE}\n",
        encoding="utf-8",
    )
    validator = root / VALIDATOR_PATH
    validator.parent.mkdir(parents=True, exist_ok=True)
    validator.write_text("# fixture\n", encoding="utf-8")


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="mynutri-doc-validator-") as temporary:
        root = Path(temporary)
        _write_fixture(root)
        assert _validate_documentation_estate(root, runtime_checks=False).ok

        extra = root / "docs/extra.md"
        extra.write_text("# Extra\n", encoding="utf-8")
        assert not _validate_documentation_estate(root, runtime_checks=False).ok
        extra.unlink()
        print("self-test: extra Markdown rejected")

        evidence = root / "docs/evidence.png"
        evidence.write_bytes(b"not-an-image")
        assert not _validate_documentation_estate(root, runtime_checks=False).ok
        evidence.unlink()
        print("self-test: documentation evidence rejected")

        readme = root / "README.md"
        readme.write_text("# Current\n\n[Broken](missing.md)\n", encoding="utf-8")
        assert not _validate_documentation_estate(root, runtime_checks=False).ok
        print("self-test: broken link rejected")
        _write_fixture(root)

        readme.write_text(
            "# Current\n\nDATABASE_URL=postgresql://user:password@host/db\n",
            encoding="utf-8",
        )
        assert not _validate_documentation_estate(root, runtime_checks=False).ok
        print("self-test: secret-shaped assignment rejected")

    with tempfile.TemporaryDirectory(prefix="mynutri-runtime-validator-") as temporary:
        root = Path(temporary)
        _write_fixture(root)
        for name in ("06_DATA_MIGRATION_AND_CUTOVER", "07_RELEASE_AND_ROLLBACK_RUNBOOK"):
            (root / f"docs/product/v2/{name}.md").write_text(EXPECTED_ALEMBIC_HEAD, encoding="utf-8")
        models = root / "backend/app/models.py"
        models.parent.mkdir(parents=True)
        models.write_text("\n".join(f"class {name}(SQLModel, table=True): pass" for name in sorted(EXPECTED_MODELS)), encoding="utf-8")
        migration = root / "backend/alembic/versions/current.py"
        migration.parent.mkdir(parents=True)
        migration.write_text(f'revision = "{EXPECTED_ALEMBIC_HEAD}"\ndown_revision = None\n', encoding="utf-8")
        profile = root / "frontend/features/profile/profile-model.ts"
        profile.parent.mkdir(parents=True)
        profile.write_text(SPECIALIST_MESSAGE + VERY_LOW_MESSAGE, encoding="utf-8")
        paths = {path: {method: {} for method in methods} for operations in (EXPECTED_FOOD_OPERATIONS, EXPECTED_TARGET_PLAN_OPERATIONS, EXPECTED_LABS_OPERATIONS) for path, methods in operations.items()}
        paths["/foods"]["get"] = {"responses": {"200": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/FoodListResponse"}}}}}}
        contract = root / "frontend/openapi.json"
        contract.write_text(json.dumps({"paths": paths}), encoding="utf-8")
        catalog_path = root / "backend/app/labs/catalog.v1.json"
        catalog_path.parent.mkdir(parents=True)
        approved_catalog = json.loads((Path(__file__).resolve().parents[2] / "backend/app/labs/catalog.v1.json").read_text(encoding="utf-8"))
        catalog_path.write_text(json.dumps(approved_catalog), encoding="utf-8")
        assert _validate_documentation_estate(root).ok

        for path, method in (("/labs/results", "get"), ("/admin/users/{principal_id}/labs/results", "post"), ("/labs/catalog", "options")):
            changed = json.loads(contract.read_text(encoding="utf-8"))
            changed["paths"].setdefault(path, {})[method] = {}
            contract.write_text(json.dumps(changed), encoding="utf-8")
            assert any("Labs OpenAPI operations" in issue for issue in _validate_documentation_estate(root).issues), (path, method)
            contract.write_text(json.dumps({"paths": paths}), encoding="utf-8")
        print("self-test: unexpected Labs operations rejected")
        original_models = models.read_text(encoding="utf-8")
        for changed in (original_models + "\nclass LabPanel(SQLModel, table=True): pass", original_models.replace("class LabResult(SQLModel, table=True): pass", "")):
            models.write_text(changed, encoding="utf-8")
            assert any("runtime entities" in issue for issue in _validate_documentation_estate(root).issues)
        models.write_text(original_models, encoding="utf-8")
        print("self-test: extra and missing entities rejected")
        for mutation in ("missing", "duplicate", "substitute", "category", "panel"):
            changed = json.loads(json.dumps(approved_catalog))
            if mutation == "missing":
                changed["tests"].pop()
            elif mutation == "duplicate":
                changed["tests"].append(changed["tests"][0])
            elif mutation == "substitute":
                changed["tests"][0]["test_key"] = "unapproved_test"
            elif mutation == "category":
                changed["categories"].pop()
            else:
                changed["panels"].pop()
            catalog_path.write_text(json.dumps(changed), encoding="utf-8")
            assert any("Labs catalog" in issue for issue in _validate_documentation_estate(root).issues), mutation
        catalog_path.write_text(json.dumps(approved_catalog), encoding="utf-8")
        print("self-test: Labs catalog drift rejected")
        migration.write_text('revision = "unexpected"\ndown_revision = None\n', encoding="utf-8")
        assert any("Alembic heads" in issue for issue in _validate_documentation_estate(root).issues)
        print("self-test: unexpected head rejected")

    print("self-test: passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    results = _validate_documentation_estate(args.root.resolve())
    _print_results(results)
    return 0 if results.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
