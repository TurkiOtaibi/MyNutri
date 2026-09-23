from __future__ import annotations

from typing import get_type_hints

from fastapi.testclient import TestClient
from pydantic import TypeAdapter

from app.api.routes import (
    admin as admin_routes,
    diary as diary_routes,
    foods as food_routes,
    profile as profile_routes,
    target_plans as target_plan_routes,
)
from app.api.routes.diary import add_entry, edit_entry
from app.api.routes.foods import add_food, edit_food
from app.main import app
from app.nutrition_rules.manifest import registry_response
from app.schemas import NutritionRegistryResponse


def test_labs_openapi_routes_and_exact_wire_contracts():
    schema = app.openapi()
    paths, models = schema["paths"], schema["components"]["schemas"]
    expected = {
        ("/labs/catalog", "get"): ("200", "LabCatalogResponse"),
        ("/labs", "get"): ("200", "LabOverviewResponse"),
        ("/labs/tests/{test_key}", "get"): ("200", "LabTestDetailResponse"),
        ("/labs/results", "post"): ("201", "LabCreateReceipt"),
        ("/labs/results/{result_id}", "patch"): ("200", "LabResultResponse"),
        ("/labs/results/{result_id}", "delete"): ("204", None),
        ("/admin/users/{principal_id}/labs", "get"): ("200", "LabOverviewResponse"),
        ("/admin/users/{principal_id}/labs/tests/{test_key}", "get"):
            ("200", "LabTestDetailResponse"),
    }
    assert set(expected) == {
        (path, method) for path, operations in paths.items()
        if path.startswith("/labs") or "/labs" in path
        for method in operations if method in {"get", "post", "patch", "put", "delete"}
    }
    for (path, method), (status, name) in expected.items():
        operation = paths[path][method]
        assert operation["security"] == [{"BearerAuth": []}]
        assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
        if name:
            assert operation["responses"][status]["content"]["application/json"]["schema"] == {
                "$ref": f"#/components/schemas/{name}"
            }
        for error in ("409", "422"):
            assert operation["responses"][error]["content"]["application/json"]["schema"] == {
                "$ref": "#/components/schemas/LabErrorResponse"
            }
    assert "Idempotent-Replayed" in paths["/labs/results"]["post"]["responses"]["201"]["headers"]
    for path, method, keys in (
        ("/labs/results", "post", {"test_date", "results"}),
        ("/labs/results/{result_id}", "patch", {"test_date", "entered_value", "entered_unit", "expected_updated_at"}),
    ):
        body = _request_schema(path, method)
        assert set(body["properties"]) == keys
        assert set(body["required"]) == keys and body["additionalProperties"] is False
        if method == "patch":
            assert body["properties"]["expected_updated_at"]["type"] == "string"
            assert body["properties"]["expected_updated_at"]["format"] == "date-time"
    row = models["LabCreateRow"]
    assert row["additionalProperties"] is False
    assert set(row["properties"]) == {"test_key", "entered_value", "entered_unit"}
    for field in row["properties"].values():
        assert field["type"] == "string" and "enum" not in field
    for field in ("entered_value", "display_value"):
        assert models["LabResultResponse"]["properties"][field]["type"] == "string"
    for field in ("low", "high"):
        assert models["LabStatusZone"]["properties"][field]["anyOf"] == [
            {"type": "string"}, {"type": "null"}
        ]
    assert "medical_rules_version" in models["LabResultResponse"]["required"]


def _request_schema(path: str, method: str) -> dict[str, object]:
    return app.openapi()["paths"][path][method]["requestBody"]["content"]["application/json"][
        "schema"
    ]


def test_food_and_diary_openapi_bodies_expose_real_contracts() -> None:
    food_create = _request_schema("/foods", "post")
    food_update = _request_schema("/foods/{food_id}", "put")
    diary_create = _request_schema("/diary/entries", "post")
    diary_update = _request_schema("/diary/entries/{entry_id}", "patch")

    assert set(food_create["required"]) >= {
        "name",
        "primary_category",
        "subcategory",
        "nutrition_data_source",
        "nutrition_basis",
        "default_unit_type",
        "unit_amount",
        "unit_basis",
        "calories",
        "protein_g",
        "carb_g",
        "fat_g",
    }
    assert {"name", "calories", "nutrition_data_source"} <= set(food_create["properties"])
    assert {"name", "calories", "nutrition_data_source"} <= set(food_update["properties"])
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
    assert [item.model_dump() for item in validated.nutrients] == runtime_payload["nutrients"]
    assert "nova" not in validated.model_dump(mode="json")


