"""Creation requires a meal; persisted legacy meals retain their existing API rights."""

from datetime import date

import pytest
from sqlmodel import select

from app.models import DiaryEntry, MealType
from test_target_plans import seed_food


@pytest.mark.parametrize("meal", ["breakfast", "lunch", "dinner", "snack"])
def test_create_accepts_each_explicit_meal(labs_client, labs_postgresql_session, lab_owner, meal):
    food = seed_food(labs_postgresql_session, lab_owner.id)
    response = labs_client.post(
        "/diary/entries",
        json={
            "food_id": str(food.id),
            "entry_date": "2026-01-01",
            "quantity": 1,
            "meal_type": meal,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["meal_type"] == meal


@pytest.mark.parametrize("meal", ["missing", None, "unspecified", "brunch"])
def test_create_rejects_missing_or_nonstandard_meal_without_writing(
    labs_client,
    labs_postgresql_session,
    lab_owner,
    meal,
):
    food = seed_food(labs_postgresql_session, lab_owner.id)
    body = {"food_id": str(food.id), "entry_date": "2026-01-01", "quantity": 1}
    if meal != "missing":
        body["meal_type"] = meal
    response = labs_client.post("/diary/entries", json=body)
    assert response.status_code == 422, response.text
    assert response.json()["detail"][0]["code"] == "DIARY_MEAL_REQUIRED"
    assert (
        response.json()["detail"][0]["msg"]
        == "اختر وجبة لإضافة الطعام: فطور أو غداء أو عشاء أو سناك."
    )
    assert labs_postgresql_session.exec(select(DiaryEntry)).all() == []


def test_legacy_unspecified_remains_readable_editable_and_deletable(
    labs_client,
    labs_postgresql_session,
    lab_owner,
):
    food = seed_food(labs_postgresql_session, lab_owner.id)
    entry = DiaryEntry(
        principal_id=lab_owner.id,
        food_id=food.id,
        entry_date=date(2026, 1, 1),
        quantity=1,
        meal_type=MealType.unspecified,
        recorded_unit_type=food.default_unit_type,
        recorded_unit_amount=food.unit_amount,
        recorded_unit_basis=food.unit_basis,
    )
    labs_postgresql_session.add(entry)
    labs_postgresql_session.commit()
    entry_id = str(entry.id)
    response = labs_client.get("/diary/entries", params={"entry_date": "2026-01-01"})
    assert response.status_code == 200
    assert response.json()[0]["meal_type"] == "unspecified"
    response = labs_client.patch(f"/diary/entries/{entry_id}", json={"quantity": 2})
    assert response.status_code == 200, response.text
    assert response.json()["meal_type"] == "unspecified"
    assert response.json()["quantity"] == 2
    response = labs_client.patch(f"/diary/entries/{entry_id}", json={"meal_type": "unspecified"})
    assert response.status_code == 200
    assert response.json()["meal_type"] == "unspecified"
    assert labs_client.delete(f"/diary/entries/{entry_id}").status_code == 204
    assert labs_postgresql_session.exec(select(DiaryEntry)).all() == []
