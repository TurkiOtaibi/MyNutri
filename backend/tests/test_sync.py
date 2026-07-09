import os
from pathlib import Path
from uuid import uuid4

DB_PATH = Path("test-sync.db")
DB_PATH.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///./test-sync.db"
os.environ["SINGLE_USER_TOKEN"] = "dev-token"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def test_sync_push_is_ordered_and_idempotent() -> None:
    headers = {"Authorization": "Bearer dev-token"}
    food_id = str(uuid4())
    entry_id = str(uuid4())
    operations = [
        {
            "method": "POST",
            "path": "/foods",
            "client_id": "1",
            "created_at": "2026-07-08T10:00:00Z",
            "body": {
                "id": food_id,
                "name": "Batch food",
                "serving_label": "1 serving",
                "serving_grams": None,
                "calories": 300,
                "protein_g": 20,
                "carb_g": 25,
                "fat_g": 8,
                "saturated_fat_g": None,
                "trans_fat_g": None,
                "cholesterol_mg": None,
                "sodium_mg": None,
                "fiber_g": 5,
                "total_sugars_g": None,
                "added_sugar_g": None,
            },
        },
        {
            "method": "PUT",
            "path": f"/foods/{food_id}",
            "client_id": "2",
            "created_at": "2026-07-08T10:01:00Z",
            "body": {"calories": 350},
        },
        {
            "method": "POST",
            "path": "/diary",
            "client_id": "3",
            "created_at": "2026-07-08T10:02:00Z",
            "body": {
                "id": entry_id,
                "entry_date": "2026-07-08",
                "food_id": food_id,
                "quantity": 2,
            },
        },
    ]

    with TestClient(app) as client:
        first = client.post("/sync/push", json={"operations": operations}, headers=headers)
        second = client.post("/sync/push", json={"operations": operations}, headers=headers)
        pull = client.get("/sync/pull", headers=headers)

    assert first.status_code == 200
    assert first.json() == {"accepted": 3, "accepted_client_ids": ["1", "2", "3"], "rejected": []}
    assert second.status_code == 200
    assert second.json()["rejected"] == []
    assert len(pull.json()["foods"]) == 1
    assert len(pull.json()["diary_entries"]) == 1
    assert pull.json()["diary_entries"][0]["totals"]["calories"] == 700
