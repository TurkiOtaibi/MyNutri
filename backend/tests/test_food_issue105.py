from datetime import date
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.models import DiaryEntry
from app.schemas import FoodCreate
from app.services.food import create_food, duplicate_key
from labs_fixtures import run_labs_alembic
from test_foods import food_payload


def test_duplicate_identity_uses_normalized_brand_and_preserves_serving_definition():
    original = food_payload(brand=" STRAẞE   Brand ")
    assert duplicate_key(original) == duplicate_key(food_payload(brand="strasse brand"))
    assert duplicate_key(original) != duplicate_key(food_payload(brand="Other"))
    assert duplicate_key(food_payload(brand=None)) == duplicate_key(food_payload(brand="  "))
    assert duplicate_key(original) != duplicate_key(food_payload(brand="strasse brand", unit_amount=200))


def test_brand_normalization_and_true_duplicates(labs_postgresql_session, lab_admin):
    session = labs_postgresql_session
    first = create_food(session, lab_admin.context, FoodCreate(**food_payload(brand=" Brand A ")))
    second = create_food(session, lab_admin.context, FoodCreate(**food_payload(brand="Brand B")))
    assert first.id != second.id
    assert first.normalized_brand == "brand a"
    with pytest.raises(HTTPException) as error:
        create_food(session, lab_admin.context, FoodCreate(**food_payload(brand=" BRAND   a ")))
    assert error.value.status_code == 422
    with pytest.raises(IntegrityError), session.begin_nested():
        session.execute(text("UPDATE food SET normalized_brand='brand a' WHERE id=:id"), {"id": second.id})


@pytest.mark.parametrize("brand", [None, "", "   "])
def test_unbranded_duplicates_remain_rejected(labs_postgresql_session, lab_admin, brand):
    create_food(labs_postgresql_session, lab_admin.context, FoodCreate(**food_payload(brand=None)))
    with pytest.raises(HTTPException) as error:
        create_food(labs_postgresql_session, lab_admin.context, FoodCreate(**food_payload(brand=brand)))
    assert error.value.status_code == 422


def test_food_usage_counts_are_admin_only_and_aggregate_only(
    labs_client, labs_postgresql_session, lab_admin, lab_owner, other_lab_owner, as_actor
):
    session = labs_postgresql_session
    food = create_food(session, lab_admin.context, FoodCreate(**food_payload()))
    path = f"/foods/{food.id}/usage"
    assert labs_client.get(path).status_code == 403
    assert labs_client.get(f"/foods/{uuid4()}/usage").status_code == 403
    as_actor(lab_admin)
    assert labs_client.get(path).json() == {"diary_entries": 0, "users": 0}
    for owner in [lab_owner, lab_owner, other_lab_owner]:
        session.add(DiaryEntry(principal_id=owner.id, food_id=food.id, entry_date=date(2026, 1, 1), quantity=1,
                               recorded_unit_type=food.default_unit_type, recorded_unit_amount=food.unit_amount,
                               recorded_unit_basis=food.unit_basis))
    session.commit()
    response = labs_client.get(path)
    assert response.status_code == 200
    assert response.json() == {"diary_entries": 3, "users": 2}
    assert labs_client.get(f"/foods/{uuid4()}/usage").status_code == 404


def test_exact_name_search_normalizes_and_finds_all_brands(labs_client, labs_postgresql_session, lab_admin):
    for brand in ["A", "B"]:
        create_food(labs_postgresql_session, lab_admin.context, FoodCreate(**food_payload(name="  Same   Name ", brand=brand)))
    response = labs_client.get("/foods", params={"exact_name": " SAME  name ", "page_size": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1
    assert labs_client.get("/foods", params={"exact_name": "Same"}).json()["total"] == 0


@pytest.mark.migration
def test_brand_migration_backfill_downgrade_and_collision_guard(labs_postgresql_database, labs_postgresql_session, lab_admin):
    session = labs_postgresql_session
    food = create_food(session, lab_admin.context, FoodCreate(**food_payload(brand="  STRAẞE   Brand  ")))
    food_id = food.id
    session.close()
    run_labs_alembic("downgrade", "b6e4c2a78190")
    run_labs_alembic("upgrade", "head")
    with labs_postgresql_database.engine.connect() as connection:
        assert connection.execute(text("SELECT normalized_brand FROM food WHERE id=:id"), {"id": food_id}).scalar_one() == "strasse brand"
    unique = inspect(labs_postgresql_database.engine).get_unique_constraints("food")
    assert "normalized_brand" in next(item for item in unique if item["name"] == "uq_food_catalog_duplicate")["column_names"]
    assert "No new upgrade operations detected" in run_labs_alembic("check").stdout
    create_food(session, lab_admin.context, FoodCreate(**food_payload(brand="Different")))
    session.close()
    blocked = run_labs_alembic("downgrade", "b6e4c2a78190", check=False)
    assert blocked.returncode != 0
    assert "FOOD_BRAND_DOWNGRADE_COLLISION" in blocked.stderr
