from datetime import date
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.session import get_session
from app.core.auth import PrincipalContext
from app.main import app
from app.models import (
    DefaultUnitType,
    DiaryEntry,
    FoodAnalyticalTrait,
    FoodGroupContribution,
    NutritionBasis,
    Principal,
    UnitBasis,
)
from app.schemas import FoodCreate
from app.services.diary import make_snapshot, to_entry_response
from app.services.food import (
    UNCATEGORIZED_CATEGORY,
    create_food,
    delete_food,
    list_foods,
    list_foods_page,
)

from app.services.food_validation_errors import (
    ABOVE_MAX_MESSAGE,
    ADDED_SUGAR_GT_SUGAR_MESSAGE,
    BELOW_MIN_MESSAGE,
    DUPLICATE_FOOD_MESSAGE,
    FIBER_GT_CARBS_MESSAGE,
    FOOD_NAME_REQUIRED_MESSAGE,
    INVALID_SELECT_MESSAGE,
    OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE,
    REQUIRED_MESSAGE,
    SATURATED_TRANS_GT_FAT_MESSAGE,
)

TEST_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_PRINCIPAL = PrincipalContext(TEST_PRINCIPAL_ID)


def session_fixture() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add(Principal(id=TEST_PRINCIPAL_ID))
    session.commit()
    return session


def food_payload(**overrides):
    payload = {
        "name": "Greek Yogurt",
        "brand": "Local",
        "category": "Dairy",
        "primary_category_key": "other",
        "food_kind": "simple",
        "nutrition_basis": NutritionBasis.per_100g,
        "default_unit_type": DefaultUnitType.serving,
        "unit_amount": 170,
        "unit_basis": UnitBasis.g,
        "calories": 120,
        "protein_g": 18,
        "carb_g": 7,
        "fat_g": 0,
        "fiber_g": 1,
        "sugar_g": 4,
        "added_sugar_g": 0,
        "nutrition_source": {"type": "unknown"},
    }
    payload.update(overrides)
    return payload


def food_json(**overrides):
    payload = food_payload(**overrides)
    for key, value in list(payload.items()):
        if hasattr(value, "value"):
            payload[key] = value.value
    return payload


@pytest.fixture
def api_client():
    session = session_fixture()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        client.close()
        session.close()


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-token"}


def error_by_field(response) -> dict[str, dict]:
    assert response.status_code == 422
    details = response.json()["detail"]
    return {item["field"]: item for item in details}


def test_create_food_blocks_normalized_duplicate() -> None:
    with session_fixture() as session:
        create_food(
            session, TEST_PRINCIPAL, FoodCreate.model_validate(food_payload(name="Greek   Yogurt"))
        )

        with pytest.raises(HTTPException) as error:
            create_food(
                session,
                TEST_PRINCIPAL,
                FoodCreate.model_validate(food_payload(name=" greek yogurt ")),
            )

        assert error.value.status_code == 422
        assert error.value.detail[0]["msg"] == DUPLICATE_FOOD_MESSAGE


def test_food_api_returns_structured_arabic_required_errors(api_client: TestClient) -> None:
    response = api_client.post("/foods", json={"name": "Rice"}, headers=auth_headers())

    errors = error_by_field(response)

    assert errors["nutrition_basis"]["code"] == "required"
    assert errors["nutrition_basis"]["msg"] == REQUIRED_MESSAGE
    assert errors["calories"]["code"] == "required"
    assert errors["calories"]["msg"] == REQUIRED_MESSAGE
    assert errors["default_unit_type"]["loc"] == ["body", "default_unit_type"]


def test_food_api_returns_arabic_invalid_enum_and_number_errors(api_client: TestClient) -> None:
    payload = food_json(nutrition_basis="per_serving", unit_basis="oz", calories=-1, protein_g=301)

    response = api_client.post("/foods", json=payload, headers=auth_headers())
    errors = error_by_field(response)

    assert errors["nutrition_basis"]["code"] == "invalid_option"
    assert errors["nutrition_basis"]["msg"] == INVALID_SELECT_MESSAGE
    assert errors["unit_basis"]["code"] == "invalid_option"
    assert errors["calories"]["code"] == "below_min"
    assert errors["calories"]["msg"] == BELOW_MIN_MESSAGE
    assert errors["protein_g"]["code"] == "above_max"
    assert errors["protein_g"]["msg"] == ABOVE_MAX_MESSAGE


