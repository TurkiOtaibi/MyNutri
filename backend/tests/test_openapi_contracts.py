from __future__ import annotations

from typing import get_type_hints

import pytest
from fastapi import HTTPException
from pydantic import TypeAdapter

from app.api.routes.diary import _command_expected_version, add_entry, edit_entry
from app.api.routes.foods import add_food, edit_food
from app.main import app
from app.nutrition_rules.manifest import registry_response
from app.schemas import (
    DiaryDayStatusCommand,
    NutritionRegistryResponse,
    WeeklyPriorityAnalysisInputV1,
)


def _request_schema(path: str, method: str) -> dict[str, object]:
    return app.openapi()["paths"][path][method]["requestBody"]["content"][
        "application/json"
    ]["schema"]


def test_food_and_diary_openapi_bodies_expose_real_contracts() -> None:
    food_create = _request_schema("/foods", "post")
    food_update = _request_schema("/foods/{food_id}", "put")
    diary_create = _request_schema("/diary/entries", "post")
    diary_update = _request_schema("/diary/entries/{entry_id}", "patch")

    assert set(food_create["required"]) >= {
        "name",
        "food_category_key",
        "nutrition_basis",
        "default_unit_type",
        "unit_amount",
        "unit_basis",
        "calories",
        "protein_g",
        "carb_g",
        "fat_g",
    }
    assert {"name", "calories", "nutrition_source"} <= set(
        food_create["properties"]
    )
    assert {"name", "calories", "nutrition_source"} <= set(
        food_update["properties"]
    )
    assert set(diary_create["required"]) == {"entry_date", "food_id", "quantity"}
    assert diary_create["properties"]["meal_type"]["default"] == "unspecified"
    assert "required" not in diary_update
    assert {"quantity", "meal_type"} == set(diary_update["properties"])
    assert food_create.get("additionalProperties") is not True
    assert diary_create.get("additionalProperties") is not True


def test_openapi_metadata_keeps_custom_runtime_payloads_as_plain_dicts() -> None:
    unvalidated = {"unexpected": "payload"}
    for endpoint in (add_food, edit_food, add_entry, edit_entry):
        annotation = get_type_hints(endpoint, include_extras=True)["payload"]
        assert TypeAdapter(annotation).validate_python(unvalidated) is unvalidated


def test_registry_openapi_is_typed_without_changing_runtime_payload() -> None:
    documented = app.openapi()["paths"]["/nutrition/registry"]["get"]["responses"]
    schema = documented["200"]["content"]["application/json"]["schema"]

    assert schema == {"$ref": "#/components/schemas/NutritionRegistryResponse"}
    assert documented["304"]["description"] == "Registry not modified"
    runtime_payload = registry_response()
    validated = NutritionRegistryResponse.model_validate(runtime_payload)
    assert validated.rules_manifest_hash == runtime_payload["rules_manifest_hash"]
    assert [item.model_dump() for item in validated.nutrients] == runtime_payload[
        "nutrients"
    ]
    assert validated.nova.model_dump(mode="json") == runtime_payload["nova"]


def test_day_logging_status_openapi_is_structured_and_admin_is_read_only() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    assert paths["/diary/days/{diary_date}/status"]["get"]["responses"]["200"]
    for action in ("complete", "reopen"):
        operation = paths[f"/diary/days/{{diary_date}}/{action}"]["put"]
        body = operation["requestBody"]["content"]["application/json"]["schema"]
        assert body == {"$ref": "#/components/schemas/DiaryDayStatusCommand"}
        headers = {
            item["name"]: item
            for item in operation["parameters"]
            if item["in"] == "header"
        }
        assert headers["If-Match"]["required"] is False
    response = components["DiaryDayStatusResponse"]
    assert set(response["required"]) == {
        "date",
        "logging_status",
        "logging_status_version",
        "entry_count",
        "analysis_eligible",
        "completed_at",
        "calendar",
    }
    assert set(components["DiaryLoggingStatus"]["enum"]) == {
        "unregistered",
        "partial",
        "complete",
    }
    admin_path = paths["/admin/users/{principal_id}/diary-days"]
    assert set(admin_path) == {"get"}
    assert not any(
        path.startswith("/admin/") and path.endswith(("/complete", "/reopen"))
        for path in paths
    )
    for path, method in (
        ("/diary/entries", "post"),
        ("/diary/entries/{entry_id}", "patch"),
        ("/diary/entries/{entry_id}", "delete"),
    ):
        headers = {
            item["name"]: item
            for item in paths[path][method]["parameters"]
            if item["in"] == "header"
        }
        assert headers["If-Match"]["required"] is True


def test_day_command_if_match_must_agree_with_body_version() -> None:
    payload = DiaryDayStatusCommand(expected_version=7)
    assert _command_expected_version(payload, None) == 7
    assert _command_expected_version(payload, '"day-7"') == 7
    with pytest.raises(HTTPException) as mismatch:
        _command_expected_version(payload, '"day-8"')
    assert mismatch.value.status_code == 422
    assert mismatch.value.detail["code"] == "VALIDATION_ERROR"


def test_pattern_analysis_openapi_is_closed_versioned_and_owner_only() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    for path, methods in {
        "/progress/nutrition-analysis/current": {"get"},
        "/progress/nutrition-analysis/history": {"get"},
        "/progress/nutrition-analysis/{analysis_id}/revisions/{revision}": {"get"},
        "/progress/nutrition-analysis/evaluate": {"post"},
        "/admin/nutrition-analysis/monitoring": {"get"},
    }.items():
        assert set(paths[path]) == methods
    evaluate = paths["/progress/nutrition-analysis/evaluate"]["post"]
    headers = {
        item["name"]: item
        for item in evaluate["parameters"]
        if item["in"] == "header"
    }
    assert headers["If-Match"]["required"] is True
    assert headers["Idempotency-Key"]["required"] is True
    priority = schema["components"]["schemas"]["WeeklyPriorityAnalysisInputV1"]
    assert priority["additionalProperties"] is False
    assert set(priority["required"]) >= {
        "principal_ref",
        "source_analysis_id",
        "source_analysis_revision",
        "days",
        "previous_period",
        "metric_facts",
        "safety_flags",
    }
    assert WeeklyPriorityAnalysisInputV1.model_config["extra"] == "forbid"
