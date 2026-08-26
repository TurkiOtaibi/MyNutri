from __future__ import annotations

from base64 import urlsafe_b64encode
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine as sa_create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.routes import admin as admin_route
from app.core.auth import AuthClaims, PrincipalContext, get_token_verifier
from app.db.session import get_session
from app.main import app
from app.models import (
    ActivityLevel,
    BehaviorGoal,
    BehaviorGoalHistory,
    DiaryEntry,
    Goal,
    NutritionAnalysis,
    NutritionAnalysisRevision,
    NutritionAnalysisRevisionEvent,
    Principal,
    PrincipalRole,
    Profile,
    Sex,
    TargetProvenance,
    WeeklyPriorityRecommendation,
)
from app.services.pattern_analysis import analysis_history
import app.services.weekly_priorities as weekly_priority_service
from app.services.weekly_priorities import process_due_goals
from app.services.diary import AdminDiaryCursorError, _encode_admin_diary_cursor
from test_weekly_priorities import _persist_trackable_graph

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


@contextmanager
def _capture_executions(session: Session):
    executions: list[tuple[str, object]] = []

    def capture(_connection, _cursor, statement, parameters, _context, _executemany) -> None:
        executions.append((" ".join(statement.split()).lower(), parameters))

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        yield executions
    finally:
        event.remove(engine, "before_cursor_execute", capture)


def _parameter_uuids(parameters: object) -> set[UUID]:
    if isinstance(parameters, dict):
        values = tuple(parameters.values())
    elif isinstance(parameters, (list, tuple)):
        values = parameters
    else:
        values = (parameters,)
    return {value for value in values if isinstance(value, UUID)}


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
def plan025_postgresql_database():
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

    database_name = f"mynutri_test_plan025_{uuid4().hex[:12]}"
    admin_url = parsed.set(database="postgres").render_as_string(hide_password=False)
    admin_engine = sa_create_engine(admin_url, isolation_level="AUTOCOMMIT")
    test_url = parsed.set(database=database_name).render_as_string(hide_password=False)
    database_created = False
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
            database_created = True
        yield test_url
    finally:
        if database_created:
            with admin_engine.connect() as connection:
                connection.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                    ),
                    {"database_name": database_name},
                )
                connection.execute(text(f'DROP DATABASE "{database_name}"'))
        admin_engine.dispose()


@pytest.fixture
def plan025_postgresql_session(plan025_postgresql_database: str):
    schema_name = f"isolated_plan025_{uuid4().hex}"
    admin_engine = sa_create_engine(plan025_postgresql_database, isolation_level="AUTOCOMMIT")
    test_engine = None
    schema_created = False
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            schema_created = True
        test_engine = sa_create_engine(
            plan025_postgresql_database, connect_args={"options": f"-csearch_path={schema_name}"}
        )
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


def _run_alembic(url: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": url},
        text=True,
        capture_output=True,
        check=True,
    )


def _index_catalog(session: Session) -> dict[str, object]:
    row = (
        session.execute(
            text(
                "SELECT pg_get_indexdef(indexrelid) AS definition, indpred IS NULL AS no_predicate, "
                "indnkeyatts, indnatts, indoption::smallint[] AS options, "
                "array_agg(pg_get_indexdef(indexrelid, key_position, true) ORDER BY key_position) AS keys "
                "FROM pg_index JOIN pg_class ON pg_class.oid = indexrelid "
                "CROSS JOIN LATERAL generate_series(1, indnkeyatts) AS key_position "
                "WHERE indrelid = 'diary_entry'::regclass "
                "AND relname = 'ix_diary_entry_principal_date_created_id_desc' "
                "GROUP BY indexrelid, indpred, indnkeyatts, indnatts, indoption"
            )
        )
        .mappings()
        .one()
    )
    return dict(row)


def _assert_diary_index_catalog(session: Session) -> None:
    indexes = session.execute(
        text(
            "SELECT count(*) FROM pg_index JOIN pg_class ON pg_class.oid = indexrelid "
            "WHERE indrelid = 'diary_entry'::regclass "
            "AND relname = 'ix_diary_entry_principal_date_created_id_desc'"
        )
    ).scalar_one()
    assert indexes == 1
    catalog = _index_catalog(session)
    assert catalog["no_predicate"] is True
    assert catalog["indnkeyatts"] == catalog["indnatts"] == 4
    assert catalog["keys"] == ["principal_id", "entry_date", "created_at", "id"]
    assert catalog["options"] == [0, 3, 3, 3]
    assert str(catalog["definition"]).endswith(
        "USING btree (principal_id, entry_date DESC, created_at DESC, id DESC)"
    )


def _walk_plan(node: dict) -> list[dict]:
    return [
        node,
        *[descendant for child in node.get("Plans", []) for descendant in _walk_plan(child)],
    ]