def test_food_api_returns_arabic_name_and_unit_amount_errors(api_client: TestClient) -> None:
    payload = food_json(name="   ", unit_amount=0)

    response = api_client.post("/foods", json=payload, headers=auth_headers())
    errors = error_by_field(response)

    assert errors["name"]["field"] == "name"
    assert errors["name"]["code"] == "required"
    assert errors["name"]["msg"] == FOOD_NAME_REQUIRED_MESSAGE
    assert errors["unit_amount"]["code"] == "below_min"
    assert errors["unit_amount"]["msg"] == BELOW_MIN_MESSAGE


@pytest.mark.parametrize(
    ("field", "maximum"),
    [
        ("name", 120),
        ("brand", 80),
        ("category", 80),
        ("notes", 500),
        ("data_source", 120),
    ],
)
def test_food_api_enforces_text_max_lengths(
    api_client: TestClient,
    field: str,
    maximum: int,
) -> None:
    accepted_payload = food_json(name=f"Accepted {field}")
    accepted_payload[field] = "a" * maximum
    accepted = api_client.post("/foods", json=accepted_payload, headers=auth_headers())
    assert accepted.status_code == 201

    rejected_payload = food_json(name=f"Rejected {field}")
    rejected_payload[field] = "b" * (maximum + 1)
    rejected = api_client.post("/foods", json=rejected_payload, headers=auth_headers())
    errors = error_by_field(rejected)
    assert errors[field]["code"] == "above_max"
    assert errors[field]["msg"] == ABOVE_MAX_MESSAGE

    update = api_client.put(
        f"/foods/{accepted.json()['id']}",
        json={field: "c" * (maximum + 1)},
        headers=auth_headers(),
    )
    update_errors = error_by_field(update)
    assert update_errors[field]["code"] == "above_max"
    assert update_errors[field]["msg"] == ABOVE_MAX_MESSAGE


def test_food_api_returns_field_level_cross_field_errors(api_client: TestClient) -> None:
    response = api_client.post("/foods", json=food_json(fiber_g=8), headers=auth_headers())
    errors = error_by_field(response)

    assert errors["fiber_g"]["code"] == "fiber_gt_carbs"
    assert errors["fiber_g"]["msg"] == FIBER_GT_CARBS_MESSAGE

    response = api_client.post(
        "/foods", json=food_json(sugar_g=3, added_sugar_g=4), headers=auth_headers()
    )
    errors = error_by_field(response)

    assert errors["added_sugar_g"]["code"] == "added_sugar_gt_sugar"
    assert errors["added_sugar_g"]["msg"] == ADDED_SUGAR_GT_SUGAR_MESSAGE

    response = api_client.post(
        "/foods",
        json=food_json(fat_g=5, saturated_fat_g=3, trans_fat_g=3),
        headers=auth_headers(),
    )
    errors = error_by_field(response)

    assert errors["trans_fat_g"]["code"] == "saturated_trans_gt_fat"
    assert errors["trans_fat_g"]["msg"] == SATURATED_TRANS_GT_FAT_MESSAGE


def test_food_api_returns_arabic_optional_nutrient_max_error(api_client: TestClient) -> None:
    response = api_client.post("/foods", json=food_json(vitamin_d_mcg=251), headers=auth_headers())
    errors = error_by_field(response)

    assert errors["vitamin_d_mcg"]["code"] == "optional_nutrient_above_max"
    assert errors["vitamin_d_mcg"]["msg"] == OPTIONAL_NUTRIENT_ABOVE_MAX_MESSAGE


def test_food_api_returns_structured_duplicate_error(api_client: TestClient) -> None:
    first = api_client.post("/foods", json=food_json(name="Greek   Yogurt"), headers=auth_headers())
    assert first.status_code == 201

    response = api_client.post(
        "/foods", json=food_json(name=" greek yogurt "), headers=auth_headers()
    )
    errors = error_by_field(response)

    assert errors["name"]["code"] == "duplicate_food"
    assert errors["name"]["msg"] == DUPLICATE_FOOD_MESSAGE


