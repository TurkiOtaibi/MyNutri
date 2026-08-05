from __future__ import annotations

from base64 import urlsafe_b64encode
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import json
import os
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api.routes import admin as admin_route
from app.core.auth import AuthClaims, PrincipalContext, get_token_verifier
from app.db.session import get_session
from app.main import app
from app.models import ActivityLevel, DiaryEntry, Goal, Principal, PrincipalRole, Profile, Sex, TargetProvenance

ADMIN_ID = UUID("00000000-0000-0000-0000-0000000000aa")
USER_ID = UUID("00000000-0000-0000-0000-0000000000bb")
OTHER_ID = UUID("00000000-0000-0000-0000-0000000000cc")
ADMIN_AUTH_ID = UUID("10000000-0000-0000-0000-0000000000aa")
USER_AUTH_ID = UUID("10000000-0000-0000-0000-0000000000bb")


class _Verifier:
    def verify(self, token: str) -> AuthClaims:
        if token == "admin":
            return AuthClaims(ADMIN_AUTH_ID, "admin@example.com", "Admin")
        if token == "user":
            return AuthClaims(USER_AUTH_ID, "user@example.com", "User")
        raise ValueError("invalid token")


@pytest.fixture
def admin_context():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    session.add_all(
        [
            Principal(
                id=ADMIN_ID,
                auth_user_id=ADMIN_AUTH_ID,
                email="admin@example.com",
                role=PrincipalRole.admin,
            ),
            Principal(id=USER_ID, auth_user_id=USER_AUTH_ID, email="user@example.com"),
            Principal(id=OTHER_ID, auth_user_id=uuid4(), email="other@example.com"),
        ]
    )
    session.commit()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_token_verifier] = _Verifier
    client = TestClient(app)
    try:
        yield client, session
    finally:
        app.dependency_overrides.clear()
        client.close()
        session.close()


def _headers(token: str = "admin") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _cursor(payload: dict) -> str:
    return urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


@contextmanager
def _capture_statements(session: Session):
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(" ".join(statement.split()).lower())

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def _snapshot() -> dict:
    return {
        "food_id": None,
        "name": "Plan025 Food",
        "brand": None,
        "category": "other",
        "nutrition_basis": "per_100g",
        "default_unit_type": "serving",
        "unit_amount": 100,
        "unit_basis": "g",
        "calories": 100,
        "protein_g": 1,
        "carb_g": 10,
        "fat_g": 1,
    }


