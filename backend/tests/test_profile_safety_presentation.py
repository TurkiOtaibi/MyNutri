"""BR-PRF-015/022: presentation follows existing decisions and stored results."""

import ast
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import get_args
from uuid import uuid4

import pytest

from app.models import TargetPlan
from app.nutrition_rules.calculation import CalculationError, calculate_carbohydrate
from app.schemas import ProfilePreview, TargetResponse
from app.services.profile import preview_targets
from app.services.target_plans import to_plan_summary


def test_every_blocking_backend_reason_has_frontend_reason_and_alternative():
    root = Path(__file__).resolve().parents[2]
    copy = json.loads((root / "frontend/features/profile/profile-safety-copy.json").read_text(encoding="utf-8"))
    outcomes = set(get_args(TargetResponse.model_fields["safety_outcome"].annotation)) - {"normal"}
    assert outcomes <= copy.keys()
    tree = ast.parse((root / "backend/app/nutrition_rules/calculation.py").read_text(encoding="utf-8"))
    calculation_codes = {
        node.args[0].value for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "CalculationError" and isinstance(node.args[0], ast.Constant)
    }
    assert {item["code"] for item in copy.values()} == calculation_codes | {
        "SPECIALIST_REVIEW_REQUIRED", "VERY_LOW_ENERGY_TARGET_BLOCKED",
    }
    for item in copy.values():
        assert item["reason"] and item["alternative"]
        assert "خفض الوزن" not in item["alternative"]
    with pytest.raises(CalculationError) as error:
        calculate_carbohydrate(800, Decimal(200), Decimal("0.3"))
    assert error.value.code == copy["non_positive_carbohydrate_allocation"]["code"]


@pytest.mark.parametrize(("weight", "height", "goal", "expected"), [
    (80, 180, "maintain", (1434, 1720.8, 1721, 96, 57.4, 205.2, "normal", True)),
    (40, 150, "cut", (846.5, 1015.8, 813, 48, 27.1, 94.3, "specialist_review_required", False)),
    (20, 100, "cut", (334, 400.8, 321, 24, 10.7, 32.2, "very_low_energy_blocked", False)),
])
def test_safety_copy_does_not_change_preview_calculations(weight, height, goal, expected):
    result = preview_targets(ProfilePreview(
        sex="female", birth_date=date(1960, 1, 1), height_cm=height, weight_kg=weight,
        activity_level="sedentary", goal=goal, protein_per_kg=1.2, fat_pct=0.3,
        selected_cut_intensity=0.2,
    ), date(2026, 10, 26))
    assert (
        result.bmr, result.tdee, result.target_calories, result.protein_g,
        result.fat_g, result.carb_g, result.safety_outcome, result.can_activate,
    ) == expected


def test_plan_history_projects_stored_macros_without_recalculation(monkeypatch):
    result = preview_targets(ProfilePreview(
        sex="male", birth_date=date(1990, 1, 1), height_cm=180, weight_kg=80,
        activity_level="moderate", goal="maintain", protein_per_kg=1.2,
        fat_pct=0.25, selected_cut_intensity=0.2,
    ), date(2026, 10, 26)).model_dump(mode="json")
    result.update(target_calories=1999, protein_g=95.5, carb_g=250.3, fat_g=61.2)

    def forbid_calculation(*args, **kwargs):
        pytest.fail("History must project stored results, not recalculate them")

    monkeypatch.setattr("app.services.profile.calculate_targets", forbid_calculation)
    plan = TargetPlan(
        id=uuid4(), principal_id=uuid4(), profile_id=uuid4(), revision=2,
        effective_from=date(2026, 10, 17), created_at=datetime(2026, 10, 16, tzinfo=UTC),
        calculation_document={"target_result": result},
    )
    summary = to_plan_summary(plan)
    assert summary.targets.model_dump(mode="json") == result
    assert summary.revision == 2
    assert summary.effective_from == date(2026, 10, 17)