def test_food_api_update_returns_structured_arabic_errors_for_direct_invalid_field(
    api_client: TestClient,
) -> None:
    created = api_client.post("/foods", json=food_json(), headers=auth_headers())
    assert created.status_code == 201
    food_id = created.json()["id"]

    response = api_client.put(
        f"/foods/{food_id}",
        json={"protein_g": -1},
        headers=auth_headers(),
    )
    errors = error_by_field(response)

    assert errors["protein_g"]["code"] == "below_min"
    assert errors["protein_g"]["msg"] == BELOW_MIN_MESSAGE


def test_food_api_update_returns_structured_arabic_errors_after_merge(
    api_client: TestClient,
) -> None:
    created = api_client.post("/foods", json=food_json(), headers=auth_headers())
    assert created.status_code == 201
    food_id = created.json()["id"]

    response = api_client.put(
        f"/foods/{food_id}",
        json={"fiber_g": 8},
        headers=auth_headers(),
    )
    errors = error_by_field(response)

    assert errors["fiber_g"]["code"] == "fiber_gt_carbs"
    assert errors["fiber_g"]["msg"] == FIBER_GT_CARBS_MESSAGE


def test_same_food_name_with_different_default_unit_is_allowed() -> None:
    with session_fixture() as session:
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(default_unit_type=DefaultUnitType.serving)),
        )
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(default_unit_type=DefaultUnitType.cup)),
        )

        assert len(list_foods(session, TEST_PRINCIPAL)) == 2


def test_deleted_food_does_not_block_duplicate_recreation() -> None:
    with session_fixture() as session:
        food = create_food(session, TEST_PRINCIPAL, FoodCreate.model_validate(food_payload()))
        delete_food(session, TEST_PRINCIPAL, food.id)
        recreated = create_food(session, TEST_PRINCIPAL, FoodCreate.model_validate(food_payload()))

        assert recreated.id != food.id
        assert len(list_foods(session, TEST_PRINCIPAL)) == 1


def test_food_list_pagination_preserves_legacy_array_response(api_client: TestClient) -> None:
    first = api_client.post(
        "/foods",
        json=food_json(name="Legacy Food", category="Legacy"),
        headers=auth_headers(),
    )
    assert first.status_code == 201

    legacy = api_client.get("/foods", headers=auth_headers())
    assert legacy.status_code == 200
    assert isinstance(legacy.json(), list)

    paged = api_client.get("/foods?page=1&page_size=20", headers=auth_headers())
    assert paged.status_code == 200
    body = paged.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total_pages"] == 1
    assert body["categories"] == ["Legacy"]
    assert body["items"][0]["name"] == "Legacy Food"


def test_food_page_combines_search_category_and_uncategorized_filters() -> None:
    with session_fixture() as session:
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(name="Arabic Oats", category="Breakfast")),
        )
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(name="Other Oats", category="Snacks")),
        )
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(name="Plain Oats", category=None)),
        )

        breakfast = list_foods_page(session, TEST_PRINCIPAL, search="oats", category="Breakfast")
        assert [food.name for food in breakfast.items] == ["Arabic Oats"]
        assert breakfast.total == 1
        assert breakfast.categories == ["Breakfast", "Snacks"]
        assert breakfast.uncategorized_count == 1

        uncategorized = list_foods_page(session, TEST_PRINCIPAL, category=UNCATEGORIZED_CATEGORY)
        assert [food.name for food in uncategorized.items] == ["Plain Oats"]


def test_food_search_matches_brand_for_diary_picker() -> None:
    with session_fixture() as session:
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(name="Arabic oats", brand="Gullon Oaty")),
        )
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(name="Other food", brand="Different")),
        )

        legacy_results = list_foods(session, TEST_PRINCIPAL, "gullon")
        paged_results = list_foods_page(session, TEST_PRINCIPAL, search="GULLON")

        assert [food.name for food in legacy_results] == ["Arabic oats"]
        assert [food.name for food in paged_results.items] == ["Arabic oats"]


def test_food_page_sorts_by_derived_serving_calories_and_protein() -> None:
    with session_fixture() as session:
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(name="Small Serving", calories=500, protein_g=20, unit_amount=10)
            ),
        )
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(name="Large Serving", calories=100, protein_g=8, unit_amount=100)
            ),
        )

        by_calories = list_foods_page(session, TEST_PRINCIPAL, sort="calories")
        assert [food.name for food in by_calories.items] == ["Large Serving", "Small Serving"]

        by_protein = list_foods_page(session, TEST_PRINCIPAL, sort="protein")
        assert [food.name for food in by_protein.items] == ["Large Serving", "Small Serving"]