def test_day_logging_status_contract_is_absent() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    components = schema["components"]["schemas"]

    retired_paths = {
        "/diary/days/{diary_date}/status",
        "/diary/days/{diary_date}/complete",
        "/diary/days/{diary_date}/reopen",
        "/admin/users/{principal_id}/diary-days",
    }
    assert retired_paths.isdisjoint(paths)
    assert {
        "DiaryLoggingStatus",
        "DiaryDayStatusCommand",
        "DiaryDayStatusResponse",
        "AdminDiaryDayStatusPage",
    }.isdisjoint(components)
    assert {
        "logging_status",
        "logging_status_version",
        "entry_count",
        "completed_at",
    }.isdisjoint(components["DaySummary"]["properties"])
    for path, method in (
        ("/diary/entries", "post"),
        ("/diary/entries/{entry_id}", "patch"),
        ("/diary/entries/{entry_id}", "delete"),
    ):
        assert not any(
            item["in"] == "header" and item["name"].lower() == "if-match"
            for item in paths[path][method].get("parameters", [])
        )

    client = TestClient(app)
    for method, url in (
        ("GET", "/diary/days/2026-09-13/status"),
        ("PUT", "/diary/days/2026-09-13/complete"),
        ("PUT", "/diary/days/2026-09-13/reopen"),
        ("GET", "/admin/users/00000000-0000-0000-0000-000000000001/diary-days"),
    ):
        assert client.request(method, url, json={} if method == "PUT" else None).status_code == 404
    schemas = app.openapi()["components"]["schemas"]
    serialized = str(schemas)
    for retired in (
        "calculation_document_schema_version",
        "calculation_engine_version",
        "nutrition_registry_version",
        "registry_schema_version",
        "target_provenance",
        "target_source_detail",
        "legacy_unversioned",
    ):
        assert retired not in serialized

    assert "source" not in schemas["DiaryNutrientTarget"]["properties"]
    assert "target_provenance" not in schemas["DiaryEntryResponse"]["properties"]
    assert "target_provenance" not in schemas["DaySummary"]["properties"]
    assert "target_provenance" not in schemas["ProfileResponse"]["properties"]
    for name in ("plan", "targets"):
        assert {"type": "null"} in schemas["TargetSourceResponse"]["properties"][name]["anyOf"]


def test_retired_analysis_priority_and_snapshot_contracts_are_absent() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    assert not any(path.startswith("/progress/") for path in paths)
    assert "/admin/nutrition-analysis/monitoring" not in paths
    serialized = str(schema).lower()
    for retired in (
        "nutrition_snapshot",
        "snapshot_schema_version",
        "weeklypriority",
        "behaviorgoal",
        "nutritionanalysis",
    ):
        assert retired not in serialized


def test_sync_future_scope_has_no_runtime_contract() -> None:
    schema = app.openapi()

    assert not any(path.startswith("/sync") for path in schema["paths"])
    assert {
        "SyncOperation",
        "SyncPushRequest",
        "SyncPushResponse",
    }.isdisjoint(schema["components"]["schemas"])


def test_unused_routes_are_absent_and_protected_routes_remain() -> None:
    relevant_routers = (
        admin_routes.router,
        diary_routes.router,
        food_routes.router,
        profile_routes.router,
        target_plan_routes.router,
    )
    operations = {
        (method, route.path)
        for router in relevant_routers
        for route in router.routes
        for method in getattr(route, "methods", set())
    }
    assert operations.isdisjoint(
        {
            ("POST", "/diary"),
            ("GET", "/diary"),
            ("GET", "/diary/{entry_id}"),
            ("PUT", "/diary/{entry_id}"),
            ("DELETE", "/diary/{entry_id}"),
            ("GET", "/diary/entries/{entry_id}"),
            ("GET", "/admin/users/{principal_id}/diary/week"),
            ("GET", "/admin/users/{principal_id}/target-plans"),
            ("GET", "/diary/days/{diary_date}/status"),
            ("PUT", "/diary/days/{diary_date}/complete"),
            ("PUT", "/diary/days/{diary_date}/reopen"),
            ("GET", "/admin/users/{principal_id}/diary-days"),
            ("PUT", "/profile"),
        }
    )
    assert ("DELETE", "/foods/{food_id}") in operations
    assert {
        ("POST", "/target-plans"),
        ("GET", "/target-plans"),
        ("GET", "/target-plans/current"),
    } <= operations
    assert {
        ("POST", "/target-plans/activate"),
        ("POST", "/target-plans/pending/replace"),
        ("GET", "/target-plans/pending"),
    }.isdisjoint(operations)


def test_food_catalog_contract_has_one_surface_without_archive_state() -> None:
    schema = app.openapi()
    paths = schema["paths"]
    schemas = schema["components"]["schemas"]

    assert {
        ("get", "/foods"),
        ("post", "/foods"),
        ("get", "/foods/picker"),
        ("get", "/foods/{food_id}"),
        ("put", "/foods/{food_id}"),
        ("delete", "/foods/{food_id}"),
    } == {
        (method, path)
        for path, definition in paths.items()
        if path == "/foods" or path.startswith("/foods/")
        for method in definition
        if method in {"get", "post", "put", "delete"}
    }
    assert not any(path.startswith("/admin/foods") for path in paths)
    assert paths["/foods/{food_id}"]["delete"]["responses"]["204"]["description"]
    assert "FoodDeleteResponse" not in schemas
    assert "archived_at" not in schemas["FoodResponse"]["properties"]
    assert not {"FoodCreateV3", "FoodUpdateV3", "FoodResponseV3"} & schemas.keys()
    assert "uncategorized_count" not in schemas["FoodListResponse"]["properties"]
    assert paths["/foods"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"] == {"$ref": "#/components/schemas/FoodListResponse"}
    assert "archived" not in {
        parameter["name"] for parameter in paths["/foods"]["get"].get("parameters", [])
    }
