from app.models import Food
from app.services.diary import make_snapshot, totals_from_snapshot


def test_diary_snapshot_freezes_food_values() -> None:
    food = Food(
        name="Greek yogurt",
        serving_label="170 g",
        calories=120,
        protein_g=18,
        carb_g=7,
        fat_g=0,
        fiber_g=1,
    )

    snapshot = make_snapshot(food)
    food.calories = 200

    totals = totals_from_snapshot(snapshot, 2)

    assert snapshot["calories"] == 120
    assert totals.calories == 240
    assert totals.protein_g == 36
    assert totals.net_carbs_g == 12