def _explain(session: Session, statement: str, **params: object) -> dict:
    result = session.execute(
        text(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {statement}"), params
    ).scalar_one()
    return result[0]["Plan"]


def _assert_bounded_diary_index_plan(
    plan: dict,
    *,
    row_limit: int,
    require_cursor_boundary: bool = False,
    maximum_buffer_accesses: int | None = None,
) -> dict:
    nodes = _walk_plan(plan)
    assert plan["Node Type"] == "Limit"
    assert not any(node["Node Type"] in {"Sort", "Incremental Sort"} for node in nodes)
    diary_scans = [
        node
        for node in nodes
        if node["Node Type"] in {"Index Scan", "Index Only Scan"}
        and node.get("Relation Name") == "diary_entry"
    ]
    assert len(diary_scans) == 1
    scan = diary_scans[0]
    assert scan["Index Name"] == "ix_diary_entry_principal_date_created_id_desc"
    assert scan["Actual Rows"] <= row_limit
    assert scan["Actual Loops"] == 1
    index_condition = scan.get("Index Cond", "").lower()
    assert "principal_id" in index_condition
    assert not any(
        node["Node Type"] == "Seq Scan" and node.get("Relation Name") == "diary_entry"
        for node in nodes
    )
    if require_cursor_boundary:
        assert "row(entry_date, created_at, id) < row(" in index_condition
        assert not scan.get("Filter")
        assert scan.get("Rows Removed by Filter", 0) == 0
    if maximum_buffer_accesses is not None:
        buffer_accesses = scan.get("Shared Hit Blocks", 0) + scan.get("Shared Read Blocks", 0)
        assert buffer_accesses <= maximum_buffer_accesses
    return scan


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
            response = client.get(
                "/admin/users", params={"page_size": page_size}, headers=_headers()
            )
        assert response.status_code == 200, response.text
        assert len(response.json()["items"]) == page_size
        assert all(" for update" not in statement for statement in statements)
        assert not any(
            statement.startswith(("insert ", "update ", "delete ")) for statement in statements
        )
        counts.append(len(statements))
    assert counts == [3, 3, 3]
    profiled = client.get(
        "/admin/users", params={"search": "user-0@example.com"}, headers=_headers()
    )
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
    assert all(
        item["id"] not in {str(entry.id) for entry in other_entries} for item in first_page["items"]
    )
    assert not any(
        statement.startswith(("insert ", "update ", "delete ")) for statement in statements
    )
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
    assert (
        client.get(
            f"/admin/users/{USER_ID}/diary", params={"limit": 101}, headers=_headers()
        ).status_code
        == 422
    )
    for cursor in (
        "not-a-cursor",
        _cursor({"entry_date": 1, "created_at": "2026-08-01T12:00:00", "id": str(uuid4())}),
        _cursor(
            {"entry_date": "2026-08-01", "created_at": "2026-08-01T12:00:00", "id": str(uuid4())}
        ),
        _cursor(
            {
                "entry_date": "20260801",
                "created_at": "2026-08-01T12:00:00+00:00",
                "id": str(uuid4()),
            }
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
        assert (
            client.get(
                f"/admin/users/{USER_ID}/diary", params={"cursor": cursor}, headers=_headers()
            ).status_code
            == 422
        )


@pytest.mark.parametrize("size", [1, 20, 100])
def test_plan025_postgresql_budgets_read_only_and_bounded_pages(
    plan025_postgresql_session: Session, size: int, monkeypatch
) -> None:
    session = plan025_postgresql_session
    for index in range(100):
        principal = Principal(
            id=uuid4(), auth_user_id=uuid4(), email=f"postgres-{index}@example.com"
        )
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
    _seed_diary(session, USER_ID, 501)
    other_entries = _seed_diary(session, OTHER_ID, 301)

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
    assert not any(
        statement.startswith(("insert ", "update ", "delete ")) for statement in statements
    )
    assert not any(" for update" in statement for statement in statements)

    principal = PrincipalContext(USER_ID)
    first = admin_route.admin_diary_page(session, principal, 50)
    second = admin_route.admin_diary_page(session, principal, 100, first.next_cursor)
    assert len(first.items) == 50
    assert len(second.items) == 100
    assert len({item.id for item in first.items + second.items}) == 150
    assert {item.id for item in first.items}.isdisjoint({entry.id for entry in other_entries})
    with _capture_statements(session) as invalid_statements:
        with pytest.raises(AdminDiaryCursorError, match="^invalid cursor$"):
            admin_route.admin_diary_page(session, principal, 50, "not-a-cursor")
    assert invalid_statements == []

    session.execute(text("ANALYZE diary_entry"))
    first_plan = _explain(
        session,
        "SELECT id, entry_date, meal_type, quantity, nutrition_snapshot, snapshot_schema_version, "
        "created_at FROM diary_entry WHERE principal_id = CAST(:principal_id AS uuid) "
        "ORDER BY entry_date DESC, created_at DESC, id DESC LIMIT 51",
        principal_id=str(USER_ID),
    )
    boundary = first.items[-1]
    boundary_created_at = session.exec(
        select(DiaryEntry.created_at).where(DiaryEntry.id == boundary.id)
    ).one()
    cursor_plan = _explain(
        session,
        "SELECT id, entry_date, meal_type, quantity, nutrition_snapshot, snapshot_schema_version, "
        "created_at FROM diary_entry WHERE principal_id = CAST(:principal_id AS uuid) AND "
        "(entry_date, created_at, id) < "
        "(CAST(:entry_date AS date), CAST(:created_at AS timestamptz), CAST(:entry_id AS uuid)) "
        "ORDER BY entry_date DESC, created_at DESC, id DESC LIMIT 101",
        principal_id=str(USER_ID),
        entry_date=boundary.entry_date.isoformat(),
        created_at=boundary_created_at.isoformat(),
        entry_id=str(boundary.id),
    )
    _assert_bounded_diary_index_plan(first_plan, row_limit=51)
    _assert_bounded_diary_index_plan(
        cursor_plan,
        row_limit=101,
        require_cursor_boundary=True,
    )
    _assert_diary_index_catalog(session)


def test_plan025_postgresql_deep_cursor_uses_complete_bounded_index_seek(
    plan025_postgresql_session: Session,
) -> None:
    session = plan025_postgresql_session
    entry_count = 10_001
    cursor_offset = 9_000
    page_size = 50
    _seed_diary(session, USER_ID, entry_count)
    _seed_diary(session, OTHER_ID, entry_count)
    order = (DiaryEntry.entry_date.desc(), DiaryEntry.created_at.desc(), DiaryEntry.id.desc())
    boundary = session.exec(
        select(DiaryEntry.entry_date, DiaryEntry.created_at, DiaryEntry.id)
        .where(DiaryEntry.principal_id == USER_ID)
        .order_by(*order)
        .offset(cursor_offset)
        .limit(1)
    ).one()
    expected_ids = list(
        session.exec(
            select(DiaryEntry.id)
            .where(DiaryEntry.principal_id == USER_ID)
            .order_by(*order)
            .offset(cursor_offset + 1)
            .limit(page_size)
        ).all()
    )
    cursor = _encode_admin_diary_cursor(boundary.entry_date, boundary.created_at, boundary.id)

    with _capture_statements(session) as statements:
        page = admin_route.admin_diary_page(
            session,
            PrincipalContext(USER_ID),
            page_size,
            cursor,
        )
    assert [item.id for item in page.items] == expected_ids
    diary_statements = [
        statement
        for statement in statements
        if statement.startswith("select ") and " from diary_entry " in statement
    ]
    assert len(diary_statements) == 1
    assert (
        "(diary_entry.entry_date, diary_entry.created_at, diary_entry.id) < ("
        in diary_statements[0]
    )

    session.execute(text("ANALYZE diary_entry"))
    plan = _explain(
        session,
        "SELECT id, entry_date, meal_type, quantity, nutrition_snapshot, snapshot_schema_version, "
        "created_at FROM diary_entry WHERE principal_id = CAST(:principal_id AS uuid) AND "
        "(entry_date, created_at, id) < "
        "(CAST(:entry_date AS date), CAST(:created_at AS timestamptz), CAST(:entry_id AS uuid)) "
        "ORDER BY entry_date DESC, created_at DESC, id DESC LIMIT 51",
        principal_id=str(USER_ID),
        entry_date=boundary.entry_date.isoformat(),
        created_at=boundary.created_at.isoformat(),
        entry_id=str(boundary.id),
    )
    scan = _assert_bounded_diary_index_plan(
        plan,
        row_limit=page_size + 1,
        require_cursor_boundary=True,
        maximum_buffer_accesses=128,
    )
    assert scan.get("Rows Removed by Index Recheck", 0) == 0
    _assert_diary_index_catalog(session)


def test_plan025_migration_rehearsal_catalog_and_reversibility(
    plan025_postgresql_database: str,
) -> None:
    heads = _run_alembic(plan025_postgresql_database, "heads")
    assert heads.stdout.strip() == "22733dbf5249 (head)"
    _run_alembic(plan025_postgresql_database, "upgrade", "head")
    engine = sa_create_engine(plan025_postgresql_database)
    try:
        with Session(engine) as session:
            _assert_diary_index_catalog(session)
            session.execute(
                text(
                    "INSERT INTO principal (id, auth_user_id, role, created_at, updated_at) VALUES "
                    "(CAST(:principal_id AS uuid), CAST(:auth_id AS uuid), 'user', "
                    "TIMESTAMPTZ '2026-08-01 12:00:00+00', "
                    "TIMESTAMPTZ '2026-08-01 12:00:00+00')"
                ),
                {"principal_id": str(USER_ID), "auth_id": str(USER_AUTH_ID)},
            )
            session.execute(
                text(
                    "INSERT INTO diary_entry "
                    "(id, principal_id, entry_date, meal_type, quantity, target_provenance, nutrition_snapshot, created_at) "
                    "VALUES (CAST(:entry_id AS uuid), CAST(:principal_id AS uuid), DATE '2026-08-01', "
                    "'unspecified', 1, "
                    "'no_target_source', CAST(:snapshot AS jsonb), TIMESTAMPTZ '2026-08-01 12:00:00+00')"
                ),
                {
                    "entry_id": str(uuid4()),
                    "principal_id": str(USER_ID),
                    "snapshot": json.dumps(_snapshot()),
                },
            )
            session.commit()
            before = session.execute(text("SELECT count(*) FROM diary_entry")).scalar_one()
        _run_alembic(plan025_postgresql_database, "downgrade", "7c4a9d2e1f06")
        with Session(engine) as session:
            assert session.execute(text("SELECT count(*) FROM diary_entry")).scalar_one() == before
            assert (
                session.execute(
                    text(
                        "SELECT count(*) FROM pg_indexes WHERE tablename = 'diary_entry' "
                        "AND indexname = 'ix_diary_entry_principal_date_created_id_desc'"
                    )
                ).scalar_one()
                == 0
            )
        _run_alembic(plan025_postgresql_database, "upgrade", "head")
        with Session(engine) as session:
            _assert_diary_index_catalog(session)
            assert session.execute(text("SELECT count(*) FROM diary_entry")).scalar_one() == before
    finally:
        engine.dispose()
    _run_alembic(plan025_postgresql_database, "check")


def test_plan032_history_limit_100_uses_constant_bulk_queries(admin_context) -> None:
    _client, session = admin_context
    revisions = []
    for index in range(100):
        period_end = date(2026, 8, 17) - timedelta(days=index)
        series = NutritionAnalysis(
            principal_id=USER_ID,
            as_of_diary_date=period_end,
            calendar_timezone="Asia/Riyadh",
            interface_version=1,
        )
        session.add(series)
        session.flush()
        revision = NutritionAnalysisRevision(
            analysis_id=series.id,
            principal_id=USER_ID,
            revision=1,
            period_start=period_end - timedelta(days=6),
            period_end=period_end,
            previous_period_start=period_end - timedelta(days=13),
            previous_period_end=period_end - timedelta(days=7),
            analysis_rules_version="w3-analysis-1.1.0",
            source_versions={},
            source_input_hash=f"{index:064x}",
            content_hash=f"{index + 100:064x}",
            complete_day_count=4,
            previous_complete_day_count=4,
            result_status="available",
            analysis_document={},
            generated_at=datetime(2026, 8, 17, 8, tzinfo=timezone.utc),
            finalized_at=datetime(2026, 8, 17, 8, 0, 0, 1000, tzinfo=timezone.utc),
        )
        revisions.append(revision)
        session.add(revision)
    session.commit()

    with _capture_statements(session) as statements:
        page = analysis_history(session, PrincipalContext(USER_ID), 100, None)

    analysis_selects = [
        statement
        for statement in statements
        if statement.startswith("select ")
        and any(
            f" from {table} " in statement
            for table in (
                "nutrition_analysis_revision",
                "nutrition_analysis",
                "nutrition_analysis_revision_event",
            )
        )
    ]
    assert len(page.items) == 100
    assert page.next_cursor is None
    assert len(analysis_selects) == 3
    assert [item.period_end for item in page.items] == sorted(
        (item.period_end for item in page.items), reverse=True
    )


def test_plan033_due_batch_bulk_loads_sources_and_reminders(admin_context) -> None:
    _client, session = admin_context
    principal_id, source, _series, _revision, recommendation = _persist_trackable_graph(session)
    now = datetime.now(timezone.utc)
    for index in range(100):
        goal_id = uuid4()
        session.add(
            BehaviorGoal(
                id=goal_id,
                principal_id=principal_id,
                recommendation_id=recommendation.id,
                root_goal_id=goal_id,
                sequence_number=1,
                state="completed",
                version=1,
                rule_key="fruit_vegetable_gap",
                action_key="add_fruit_or_vegetable",
                weekly_target_count=1,
                day_mask=[],
                window_start=source.period_start,
                window_end=source.period_end - timedelta(days=1),
                rules_version="w3-priority-1.1.0",
                copy_version="w3-priority-ar-1.1.0",
                progress_document={
                    "window_start": source.period_start.isoformat(),
                    "window_end": (source.period_end - timedelta(days=1)).isoformat(),
                    "progress_count": 3,
                    "target_count": 1,
                    "progress_percent": 100,
                    "complete_day_count": 4,
                    "partial_day_count": 0,
                    "unregistered_day_count": 3,
                    "status": "achieved",
                    "as_of_diary_date": source.as_of_diary_date.isoformat(),
                    "source_day_versions": {},
                    "calculation_rules_version": "w3-priority-1.1.0",
                    "last_recomputed_at": now.isoformat(),
                },
                progress_revision=1,
                reminder_preference="disabled",
                completed_at=now,
            )
        )
    session.commit()
    with _capture_statements(session) as statements:
        result = process_due_goals(session, limit=100)
    reads = [statement for statement in statements if statement.startswith("select ")]
    assert result["processed"] == 100
    # Cohort/owner discovery, one bounded goal/reminder/recommendation batch,
    # and two bounded source-validation batches are constant in goal count.
    assert len(reads) <= 14


def _add_current_analysis_history(
    session: Session,
    *,
    principal_id: UUID,
    source,
    history_depth: int,
) -> NutritionAnalysis:
    series_rows = [
        NutritionAnalysis(
            id=uuid4(),
            principal_id=principal_id,
            as_of_diary_date=source.as_of_diary_date + timedelta(days=index),
            calendar_timezone="Asia/Riyadh",
        )
        for index in range(1, history_depth)
    ]
    session.add_all(series_rows)
    session.flush()
    revisions = [
        NutritionAnalysisRevision(
            id=uuid4(),
            analysis_id=series.id,
            principal_id=principal_id,
            revision=1,
            period_start=source.period_start,
            period_end=source.period_end,
            previous_period_start=source.previous_period_start,
            previous_period_end=source.previous_period_end,
            analysis_rules_version=source.analysis_rules_version,
            source_versions={},
            source_input_hash=series.id.hex * 2,
            content_hash=series.id.hex[::-1] * 2,
            complete_day_count=4,
            previous_complete_day_count=0,
            result_status="available",
            analysis_document={},
        )
        for series in series_rows
    ]
    session.add_all(revisions)
    session.flush()
    for series, revision in zip(series_rows, revisions, strict=True):
        series.current_revision_id = revision.id
        series.current_revision_number = revision.revision
        session.add(series)
    session.commit()
    return series_rows[-1]


@pytest.mark.parametrize("history_depth", [10, 100, 500])
def test_plan033_postgresql_source_authority_is_bounded_by_owner_and_bound_series(
    plan025_postgresql_session: Session,
    history_depth: int,
) -> None:
    session = plan025_postgresql_session
    graphs = [_persist_trackable_graph(session) for _ in range(2)]
    recommendation_ids = [graph[4].id for graph in graphs]
    expected_latest = {
        principal_id: _add_current_analysis_history(
            session,
            principal_id=principal_id,
            source=source,
            history_depth=history_depth,
        ).id
        for principal_id, source, _series, _revision, _recommendation in graphs
    }
    session.expunge_all()
    recommendations = list(
        session.exec(
            select(WeeklyPriorityRecommendation).where(
                WeeklyPriorityRecommendation.id.in_(recommendation_ids)
            )
        ).all()
    )
    materialized_series: set[UUID] = set()

    def record_series_load(series, _context) -> None:
        materialized_series.add(series.id)

    event.listen(NutritionAnalysis, "load", record_series_load)
    try:
        with _capture_statements(session) as statements:
            authority = weekly_priority_service._load_recommendation_source_authority(
                session, recommendations
            )
    finally:
        event.remove(NutritionAnalysis, "load", record_series_load)

    bound_ids = {row.source_analysis_id for row in recommendations}
    principal_ids = {row.principal_id for row in recommendations}
    assert set(authority.bound_by_id) == bound_ids
    assert {
        principal_id: series.id
        for principal_id, series in authority.latest_by_principal.items()
    } == expected_latest
    assert all(
        authority.bound_by_id[row.source_analysis_id].principal_id == row.principal_id
        for row in recommendations
    )
    assert materialized_series == bound_ids | set(expected_latest.values())
    assert len(materialized_series) <= len(bound_ids) + len(principal_ids)

    progress = weekly_priority_service._validate_recommendation_sources(
        recommendations,
        authority,
        allow_newer_revision=True,
        allow_insufficient_progress_evidence=True,
        require_trackable=True,
    )
    actions = weekly_priority_service._validate_recommendation_sources(
        recommendations, authority, require_trackable=True
    )
    assert {result.state for result in progress.values()} == {"VALID"}
    assert {result.state for result in actions.values()} == {"SUPERSEDED"}

    source_authority_selects = [
        statement
        for statement in statements
        if statement.startswith("select ")
        and any(
            f" from {table} " in statement
            for table in (
                "nutrition_analysis",
                "nutrition_analysis_revision",
                "nutrition_analysis_revision_event",
            )
        )
    ]
    assert len(source_authority_selects) == 4

    if history_depth == 500:
        session.execute(text("ANALYZE nutrition_analysis"))
        principal_a, principal_b = sorted(principal_ids)
        plan = _explain(
            session,
            "SELECT latest.* FROM nutrition_analysis AS latest "
            "JOIN (SELECT principal.id AS principal_id, "
            "(SELECT candidate.id FROM nutrition_analysis AS candidate "
            "WHERE candidate.principal_id=principal.id "
            "AND candidate.current_revision_id IS NOT NULL "
            "ORDER BY candidate.as_of_diary_date DESC, candidate.id DESC LIMIT 1) "
            "AS series_id FROM principal WHERE principal.id IN (:principal_a, :principal_b)) "
            "AS latest_by_principal ON latest.id=latest_by_principal.series_id",
            principal_a=principal_a,
            principal_b=principal_b,
        )
        nodes = _walk_plan(plan)
        latest_index_scans = [
            node
            for node in nodes
            if node.get("Index Name") == "ix_nutrition_analysis_principal_date_desc"
            and node["Node Type"] in {"Index Scan", "Index Only Scan"}
        ]
        assert latest_index_scans, plan
        assert not any(
            node["Node Type"] in {"Sort", "Incremental Sort"}
            and any(
                descendant.get("Relation Name") == "nutrition_analysis"
                for descendant in _walk_plan(node)
            )
            for node in nodes
        ), plan


def test_plan033_scheduler_reuses_one_source_authority_batch(
    plan025_postgresql_session: Session,
) -> None:
    session = plan025_postgresql_session
    graphs = [_persist_trackable_graph(session) for _ in range(2)]
    for principal_id, source, series, revision, recommendation in graphs:
        _add_due_goal(
            session,
            principal_id=principal_id,
            source=source,
            series=series,
            revision=revision,
            recommendation=recommendation,
            state="active",
            reviewed=False,
        )
    session.commit()

    with _capture_statements(session) as statements:
        result = process_due_goals(session, limit=100)

    authority_series_loads = [
        statement
        for statement in statements
        if statement.startswith("select nutrition_analysis.id, ")
        and " from nutrition_analysis " in statement
    ]
    authority_revision_loads = [
        statement
        for statement in statements
        if statement.startswith("select nutrition_analysis_revision.id, ")
        and " from nutrition_analysis_revision " in statement
    ]
    authority_event_loads = [
        statement
        for statement in statements
        if statement.startswith("select nutrition_analysis_revision_event.id, ")
        and " from nutrition_analysis_revision_event " in statement
    ]
    assert result["processed"] == 2
    assert len(authority_series_loads) == 2
    assert len(authority_revision_loads) == 1
    assert len(authority_event_loads) == 1


def _add_due_goal(
    session: Session,
    *,
    principal_id: UUID,
    source,
    series: NutritionAnalysis,
    revision: NutritionAnalysisRevision,
    recommendation,
    state: str,
    reviewed: bool,
) -> BehaviorGoal:
    now = datetime.now(timezone.utc)
    goal_id = uuid4()
    window_end = source.period_end if reviewed else source.period_end - timedelta(days=4)
    status = "achieved" if state == "completed" else "not_yet_reached"
    goal = BehaviorGoal(
        id=goal_id,
        principal_id=principal_id,
        recommendation_id=recommendation.id,
        root_goal_id=goal_id,
        sequence_number=1,
        state=state,
        version=1,
        rule_key="fruit_vegetable_gap",
        action_key="add_fruit_or_vegetable",
        weekly_target_count=3,
        day_mask=[],
        window_start=source.period_start,
        window_end=window_end,
        rules_version="w3-priority-1.1.0",
        copy_version="w3-priority-ar-1.1.0",
        progress_document={
            "window_start": source.period_start.isoformat(),
            "window_end": window_end.isoformat(),
            "progress_count": 3 if state == "completed" else 0,
            "target_count": 3,
            "progress_percent": 100 if state == "completed" else 0,
            "complete_day_count": 4,
            "partial_day_count": 0,
            "unregistered_day_count": 3,
            "status": status,
            "as_of_diary_date": source.as_of_diary_date.isoformat(),
            "source_day_versions": {},
            "calculation_rules_version": "w3-priority-1.1.0",
            "last_recomputed_at": now.isoformat(),
        },
        progress_revision=1,
        last_progress_analysis_id=series.id,
        last_progress_analysis_revision_id=revision.id,
        last_progress_analysis_revision=revision.revision,
        last_progress_attempt_analysis_id=series.id,
        last_progress_attempt_analysis_revision_id=revision.id,
        last_progress_attempt_analysis_revision=revision.revision,
        reminder_preference="disabled",
        completed_at=now - timedelta(days=2) if state == "completed" else None,
        reviewed_at=now - timedelta(days=1) if reviewed else None,
    )
    session.add(goal)
    return goal


def _locked_principals(executions: list[tuple[str, object]]) -> set[UUID]:
    return set().union(
        *(
            _parameter_uuids(parameters)
            for statement, parameters in executions
            if " from principal " in statement and " for update" in statement
        )
    )


def _principal_lock_parameter_order(executions: list[tuple[str, object]]) -> list[UUID]:
    for statement, parameters in executions:
        if " from principal " not in statement or " for update" not in statement:
            continue
        values = tuple(parameters.values()) if isinstance(parameters, dict) else parameters
        return [value for value in values if isinstance(value, UUID)]
    return []


def test_plan033_postgresql_due_claims_only_exact_locked_owner_cohort(
    plan025_postgresql_session: Session, monkeypatch
) -> None:
    session = plan025_postgresql_session
    principal_a, source_a, series_a, revision_a, recommendation_a = (
        _persist_trackable_graph(session)
    )
    principal_b, source_b, series_b, revision_b, recommendation_b = (
        _persist_trackable_graph(session)
    )
    invalidation = NutritionAnalysisRevisionEvent(
        revision_id=revision_a.id,
        principal_id=principal_a,
        event_type="day_reopened",
        reason="completed_day_reopened",
        source_day_version=2,
    )
    session.add(invalidation)
    event_goals = [
        _add_due_goal(
            session,
            principal_id=principal_a,
            source=source_a,
            series=series_a,
            revision=revision_a,
            recommendation=recommendation_a,
            state="completed",
            reviewed=True,
        )
        for _ in range(401)
    ]
    normal_goal = _add_due_goal(
        session,
        principal_id=principal_b,
        source=source_b,
        series=series_b,
        revision=revision_b,
        recommendation=recommendation_b,
        state="active",
        reviewed=False,
    )
    session.commit()
    monkeypatch.setattr(weekly_priority_service, "refresh_historical_analysis", lambda *_: None)

    with _capture_executions(session) as executions:
        result = process_due_goals(session, limit=100)

    locked = _locked_principals(executions)
    session.refresh(normal_goal)
    attempted = sum(
        1
        for goal in event_goals
        if session.get(BehaviorGoal, goal.id).last_progress_attempt_event_id == invalidation.id
    )
    assert result["processed"] == 101
    assert normal_goal.state == "incomplete"
    assert attempted == 100
    assert locked == {principal_a, principal_b}
    assert {principal_a, principal_b}.issubset(locked)


def test_plan033_postgresql_mixed_cohorts_lock_every_processed_owner(
    plan025_postgresql_session: Session, monkeypatch
) -> None:
    session = plan025_postgresql_session
    graphs = [_persist_trackable_graph(session) for _ in range(4)]
    goals = []
    for index, (principal_id, source, series, revision, recommendation) in enumerate(graphs):
        state, reviewed = ("active", False) if index in {0, 3} else ("completed", True)
        goals.append(
            _add_due_goal(
                session,
                principal_id=principal_id,
                source=source,
                series=series,
                revision=revision,
                recommendation=recommendation,
                state=state,
                reviewed=reviewed,
            )
        )
    principal_b, source_b, series_b, revision_b, _recommendation_b = graphs[1]
    next_document = source_b.model_copy(
        update={"source_analysis_revision": 2, "generated_at": datetime.now(timezone.utc)}
    ).model_dump(mode="json")
    next_revision = NutritionAnalysisRevision(
        id=uuid4(),
        analysis_id=series_b.id,
        principal_id=principal_b,
        revision=2,
        period_start=source_b.period_start,
        period_end=source_b.period_end,
        previous_period_start=source_b.previous_period_start,
        previous_period_end=source_b.previous_period_end,
        analysis_rules_version=source_b.analysis_rules_version,
        source_versions={},
        source_input_hash="d" * 64,
        content_hash="e" * 64,
        complete_day_count=4,
        previous_complete_day_count=0,
        result_status="available",
        analysis_document=next_document,
    )
    session.add(next_revision)
    session.commit()
    series_b.current_revision_id = next_revision.id
    series_b.current_revision_number = 2
    session.add(series_b)
    principal_c, _source_c, _series_c, revision_c, _recommendation_c = graphs[2]
    session.add(
        NutritionAnalysisRevisionEvent(
            revision_id=revision_c.id,
            principal_id=principal_c,
            event_type="day_version_changed",
            reason="diary_entry_changed",
            source_day_version=2,
        )
    )
    session.commit()
    monkeypatch.setattr(weekly_priority_service, "refresh_historical_analysis", lambda *_: None)

    with _capture_executions(session) as executions:
        result = process_due_goals(session, limit=100)

    locked = _locked_principals(executions)
    processed_owners = {goal.principal_id for goal in goals}
    assert result["processed"] == 4
    assert locked == processed_owners
    assert _principal_lock_parameter_order(executions) == sorted(processed_owners)


@pytest.mark.parametrize("event_source_count", [1, 10, 100])
def test_plan033_event_entity_hydration_is_one_bulk_query(
    plan025_postgresql_session: Session, monkeypatch, event_source_count: int
) -> None:
    session = plan025_postgresql_session
    for _ in range(event_source_count):
        principal_id, source, series, revision, recommendation = _persist_trackable_graph(session)
        session.add(
            NutritionAnalysisRevisionEvent(
                revision_id=revision.id,
                principal_id=principal_id,
                event_type="day_version_changed",
                reason="diary_entry_changed",
                source_day_version=2,
            )
        )
        _add_due_goal(
            session,
            principal_id=principal_id,
            source=source,
            series=series,
            revision=revision,
            recommendation=recommendation,
            state="completed",
            reviewed=True,
        )
    session.commit()
    monkeypatch.setattr(weekly_priority_service, "refresh_historical_analysis", lambda *_: None)

    with _capture_statements(session) as statements:
        result = process_due_goals(session, limit=event_source_count)

    event_entity_loads = [
        statement
        for statement in statements
        if statement.startswith(
            "select nutrition_analysis_revision_event.id, "
            "nutrition_analysis_revision_event.revision_id"
        )
        and "nutrition_analysis_revision_event.id in (" in statement
    ]
    ranked_event_queries = [
        statement
        for statement in statements
        if "row_number() over" in statement
        and "nutrition_analysis_revision_event" in statement
        and "event_rank" in statement
    ]
    event_point_loads = [
        statement
        for statement in statements
        if statement.startswith(
            "select nutrition_analysis_revision_event.id, "
            "nutrition_analysis_revision_event.revision_id"
        )
        and "nutrition_analysis_revision_event.id = " in statement
    ]
    assert result["processed"] == event_source_count
    assert len(ranked_event_queries) == 1
    assert len(event_entity_loads) == 1
    assert event_point_loads == []


def test_plan033_postgresql_finalized_revision_discovery_is_bounded_and_indexed(
    plan025_postgresql_session: Session,
) -> None:
    session = plan025_postgresql_session
    principal_id, source, series, first_revision, recommendation = _persist_trackable_graph(session)
    now = datetime(2026, 8, 26, 12, tzinfo=timezone.utc)
    next_document = source.model_copy(
        update={"source_analysis_revision": 2, "generated_at": now}
    ).model_dump(mode="json")
    next_revision = NutritionAnalysisRevision(
        id=uuid4(),
        analysis_id=series.id,
        principal_id=principal_id,
        revision=2,
        period_start=source.period_start,
        period_end=source.period_end,
        previous_period_start=source.previous_period_start,
        previous_period_end=source.previous_period_end,
        analysis_rules_version=source.analysis_rules_version,
        source_versions={},
        source_input_hash="b" * 64,
        content_hash="c" * 64,
        complete_day_count=4,
        previous_complete_day_count=0,
        result_status="available",
        analysis_document=next_document,
    )
    session.add(next_revision)
    session.commit()
    series.current_revision_id = next_revision.id
    series.current_revision_number = 2
    session.add(series)
    session.add_all(
        [
            BehaviorGoal(
                id=(goal_id := uuid4()),
                principal_id=principal_id,
                recommendation_id=recommendation.id,
                root_goal_id=goal_id,
                sequence_number=1,
                state="completed",
                version=1,
                rule_key="fruit_vegetable_gap",
                action_key="add_fruit_or_vegetable",
                weekly_target_count=3,
                day_mask=[],
                window_start=source.period_start,
                window_end=source.period_end,
                rules_version="w3-priority-1.1.0",
                copy_version="w3-priority-ar-1.1.0",
                progress_document={},
                progress_revision=1,
                last_progress_analysis_id=series.id,
                last_progress_analysis_revision_id=first_revision.id,
                last_progress_analysis_revision=1,
                last_progress_attempt_analysis_id=series.id,
                last_progress_attempt_analysis_revision_id=first_revision.id,
                last_progress_attempt_analysis_revision=1,
                reminder_preference="disabled",
                completed_at=now - timedelta(days=1),
                reviewed_at=now,
            )
            for _ in range(2_000)
        ]
    )
    session.commit()
    session.execute(text("ANALYZE behavior_goal"))
    plan = _explain(
        session,
        "SELECT goal.id FROM behavior_goal AS goal "
        "WHERE goal.state='completed' AND goal.reviewed_at IS NOT NULL "
        "AND goal.last_progress_attempt_analysis_revision_id IS NOT NULL "
        "AND EXISTS (SELECT 1 FROM weekly_priority_recommendation AS recommendation "
        "JOIN nutrition_analysis AS analysis "
        "ON analysis.id=recommendation.source_analysis_id "
        "AND analysis.principal_id=goal.principal_id "
        "WHERE recommendation.id=goal.recommendation_id "
        "AND recommendation.principal_id=goal.principal_id "
        "AND goal.last_progress_attempt_analysis_id=analysis.id "
        "AND analysis.current_revision_id IS NOT NULL "
        "AND analysis.current_revision_number IS NOT NULL "
        "AND goal.last_progress_attempt_analysis_revision < analysis.current_revision_number) "
        "ORDER BY goal.last_progress_attempt_analysis_id, "
        "goal.last_progress_attempt_analysis_revision, goal.window_end, goal.id LIMIT 100",
    )
    nodes = _walk_plan(plan)
    goal_scans = [
        node
        for node in nodes
        if node.get("Relation Name") == "behavior_goal"
        and node.get("Index Name") == "ix_behavior_goal_finalized_attempt_revision"
    ]
    assert len(goal_scans) == 1, plan
    assert goal_scans[0]["Node Type"] in {"Index Scan", "Index Only Scan"}
    assert not any(
        node["Node Type"] == "Seq Scan" and node.get("Relation Name") == "behavior_goal"
        for node in nodes
    )
    assert not any(node["Node Type"] in {"Sort", "Incremental Sort"} for node in nodes)
    assert plan["Node Type"] == "Limit" and plan["Actual Rows"] == 100


def test_plan033_postgresql_finalized_event_discovery_is_owner_source_indexed(
    plan025_postgresql_session: Session,
) -> None:
    session = plan025_postgresql_session
    principal_id, source, series, first_revision, recommendation = _persist_trackable_graph(
        session
    )
    other_principal, _other_source, _other_series, other_revision, _other_recommendation = (
        _persist_trackable_graph(session)
    )
    now = datetime(2026, 8, 26, 12, tzinfo=timezone.utc)
    event = NutritionAnalysisRevisionEvent(
        revision_id=first_revision.id,
        principal_id=principal_id,
        event_type="day_reopened",
        reason="completed_day_reopened",
        source_day_version=2,
        occurred_at=now,
    )
    session.add(event)
    session.add_all(
        [
            NutritionAnalysisRevisionEvent(
                revision_id=other_revision.id,
                principal_id=other_principal,
                event_type="day_version_changed",
                reason="diary_entry_changed",
                source_day_version=index + 1,
                occurred_at=now + timedelta(microseconds=index + 1),
            )
            for index in range(4_000)
        ]
    )
    session.add_all(
        [
            BehaviorGoal(
                id=(goal_id := uuid4()),
                principal_id=principal_id,
                recommendation_id=recommendation.id,
                root_goal_id=goal_id,
                sequence_number=1,
                state="completed",
                version=1,
                rule_key="fruit_vegetable_gap",
                action_key="add_fruit_or_vegetable",
                weekly_target_count=3,
                day_mask=[],
                window_start=source.period_start,
                window_end=source.period_end,
                rules_version="w3-priority-1.1.0",
                copy_version="w3-priority-ar-1.1.0",
                progress_document={},
                progress_revision=1,
                last_progress_analysis_id=series.id,
                last_progress_analysis_revision_id=first_revision.id,
                last_progress_analysis_revision=1,
                last_progress_attempt_analysis_id=series.id,
                last_progress_attempt_analysis_revision_id=first_revision.id,
                last_progress_attempt_analysis_revision=1,
                reminder_preference="disabled",
                completed_at=now - timedelta(days=1),
                reviewed_at=now,
            )
            for _ in range(2_000)
        ]
    )
    session.commit()
    session.execute(text("ANALYZE behavior_goal"))
    session.execute(text("ANALYZE nutrition_analysis_revision_event"))

    candidate_plan = _explain(
        session,
        "SELECT goal.id FROM behavior_goal AS goal "
        "WHERE goal.state='completed' AND goal.reviewed_at IS NOT NULL "
        "AND EXISTS (SELECT 1 FROM weekly_priority_recommendation AS recommendation "
        "JOIN nutrition_analysis_revision AS revision "
        "ON revision.analysis_id=recommendation.source_analysis_id "
        "AND revision.principal_id=goal.principal_id "
        "JOIN nutrition_analysis_revision_event AS event "
        "ON event.revision_id=revision.id AND event.principal_id=goal.principal_id "
        "WHERE recommendation.id=goal.recommendation_id "
        "AND recommendation.principal_id=goal.principal_id "
        "AND event.event_type IN ('day_reopened','day_version_changed',"
        "'target_source_changed','source_snapshot_corrected','source_version_unsupported') "
        "AND (goal.last_progress_attempt_event_id IS NULL "
        "OR (event.occurred_at,event.id) > "
        "(goal.last_progress_attempt_event_occurred_at,goal.last_progress_attempt_event_id))) "
        "ORDER BY goal.last_progress_attempt_event_occurred_at, "
        "goal.last_progress_attempt_event_id, goal.window_end, goal.id LIMIT 100",
    )
    candidate_nodes = _walk_plan(candidate_plan)
    assert any(
        node.get("Index Name") == "ix_behavior_goal_finalized_attempt_event"
        for node in candidate_nodes
    ), candidate_plan
    assert not any(
        node["Node Type"] == "Seq Scan" and node.get("Relation Name") == "behavior_goal"
        for node in candidate_nodes
    )
    assert candidate_plan["Node Type"] == "Limit" and candidate_plan["Actual Rows"] == 100

    event_plan = _explain(
        session,
        "SELECT event.id, event.occurred_at FROM nutrition_analysis_revision_event AS event "
        "WHERE event.principal_id=:principal_id AND event.revision_id=:revision_id "
        "AND event.event_type IN ('day_reopened','day_version_changed',"
        "'target_source_changed','source_snapshot_corrected','source_version_unsupported') "
        "ORDER BY event.occurred_at DESC, event.id DESC LIMIT 1",
        principal_id=principal_id,
        revision_id=first_revision.id,
    )
    event_nodes = _walk_plan(event_plan)
    assert any(
        node.get("Index Name")
        == "ix_nutrition_analysis_event_owner_revision_time_id"
        for node in event_nodes
    ), event_plan
    assert not any(
        node["Node Type"] == "Seq Scan"
        and node.get("Relation Name") == "nutrition_analysis_revision_event"
        for node in event_nodes
    )


def test_plan033_postgresql_history_keyset_uses_owner_scoped_index(
    plan025_postgresql_session: Session,
) -> None:
    session = plan025_postgresql_session
    target_principal, target_source, _target_series, _target_revision, target_recommendation = (
        _persist_trackable_graph(session)
    )
    other_principal, other_source, _other_series, _other_revision, other_recommendation = (
        _persist_trackable_graph(session)
    )
    now = datetime(2026, 8, 26, 12, tzinfo=timezone.utc)

    def add_goal(principal_id, source, recommendation):
        goal_id = uuid4()
        session.add(
            BehaviorGoal(
                id=goal_id,
                principal_id=principal_id,
                recommendation_id=recommendation.id,
                root_goal_id=goal_id,
                sequence_number=1,
                state="ended",
                version=1,
                rule_key="fruit_vegetable_gap",
                action_key="add_fruit_or_vegetable",
                weekly_target_count=3,
                day_mask=[],
                window_start=source.period_start,
                window_end=source.period_end,
                rules_version="w3-priority-1.1.0",
                copy_version="w3-priority-ar-1.1.0",
                progress_document={},
                progress_revision=1,
                reminder_preference="disabled",
                ended_at=now,
            )
        )
        session.commit()
        return goal_id

    target_goal = add_goal(target_principal, target_source, target_recommendation)
    other_goal = add_goal(other_principal, other_source, other_recommendation)
    target_rows: list[BehaviorGoalHistory] = []
    for index in range(1_500):
        target_rows.append(
            BehaviorGoalHistory(
                goal_id=target_goal,
                principal_id=target_principal,
                root_goal_id=target_goal,
                sequence_number=1,
                goal_version=index + 1,
                event_type="progress_updated",
                from_state="active",
                to_state="active",
                actor_type="system",
                occurred_at=now - timedelta(seconds=index),
                terms_progress_snapshot={},
            )
        )
    session.add_all(target_rows)
    session.add_all(
        [
            BehaviorGoalHistory(
                goal_id=other_goal,
                principal_id=other_principal,
                root_goal_id=other_goal,
                sequence_number=1,
                goal_version=index + 1,
                event_type="progress_updated",
                from_state="active",
                to_state="active",
                actor_type="system",
                occurred_at=now - timedelta(milliseconds=index),
                terms_progress_snapshot={},
            )
            for index in range(4_000)
        ]
    )
    session.commit()
    session.execute(text("ANALYZE behavior_goal_history"))
    cursor = target_rows[999]
    plan = _explain(
        session,
        "SELECT * FROM behavior_goal_history "
        "WHERE principal_id=:principal_id "
        "AND (occurred_at, id) < (:occurred_at, :history_id) "
        "ORDER BY occurred_at DESC, id DESC LIMIT 51",
        principal_id=target_principal,
        occurred_at=cursor.occurred_at,
        history_id=cursor.id,
    )
    nodes = _walk_plan(plan)
    history_scans = [
        node
        for node in nodes
        if node.get("Relation Name") == "behavior_goal_history"
        and node["Node Type"] in {"Index Scan", "Index Only Scan"}
    ]
    assert len(history_scans) == 1, plan
    assert history_scans[0]["Index Name"] == "ix_behavior_goal_history_principal_occurred_id"
    assert not any(node["Node Type"] in {"Sort", "Incremental Sort"} for node in nodes)
    assert not any(
        node["Node Type"] == "Seq Scan" and node.get("Relation Name") == "behavior_goal_history"
        for node in nodes
    )
    assert plan["Actual Rows"] == 51
