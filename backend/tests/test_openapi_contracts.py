from __future__ import annotations

from typing import get_type_hints

from pydantic import TypeAdapter

from app.api.routes.diary import add_entry, edit_entry
from app.api.routes.foods import add_food, edit_food
from app.main import app
from app.nutrition_rules.manifest import registry_response
from app.schemas import NutritionRegistryResponse


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
