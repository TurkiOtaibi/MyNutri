from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db.session import get_session
from app.main import app
from app.models import DefaultUnitType, DiaryEntry, NutritionBasis, UnitBasis
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


def session_fixture() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def food_payload(**overrides):
    payload = {
        "name": "Greek Yogurt",
        "brand": "Local",
        "category": "Dairy",
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
        create_food(session, FoodCreate.model_validate(food_payload(name="Greek   Yogurt")))

        with pytest.raises(HTTPException) as error:
            create_food(session, FoodCreate.model_validate(food_payload(name=" greek yogurt ")))

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

    response = api_client.post("/foods", json=food_json(sugar_g=3, added_sugar_g=4), headers=auth_headers())
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

    response = api_client.post("/foods", json=food_json(name=" greek yogurt "), headers=auth_headers())
    errors = error_by_field(response)

    assert errors["name"]["code"] == "duplicate_food"
    assert errors["name"]["msg"] == DUPLICATE_FOOD_MESSAGE


def test_food_api_update_returns_structured_arabic_errors_for_direct_invalid_field(api_client: TestClient) -> None:
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


def test_food_api_update_returns_structured_arabic_errors_after_merge(api_client: TestClient) -> None:
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
        create_food(session, FoodCreate.model_validate(food_payload(default_unit_type=DefaultUnitType.serving)))
        create_food(session, FoodCreate.model_validate(food_payload(default_unit_type=DefaultUnitType.cup)))

        assert len(list_foods(session)) == 2


def test_deleted_food_does_not_block_duplicate_recreation() -> None:
    with session_fixture() as session:
        food = create_food(session, FoodCreate.model_validate(food_payload()))
        delete_food(session, food.id)
        recreated = create_food(session, FoodCreate.model_validate(food_payload()))

        assert recreated.id != food.id
        assert len(list_foods(session)) == 1


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
            FoodCreate.model_validate(food_payload(name="Arabic Oats", category="Breakfast")),
        )
        create_food(
            session,
            FoodCreate.model_validate(food_payload(name="Other Oats", category="Snacks")),
        )
        create_food(
            session,
            FoodCreate.model_validate(food_payload(name="Plain Oats", category=None)),
        )

        breakfast = list_foods_page(session, search="oats", category="Breakfast")
        assert [food.name for food in breakfast.items] == ["Arabic Oats"]
        assert breakfast.total == 1
        assert breakfast.categories == ["Breakfast", "Snacks"]
        assert breakfast.uncategorized_count == 1

        uncategorized = list_foods_page(session, category=UNCATEGORIZED_CATEGORY)
        assert [food.name for food in uncategorized.items] == ["Plain Oats"]


def test_food_search_matches_brand_for_diary_picker() -> None:
    with session_fixture() as session:
        create_food(
            session,
            FoodCreate.model_validate(food_payload(name="Arabic oats", brand="Gullon Oaty")),
        )
        create_food(
            session,
            FoodCreate.model_validate(food_payload(name="Other food", brand="Different")),
        )

        legacy_results = list_foods(session, "gullon")
        paged_results = list_foods_page(session, search="GULLON")

        assert [food.name for food in legacy_results] == ["Arabic oats"]
        assert [food.name for food in paged_results.items] == ["Arabic oats"]


def test_food_page_sorts_by_derived_serving_calories_and_protein() -> None:
    with session_fixture() as session:
        create_food(
            session,
            FoodCreate.model_validate(
                food_payload(name="Small Serving", calories=500, protein_g=20, unit_amount=10)
            ),
        )
        create_food(
            session,
            FoodCreate.model_validate(
                food_payload(name="Large Serving", calories=100, protein_g=8, unit_amount=100)
            ),
        )

        by_calories = list_foods_page(session, sort="calories")
        assert [food.name for food in by_calories.items] == ["Large Serving", "Small Serving"]

        by_protein = list_foods_page(session, sort="protein")
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
        food = create_food(session, FoodCreate.model_validate(food_payload()))
        entry = DiaryEntry(
            entry_date=date(2026, 7, 9),
            food_id=food.id,
            quantity=1,
            nutrition_snapshot=make_snapshot(food, 1),
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        delete_food(session, food.id)
        response = to_entry_response(entry)

        assert response.nutrition_snapshot.name == "Greek Yogurt"
        assert response.nutrition_snapshot.nutrition_basis == NutritionBasis.per_100g
        assert response.totals.calories == 204