def _seed_diary(session: Session, principal_id: UUID, count: int) -> list[DiaryEntry]:
    created_at = datetime(2026, 8, 1, 12, tzinfo=timezone.utc)
    entries = [
        DiaryEntry(
            id=uuid5(NAMESPACE_URL, f"plan025-{principal_id}-{index}"),
            principal_id=principal_id,
            entry_date=(created_at - timedelta(days=index // 3)).date(),
            quantity=1,
            target_provenance=TargetProvenance.no_target_source,
            snapshot_schema_version=None,
            nutrition_snapshot=_snapshot(),
            created_at=created_at,
        )
        for index in range(count)
    ]
    session.add_all(entries)
    session.commit()
    return entries


@pytest.fixture
def plan025_postgresql_session():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for disposable PostgreSQL Plan 025 tests.")
    parsed = make_url(url)
    database = parsed.database or ""
    if (
        parsed.get_backend_name() != "postgresql"
        or parsed.host not in {"localhost", "127.0.0.1", "::1"}
        or not database.startswith("mynutri_test_")
    ):
        pytest.fail("Plan 025 requires a loopback mynutri_test_ PostgreSQL TEST_DATABASE_URL.")

    schema_name = f"isolated_plan025_{uuid4().hex}"
    admin_engine = sa_create_engine(url, isolation_level="AUTOCOMMIT")
    test_engine = None
    schema_created = False
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            schema_created = True
        test_engine = sa_create_engine(url, connect_args={"options": f"-csearch_path={schema_name}"})
        SQLModel.metadata.create_all(test_engine)
        with Session(test_engine) as session:
            session.add_all(
                [
                    Principal(id=ADMIN_ID, auth_user_id=ADMIN_AUTH_ID, role=PrincipalRole.admin),
                    Principal(id=USER_ID, auth_user_id=USER_AUTH_ID),
                    Principal(id=OTHER_ID, auth_user_id=uuid4()),
                ]
            )
            session.commit()
            yield session
    finally:
        if test_engine is not None:
            test_engine.dispose()
        if schema_created:
            with admin_engine.connect() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        admin_engine.dispose()


def test_plan025_admin_user_list_summary_queries_are_constant(admin_context) -> None:
    client, session = admin_context
    for index in range(100):
        principal = Principal(id=uuid4(), auth_user_id=uuid4(), email=f"user-{index}@example.com")
        session.add(principal)
        if index % 3 == 0:
            session.add(
                Profile(
                    principal_id=principal.id,
                    sex=Sex.male,
                    birth_date=date(1990, 1, 1),
                    height_cm=175,
                    weight_kg=80,
                    activity_level=ActivityLevel.moderate,
                    goal=Goal.maintain,
                )
            )
        if index % 2 == 0:
            _seed_diary(session, principal.id, 1)
    session.commit()

    counts: list[int] = []
    for page_size in (1, 20, 100):
        with _capture_statements(session) as statements:
            response = client.get("/admin/users", params={"page_size": page_size}, headers=_headers())
        assert response.status_code == 200, response.text
        assert len(response.json()["items"]) == page_size
        assert all(" for update" not in statement for statement in statements)
        assert not any(statement.startswith(("insert ", "update ", "delete ")) for statement in statements)
        counts.append(len(statements))
    assert counts == [3, 3, 3]
    profiled = client.get("/admin/users", params={"search": "user-0@example.com"}, headers=_headers())
    assert profiled.status_code == 200, profiled.text
    summary = profiled.json()["items"][0]
    assert summary["profile_complete"] is True
    assert summary["current_goal"] == "maintain"
    assert summary["last_activity_at"] is not None


def test_plan025_admin_diary_is_bounded_stable_and_owner_isolated(admin_context) -> None:
    client, session = admin_context
    _seed_diary(session, USER_ID, 101)
    other_entries = _seed_diary(session, OTHER_ID, 2)
    with _capture_statements(session) as statements:
        first = client.get(f"/admin/users/{USER_ID}/diary", headers=_headers())
    assert first.status_code == 200, first.text
    first_page = first.json()
    assert len(first_page["items"]) == 50
    assert first_page["next_cursor"]
    assert all(item["id"] not in {str(entry.id) for entry in other_entries} for item in first_page["items"])
    assert not any(statement.startswith(("insert ", "update ", "delete ")) for statement in statements)
    assert all(" for update" not in statement for statement in statements)
    cross_owner = client.get(
        f"/admin/users/{OTHER_ID}/diary",
        params={"cursor": first_page["next_cursor"]},
        headers=_headers(),
    )
    assert cross_owner.status_code == 200, cross_owner.text
    assert {item["id"] for item in cross_owner.json()["items"]}.issubset(
        {str(entry.id) for entry in other_entries}
    )

    second = client.get(
        f"/admin/users/{USER_ID}/diary",
        params={"cursor": first_page["next_cursor"], "limit": 100},
        headers=_headers(),
    )
    assert second.status_code == 200, second.text
    second_page = second.json()
    assert len(second_page["items"]) == 51
    assert second_page["next_cursor"] is None
    ids = [item["id"] for item in first_page["items"] + second_page["items"]]
    assert len(ids) == len(set(ids)) == 101
    filtered = client.get(
        f"/admin/users/{USER_ID}/diary",
        params={"entry_date": "2026-08-01", "limit": 2},
        headers=_headers(),
    )
    assert filtered.status_code == 200, filtered.text
    assert len(filtered.json()["items"]) == 2
    assert {item["entry_date"] for item in filtered.json()["items"]} == {"2026-08-01"}
    filtered_final = client.get(
        f"/admin/users/{USER_ID}/diary",
        params={
            "entry_date": "2026-08-01",
            "limit": 2,
            "cursor": filtered.json()["next_cursor"],
        },
        headers=_headers(),
    )
    assert filtered_final.status_code == 200, filtered_final.text
    assert len(filtered_final.json()["items"]) == 1
    assert filtered_final.json()["next_cursor"] is None
    empty = client.get(
        f"/admin/users/{USER_ID}/diary",
        params={"entry_date": "2025-01-01"},
        headers=_headers(),
    )
    assert empty.status_code == 200, empty.text
    assert empty.json() == {"items": [], "next_cursor": None}
    assert client.get(
        f"/admin/users/{USER_ID}/diary", params={"limit": 101}, headers=_headers()
    ).status_code == 422
    for cursor in (
        "not-a-cursor",
        _cursor({"entry_date": 1, "created_at": "2026-08-01T12:00:00", "id": str(uuid4())}),
        _cursor(
            {"entry_date": "2026-08-01", "created_at": "2026-08-01T12:00:00", "id": str(uuid4())}
        ),
        _cursor(
            {"entry_date": "20260801", "created_at": "2026-08-01T12:00:00+00:00", "id": str(uuid4())}
        ),
        _cursor(
            {
                "entry_date": "2026-08-01",
                "created_at": "2026-08-01T12:00:00",
                "id": str(uuid4()),
                "principal_id": str(OTHER_ID),
            }
        ),
        "e30",
    ):
        assert client.get(
            f"/admin/users/{USER_ID}/diary", params={"cursor": cursor}, headers=_headers()
        ).status_code == 422


@pytest.mark.parametrize("size", [1, 20, 100])
def test_plan025_postgresql_budgets_read_only_and_bounded_pages(
    plan025_postgresql_session: Session, size: int, monkeypatch
) -> None:
    session = plan025_postgresql_session
    for index in range(100):
        principal = Principal(id=uuid4(), auth_user_id=uuid4(), email=f"postgres-{index}@example.com")
        session.add(principal)
        session.flush()
        if index % 2 == 0:
            session.add(
                Profile(
                    principal_id=principal.id,
                    sex=Sex.male,
                    birth_date=date(1990, 1, 1),
                    height_cm=175,
                    weight_kg=80,
                    activity_level=ActivityLevel.moderate,
                    goal=Goal.maintain,
                )
            )
            _seed_diary(session, principal.id, 1)
    _seed_diary(session, USER_ID, 101)
    other_entries = _seed_diary(session, OTHER_ID, 1)

    def forbidden(*_args, **_kwargs):
        raise AssertionError("admin monitoring mutated session state")

    session.autoflush = False
    monkeypatch.setattr(session, "flush", forbidden)
    monkeypatch.setattr(session, "commit", forbidden)
    monkeypatch.setattr("app.services.target_plans._advance_lifecycle", forbidden)
    with _capture_statements(session) as statements:
        page = admin_route.list_users(
            page=1,
            page_size=size,
            _admin=PrincipalContext(ADMIN_ID, role=PrincipalRole.admin),
            session=session,
        )
    assert len(page.items) == size
    assert len(statements) == 2
    assert not any(statement.startswith(("insert ", "update ", "delete ")) for statement in statements)
    assert not any(" for update" in statement for statement in statements)

    principal = PrincipalContext(USER_ID)
    first = admin_route.admin_diary_page(session, principal, 50)
    second = admin_route.admin_diary_page(session, principal, 100, first.next_cursor)
    assert len(first.items) == 50
    assert len(second.items) == 51
    assert len({item.id for item in first.items + second.items}) == 101
    assert {item.id for item in first.items}.isdisjoint({entry.id for entry in other_entries})
    with _capture_statements(session) as invalid_statements:
        with pytest.raises(Exception):
            admin_route.admin_diary_page(session, principal, 50, "not-a-cursor")
    assert invalid_statements == []

    plan = session.exec(
        text(
            "EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM diary_entry "
            "WHERE principal_id = :principal_id "
            "ORDER BY entry_date DESC, created_at DESC, id DESC LIMIT 51"
        ),
        params={"principal_id": str(USER_ID)},
    ).all()
    assert plan
    # The representative plan remains bounded by LIMIT 51; no new index is added without
    # measured evidence that this bounded PostgreSQL query needs one.
    assert any("Limit" in str(row[0]) for row in plan)
