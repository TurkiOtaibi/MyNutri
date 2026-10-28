"""Real application admission/lifecycle acceptance on a named disposable database."""

from datetime import datetime, timezone
import os
import secrets
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlmodel import Session, select

from app.core.calendar import current_diary_date
from app.core.config import get_settings
from app.db.session import engine
from app.main import app
from app.models import Principal
from app.ops.internal_admin import manage_admin


def main() -> None:
    url = make_url(get_settings().database_url)
    if (
        os.environ.get("INTERNAL_AUTH_ACCEPTANCE_DISPOSABLE") != "mynutri_test_internal_auth_ci"
        or url.host not in {"127.0.0.1", "localhost"}
        or url.database != "mynutri_test_internal_auth_ci"
    ):
        raise RuntimeError("Acceptance requires the named disposable loopback PostgreSQL database.")
    admin_password = secrets.token_urlsafe(24)
    password = secrets.token_urlsafe(24)
    new_password = secrets.token_urlsafe(24)
    with Session(engine) as session:
        if session.exec(select(Principal)).first() is not None:
            raise RuntimeError("Acceptance requires an empty disposable application database.")
        manage_admin(session, "create", "AcceptanceAdmin", admin_password, datetime.now(timezone.utc))

    # No dependency overrides: requests exercise the actual app, auth dependencies,
    # schema validation, services and PostgreSQL commits.
    with TestClient(app) as client:
        def request(method, path, expected=200, token=None, **kwargs):
            headers = kwargs.pop("headers", {})
            if token:
                headers["Authorization"] = "Bearer " + token
            response = client.request(method, path, headers=headers, **kwargs)
            if response.status_code != expected:
                raise AssertionError(f"Acceptance {method} {path}: unexpected status {response.status_code}")
            return response

        def login(username, secret):
            return request("POST", "/auth/login", json={"username": username, "password": secret}).json()["access_token"]

        def denied(token):
            response = request("GET", "/account/me", 401, token)
            assert response.headers["cache-control"] == "no-store"

        admin = login("AcceptanceAdmin", admin_password)
        request("GET", "/account/me", 403, admin)
        request("POST", "/auth/change-password", token=admin,
                json={"current_password": admin_password, "new_password": new_password})
        users = []
        for username in ("AcceptanceOne", "AcceptanceTwo"):
            result = request("POST", "/admin/accounts", 201, admin,
                             headers={"Idempotency-Key": str(uuid4())},
                             json={"username": username, "display_name": username,
                                   "initial_password": password}).json()
            token = login(username, password)
            request("GET", "/profile", 403, token)
            request("POST", "/auth/change-password", token=token,
                    json={"current_password": password, "new_password": new_password})
            users.append((username, result["principal_id"], token))
        one_name, one_id, one = users[0]
        _, two_id, two = users[1]
        today = current_diary_date().isoformat()
        for token, weight in ((one, 70), (two, 90)):
            payload = {"sex": "male", "birth_date": "1990-01-01", "height_cm": 175,
                       "weight_kg": weight, "activity_level": "moderate", "goal": "maintain",
                       "protein_per_kg": 1.2, "fat_pct": 0.25, "effective_from": today}
            preview = request("POST", "/profile/preview", token=token, json=payload).json()
            request("POST", "/target-plans", 201, token,
                    headers={"Idempotency-Key": str(uuid4())},
                    json={**payload, "confirmed": True, "expected_preview_hash": preview["preview_hash"]})
        assert request("GET", "/profile", token=one).json()["weight_kg"] == 70
        assert request("GET", "/profile", token=two).json()["weight_kg"] == 90
        plans_one = request("GET", "/target-plans", token=one).json()
        plans_two = request("GET", "/target-plans", token=two).json()
        assert plans_one != plans_two
        request("GET", f"/admin/users/{two_id}", 403, one)
        food = request("POST", "/foods", 201, admin, json={
            "name": "Acceptance Food", "primary_category": "other", "subcategory": "other",
            "nutrition_basis": "per_100g", "default_unit_type": "serving", "unit_amount": 100,
            "unit_basis": "g", "calories": 180, "protein_g": 10, "carb_g": 20, "fat_g": 6,
            "nutrition_data_source": "estimated",
        }).json()
        diary = request("POST", "/diary/entries", 201, one, json={
            "food_id": food["id"], "entry_date": today, "quantity": 1, "meal_type": "lunch",
        }).json()
        assert request("GET", "/diary/entries", token=two).json() == []
        request("DELETE", f"/diary/entries/{diary['id']}", 404, two)
        labs = request("POST", "/labs/results", 201, one,
                       headers={"Idempotency-Key": str(uuid4())}, json={
                           "test_date": today, "note": "Synthetic acceptance note",
                           "results": [{"test_key": "hba1c", "entered_value": "5.2", "entered_unit": "%"}],
                       }).json()
        request("DELETE", f"/labs/results/{labs['result_ids'][0]}", 404, two)
        assert "Synthetic acceptance note" not in request("GET", "/labs/tests/hba1c", token=two).text

        other = login(one_name, new_password)
        request("POST", "/auth/change-password", token=one,
                json={"current_password": new_password, "new_password": password})
        denied(other)
        request("GET", "/account/me", token=one)
        request("PUT", f"/admin/accounts/{one_id}/password", 204, admin,
                json={"new_password": new_password})
        denied(one)
        one = login(one_name, new_password)
        request("GET", "/account/me", token=one)
        request("PUT", f"/admin/accounts/{one_id}/status", token=admin, json={"enabled": False})
        denied(one)
        request("PUT", f"/admin/accounts/{one_id}/status", token=admin, json={"enabled": True})
        denied(one)
        one = login(one_name, new_password)
        request("POST", "/auth/logout", 204, one)
        denied(one)
        one = login(one_name, new_password)
        request("DELETE", f"/admin/accounts/{one_id}", token=admin,
                json={"confirm_username": one_name})
        denied(one)
        request("GET", "/account/me", token=two)
        request("GET", "/account/me", 401, headers={"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.e30.c2ln"})
    print("Internal auth acceptance passed: isolation, forced change and immediate revocation.")


if __name__ == "__main__":
    main()