def test_optional_nutrient_cross_field_validation() -> None:
    with pytest.raises(ValidationError):
        FoodCreate.model_validate(food_payload(fiber_g=8))

    with pytest.raises(ValidationError):
        FoodCreate.model_validate(food_payload(sugar_g=3, added_sugar_g=4))

    with pytest.raises(ValidationError):
        FoodCreate.model_validate(food_payload(fat_g=5, saturated_fat_g=3, trans_fat_g=3))


def test_optional_nutrient_max_ranges() -> None:
    FoodCreate.model_validate(food_payload(vitamin_d_mcg=250, sodium_mg=50000))

    with pytest.raises(ValidationError):
        FoodCreate.model_validate(food_payload(vitamin_d_mcg=251))

    with pytest.raises(ValidationError):
        FoodCreate.model_validate(food_payload(sodium_mg=50001))


def test_diary_snapshot_survives_food_hard_delete() -> None:
    with session_fixture() as session:
        food = create_food(session, TEST_PRINCIPAL, FoodCreate.model_validate(food_payload()))
        entry = DiaryEntry(
            principal_id=TEST_PRINCIPAL_ID,
            entry_date=date(2026, 7, 9),
            food_id=food.id,
            quantity=1,
            nutrition_snapshot=make_snapshot(food, 1),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        delete_food(session, TEST_PRINCIPAL, food.id)
        response = to_entry_response(entry)

        assert response.nutrition_snapshot.name == "Greek Yogurt"
        assert response.nutrition_snapshot.nutrition_basis == NutritionBasis.per_100g
        assert response.totals.calories == 204


def test_wave1_food_contract_preserves_exact_null_zero_and_legacy_values(
    api_client: TestClient,
) -> None:
    payload = food_json(
        name="Wave 1 exact nutrients",
        selenium_mcg=0,
        iodine_mcg=None,
        folate_dfe_mcg=425.125,
        vitamin_a_rae_mcg=None,
        folate_mcg=350,
        vitamin_a_mcg=700,
    )

    response = api_client.post("/foods", json=payload, headers=auth_headers())

    assert response.status_code == 201
    body = response.json()
    assert body["selenium_mcg"] == 0
    assert body["iodine_mcg"] is None
    assert body["folate_dfe_mcg"] == 425.125
    assert body["vitamin_a_rae_mcg"] is None
    assert body["legacy_nutrition"] == {
        "folate_mcg": 350.0,
        "vitamin_a_mcg": 700.0,
        "meaning_ar": "قيمة قديمة غير محددة المعيار",
    }


@pytest.mark.parametrize("missing_field", ("primary_category_key", "food_kind", "nutrition_source"))
def test_wave1_new_food_requires_controlled_classification_and_source(
    api_client: TestClient, missing_field: str
) -> None:
    payload = food_json(name=f"Missing {missing_field}")
    payload.pop(missing_field)

    response = api_client.post("/foods", json=payload, headers=auth_headers())

    assert response.status_code == 422
    assert error_by_field(response)[missing_field]["code"] == "required"


def test_wave1_source_reliability_and_nova_are_backend_controlled(
    api_client: TestClient,
) -> None:
    payload = food_json(name="Controlled source")
    payload.update(
        nutrition_source={
            "type": "multiple_sources",
            "name": "Label and database",
            "reference": "REF-1",
        },
        ingredients={
            "text": "شوفان، حليب",
            "source_type": "official_product_label",
            "source_name": "Product label",
            "source_reference": None,
        },
        nova={"classification": "unknown"},
    )

    response = api_client.post("/foods", json=payload, headers=auth_headers())

    assert response.status_code == 201
    body = response.json()
    assert body["nutrition_source"]["reliability"] == "mixed"
    assert body["nutrition_source"]["reliability_rules_version"] == "1.0.0"
    assert body["nova"] == {
        "classification": "unknown",
        "review_status": "reviewed",
        "rules_version": "1.0.0",
    }

    payload["nutrition_source"]["reliability"] = "high"
    rejected = api_client.post("/foods", json=payload, headers=auth_headers())
    assert rejected.status_code == 422
    assert error_by_field(rejected)["reliability"]["code"] == "invalid"


def test_wave1_food_update_rejects_client_authoritative_reliability(
    api_client: TestClient,
) -> None:
    created = api_client.post(
        "/foods",
        json=food_json(name="Update controlled source"),
        headers=auth_headers(),
    )
    assert created.status_code == 201

    rejected = api_client.put(
        f"/foods/{created.json()['id']}",
        json={"source_reliability": "high"},
        headers=auth_headers(),
    )

    assert rejected.status_code == 422
    assert error_by_field(rejected)["source_reliability"]["code"] == "invalid"


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        (
            {
                "group_data_status": "known",
                "group_data_completeness": "complete",
                "group_contributions": [
                    {
                        "group_key": "fruits",
                        "amount_per_100_basis": 60,
                        "data_status": "known",
                    },
                    {
                        "group_key": "fruits",
                        "amount_per_100_basis": 40,
                        "data_status": "known",
                    },
                ],
            },
            "duplicate_food_group",
        ),
        (
            {
                "group_data_status": "known",
                "group_data_completeness": "complete",
                "group_contributions": [
                    {
                        "group_key": "fruits",
                        "amount_per_100_basis": 60,
                        "data_status": "known",
                    },
                    {
                        "group_key": "vegetables",
                        "amount_per_100_basis": 41,
                        "data_status": "known",
                    },
                ],
            },
            "food_group_total_exceeded",
        ),
        (
            {
                "group_data_status": "known",
                "group_data_completeness": "complete",
                "group_contributions": [
                    {
                        "group_key": "dairy_fortified_alternatives",
                        "amount_per_100_basis": 100,
                        "data_status": "known",
                    }
                ],
            },
            "invalid_food_group_subtype",
        ),
        (
            {
                "group_data_status": "estimated",
                "group_data_completeness": "complete",
                "group_contributions": [],
            },
            "estimated_group_data_requires_estimate",
        ),
    ],
)
def test_wave1_group_contract_returns_stable_validation_codes(
    api_client: TestClient, overrides: dict, code: str
) -> None:
    response = api_client.post(
        "/foods",
        json=food_json(name=f"Invalid {code}", **overrides),
        headers=auth_headers(),
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["code"] == code


def test_wave1_food_update_atomically_replaces_groups_and_traits(
    api_client: TestClient,
) -> None:
    payload = food_json(
        name="Composite food",
        primary_category_key="mixed_dish",
        food_kind="composite",
        group_data_status="estimated",
        group_data_completeness="partial",
        group_contributions=[
            {
                "group_key": "whole_grains",
                "amount_per_100_basis": 40,
                "data_status": "estimated",
            }
        ],
        analytical_traits=["sweetened"],
    )
    created = api_client.post("/foods", json=payload, headers=auth_headers())
    assert created.status_code == 201

    replaced = api_client.put(
        f"/foods/{created.json()['id']}",
        json={
            "group_data_status": "known",
            "group_data_completeness": "complete",
            "group_contributions": [
                {
                    "group_key": "refined_grains",
                    "amount_per_100_basis": 75,
                    "data_status": "known",
                }
            ],
            "analytical_traits": ["processed", "salted"],
        },
        headers=auth_headers(),
    )

    assert replaced.status_code == 200
    assert [item["group_key"] for item in replaced.json()["group_contributions"]] == [
        "refined_grains"
    ]
    assert replaced.json()["analytical_traits"] == ["processed", "salted"]


def test_wave1_food_hard_delete_cascades_classification_children() -> None:
    with session_fixture() as session:
        food = create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(
                    name="Delete classification",
                    group_data_status="known",
                    group_data_completeness="complete",
                    group_contributions=[
                        {
                            "group_key": "seafood",
                            "amount_per_100_basis": 100,
                            "data_status": "known",
                        }
                    ],
                    analytical_traits=["omega3_rich_seafood"],
                )
            ),
        )
        assert session.exec(
            select(FoodGroupContribution).where(FoodGroupContribution.food_id == food.id)
        ).one()
        assert session.exec(
            select(FoodAnalyticalTrait).where(FoodAnalyticalTrait.food_id == food.id)
        ).one()

        delete_food(session, TEST_PRINCIPAL, food.id)

        assert (
            session.exec(
                select(FoodGroupContribution).where(FoodGroupContribution.food_id == food.id)
            ).first()
            is None
        )
        assert (
            session.exec(
                select(FoodAnalyticalTrait).where(FoodAnalyticalTrait.food_id == food.id)
            ).first()
            is None
        )
