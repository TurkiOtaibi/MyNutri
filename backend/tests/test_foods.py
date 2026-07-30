import json
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import get_args
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Numeric, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.session import get_session
from app.core.auth import PrincipalContext, get_principal_context
from app.main import app
from app.models import (
    DefaultUnitType,
    DiaryEntry,
    FoodAnalyticalTrait,
    Food,
    FOOD_GROUP_NUMERIC_COLUMNS,
    FOOD_NUMERIC_COLUMNS,
    FoodGroupContribution,
    FoodStatus,
    NutritionBasis,
    Principal,
    PrincipalRole,
    UnitBasis,
)
from app.schemas import (
    FOOD_GROUP_NUMERIC_FIELDS,
    FOOD_NUMERIC_FIELDS,
    FOOD_RESPONSE_DERIVED_NUMERIC_FIELDS,
    OPTIONAL_NUTRIENT_MAX,
    FoodCreate,
    FoodGroupContributionInput,
    FoodPickerItem,
    FoodResponse,
    FoodUpdate,
)
from app.services.diary import make_snapshot, to_entry_response
from app.services.food import (
    archive_food_response,
    create_food,
    create_food_response,
    delete_food,
    list_foods,
    list_food_picker,
    list_foods_page,
    to_food_response,
    to_food_responses,
    update_food_response,
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
OTHER_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000002")
OTHER_PRINCIPAL = PrincipalContext(OTHER_PRINCIPAL_ID)


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
        "food_category_key": "other",
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
    app.dependency_overrides[get_principal_context] = lambda: PrincipalContext(
        TEST_PRINCIPAL_ID, role=PrincipalRole.admin
    )
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


@contextmanager
def capture_application_selects(session: Session):
    engine = session.get_bind()
    statements: list[str] = []

    def capture_cursor(
        _conn, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        normalized = " ".join(statement.split()).lower()
        if normalized.startswith("select "):
            statements.append(normalized)

    event.listen(engine, "before_cursor_execute", capture_cursor)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", capture_cursor)


@contextmanager
def client_for_session(session: Session):
    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_principal_context] = lambda: PrincipalContext(
        TEST_PRINCIPAL_ID, role=PrincipalRole.admin
    )
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()
        client.close()


def child_selects(statements: list[str]) -> list[str]:
    child_tables = ("food_group_contribution", "food_analytical_trait")
    return [statement for statement in statements if any(table in statement for table in child_tables)]


def create_plan013_representative_foods(session: Session) -> list[Food]:
    zero = create_food(
        session,
        TEST_PRINCIPAL,
        FoodCreate.model_validate(
            food_payload(name="Alpha Zero", food_category_key="other", sugar_g=None)
        ),
    )
    multiple = create_food(
        session,
        TEST_PRINCIPAL,
        FoodCreate.model_validate(
            food_payload(
                name="Beta Multiple",
                food_category_key="other",
                group_contributions=[
                    {
                        "group_key": "vegetables",
                        "amount_per_100_basis": 40,
                        "data_status": "estimated",
                    },
                    {
                        "group_key": "fruits",
                        "amount_per_100_basis": 60,
                        "data_status": "known",
                    },
                ],
                analytical_traits=["salted", "processed"],
            )
        ),
    )
    archived = create_food(
        session,
        TEST_PRINCIPAL,
        FoodCreate.model_validate(
            food_payload(
                name="Gamma Archived",
                food_category_key="sweets",
                group_contributions=[
                    {
                        "group_key": "fruits",
                        "amount_per_100_basis": 25,
                        "data_status": "known",
                    }
                ],
                analytical_traits=["sweetened"],
            )
        ),
    )
    archive_food_response(session, TEST_PRINCIPAL, archived.id)
    return [zero, multiple, archived]


def create_plan014_food(session: Session, name: str, **overrides) -> Food:
    return create_food(
        session,
        TEST_PRINCIPAL,
        FoodCreate.model_validate(food_payload(name=name, **overrides)),
    )


def create_plan014_entry(
    session: Session,
    food: Food | None,
    *,
    principal_id: UUID = TEST_PRINCIPAL_ID,
    created_at: datetime,
) -> DiaryEntry:
    entry = DiaryEntry(
        principal_id=principal_id,
        entry_date=created_at.date(),
        food_id=food.id if food else None,
        quantity=1,
        meal_type="snack",
        nutrition_snapshot={"food_id": str(food.id) if food else None, "name": food.name if food else "Deleted"},
        created_at=created_at,
    )
    session.add(entry)
    session.commit()
    return entry


@pytest.mark.plan014
def test_plan014_picker_route_contract_limits_cursor_and_precedence(api_client: TestClient) -> None:
    default = api_client.get("/foods/picker", headers=auth_headers())
    assert default.status_code == 200
    assert default.json() == {"items": [], "recent_items": [], "next_cursor": None}
    assert (
        api_client.get(
            "/foods/picker", params={"limit": 30}, headers=auth_headers()
        ).status_code
        == 200
    )

    for limit in (0, 31):
        invalid = api_client.get(
            "/foods/picker", params={"limit": limit}, headers=auth_headers()
        )
        assert invalid.status_code == 422

    for cursor in ("not-a-cursor", "e30", "eyJuYW1lIjoxLCJpZCI6ImJhZCJ9"):
        malformed = api_client.get(
            "/foods/picker", params={"cursor": cursor}, headers=auth_headers()
        )
        assert malformed.status_code == 422
        assert malformed.json()["error"]["code"] == "INVALID_CURSOR"
        assert malformed.json()["error"]["details"] == {}
        assert UUID(malformed.json()["error"]["request_id"])


@pytest.mark.plan014
def test_plan014_picker_max_page_is_bounded_and_has_opaque_continuation() -> None:
    with session_fixture() as session:
        for index in range(31):
            create_plan014_food(session, f"Bounded page {index:02}")

        result = list_food_picker(session, TEST_PRINCIPAL, limit=30)

        assert len(result.items) == 30
        assert result.next_cursor is not None
        assert "Bounded" not in result.next_cursor


@pytest.mark.plan014
def test_plan014_picker_closed_dto_search_and_stable_casefold_pagination() -> None:
    with session_fixture() as session:
        first = create_plan014_food(session, "ALPHA", brand="First Brand")
        second = create_plan014_food(
            session, "alpha", brand="Second Brand", unit_amount=171
        )
        create_plan014_food(session, "Beta", brand="Needle Brand")
        archived = create_plan014_food(session, "Archived Needle")
        archive_food_response(session, TEST_PRINCIPAL, archived.id)

        page_one = list_food_picker(session, TEST_PRINCIPAL, limit=1)
        page_two = list_food_picker(
            session, TEST_PRINCIPAL, limit=1, cursor=page_one.next_cursor
        )
        expected_alpha_ids = sorted((first.id, second.id))
        assert [page_one.items[0].id, page_two.items[0].id] == expected_alpha_ids
        assert page_one.next_cursor is not None
        assert page_two.next_cursor is not None

        name_match = list_food_picker(session, TEST_PRINCIPAL, search="AlPhA")
        brand_match = list_food_picker(session, TEST_PRINCIPAL, search="needle")
        assert {item.id for item in name_match.items} == {first.id, second.id}
        assert [item.name for item in brand_match.items] == ["Beta"]
        assert name_match.recent_items == []
        assert brand_match.recent_items == []

        expected_fields = set(FoodPickerItem.model_fields)
        assert set(name_match.items[0].model_dump()) == expected_fields
        assert not expected_fields.intersection(
            {
                "status",
                "food_category_key",
                "nutrition_source",
                "ingredients",
                "group_contributions",
                "analytical_traits",
                "created_at",
                "updated_at",
            }
        )


@pytest.mark.plan014
def test_plan014_picker_cursor_uses_database_normalized_sort_key() -> None:
    with session_fixture() as session:
        first = create_plan014_food(session, "Älpha")
        second = create_plan014_food(session, "Ömega")

        page_one = list_food_picker(session, TEST_PRINCIPAL, limit=1)
        page_two = list_food_picker(
            session, TEST_PRINCIPAL, limit=1, cursor=page_one.next_cursor
        )

        assert page_one.items[0].id == first.id
        assert page_two.items[0].id == second.id


@pytest.mark.plan014
def test_plan014_picker_recents_are_latest_unique_owner_scoped_and_active_only() -> None:
    with session_fixture() as session:
        session.add(Principal(id=OTHER_PRINCIPAL_ID))
        session.commit()
        older = create_plan014_food(session, "Older")
        newest = create_plan014_food(session, "Newest")
        archived = create_plan014_food(session, "Archived recent")
        other_owner = create_plan014_food(session, "Other owner recent")
        base = datetime(2026, 7, 30, tzinfo=timezone.utc)
        create_plan014_entry(session, older, created_at=base)
        create_plan014_entry(session, newest, created_at=base + timedelta(minutes=1))
        create_plan014_entry(session, older, created_at=base + timedelta(minutes=2))
        create_plan014_entry(
            session,
            other_owner,
            principal_id=OTHER_PRINCIPAL_ID,
            created_at=base + timedelta(minutes=4),
        )
        create_plan014_entry(session, archived, created_at=base + timedelta(minutes=3))
        archive_food_response(session, TEST_PRINCIPAL, archived.id)
        create_plan014_entry(session, None, created_at=base + timedelta(minutes=5))

        result = list_food_picker(session, TEST_PRINCIPAL)

        assert [item.id for item in result.recent_items] == [older.id, newest.id]
        assert len(result.items) <= 30
        assert len(result.recent_items) <= 5


def assert_plan014_picker_query_budget(session: Session, history_size: int) -> None:
    food = create_plan014_food(session, f"Picker budget {history_size}")
    base = datetime(2026, 7, 30, tzinfo=timezone.utc)
    session.add_all(
        [
            DiaryEntry(
                principal_id=TEST_PRINCIPAL_ID,
                entry_date=base.date(),
                food_id=food.id,
                quantity=1,
                meal_type="snack",
                nutrition_snapshot={"food_id": str(food.id), "name": food.name},
                created_at=base + timedelta(microseconds=index),
            )
            for index in range(history_size)
        ]
    )
    session.commit()

    with capture_application_selects(session) as empty_search_statements:
        empty = list_food_picker(session, TEST_PRINCIPAL)
    with capture_application_selects(session) as search_statements:
        searched = list_food_picker(session, TEST_PRINCIPAL, search="budget")

    assert len(empty_search_statements) == 2
    assert len(search_statements) == 1
    assert not any("diary_entry" in statement for statement in search_statements)
    assert len(empty.recent_items) <= 5
    assert len(searched.items) <= 30


@pytest.mark.plan014
@pytest.mark.parametrize("history_size", [10, 1000])
def test_plan014_picker_query_budget_is_fixed_on_sqlite(history_size: int) -> None:
    with session_fixture() as session:
        assert_plan014_picker_query_budget(session, history_size)


def test_plan013_batch_responses_preserve_single_item_semantics() -> None:
    with session_fixture() as session:
        foods = create_plan013_representative_foods(session)

        public_foods = list_foods(session, TEST_PRINCIPAL)
        admin_foods = list_foods_page(session, TEST_PRINCIPAL, status=None).items
        expected = [
            to_food_response(session, TEST_PRINCIPAL, food).model_dump(mode="json")
            for food in foods
        ]
        with capture_application_selects(session) as statements:
            responses = to_food_responses(session, TEST_PRINCIPAL, foods)

        assert [food.name for food in public_foods] == ["Alpha Zero", "Beta Multiple"]
        assert [food.name for food in admin_foods] == [
            "Alpha Zero",
            "Beta Multiple",
            "Gamma Archived",
        ]
        assert [response.name for response in responses] == [
            "Alpha Zero",
            "Beta Multiple",
            "Gamma Archived",
        ]
        assert responses[0].sugar_g is None
        assert responses[0].group_data_status == "unknown"
        assert responses[0].group_data_completeness == "unknown"
        assert [item.group_key for item in responses[1].group_contributions] == [
            "fruits",
            "vegetables",
        ]
        assert responses[1].analytical_traits == ["processed", "salted"]
        assert responses[1].group_data_status == "estimated"
        assert responses[1].group_data_completeness == "complete"
        assert responses[2].status == FoodStatus.archived
        assert [response.model_dump(mode="json") for response in responses] == expected
        assert len(child_selects(statements)) == 2


@pytest.mark.parametrize(("size", "expected_child_selects"), [(0, 0), (1, 2), (20, 2), (100, 2)])
def test_plan013_batch_response_child_query_budget(
    size: int, expected_child_selects: int
) -> None:
    with session_fixture() as session:
        foods = [
            create_food(
                session,
                TEST_PRINCIPAL,
                FoodCreate.model_validate(food_payload(name=f"Budget Food {index:03}")),
            )
            for index in range(size)
        ]

        with capture_application_selects(session) as statements:
            responses = to_food_responses(session, TEST_PRINCIPAL, foods)

        assert len(responses) == size
        assert len(child_selects(statements)) == expected_child_selects


def test_plan013_category_metadata_is_distinct_status_scoped_and_empty_safe() -> None:
    with session_fixture() as session:
        empty = list_foods_page(session, TEST_PRINCIPAL)
        assert empty.categories == []
        assert empty.uncategorized_count == 0

        for name in ("Alpha Sweet", "Beta Sweet"):
            create_food(
                session,
                TEST_PRINCIPAL,
                FoodCreate.model_validate(
                    food_payload(name=name, food_category_key="sweets")
                ),
            )
        archived = create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(name="Gamma Archived Category", food_category_key="other")
            ),
        )
        archive_food_response(session, TEST_PRINCIPAL, archived.id)

        with capture_application_selects(session) as statements:
            active = list_foods_page(session, TEST_PRINCIPAL)
        all_statuses = list_foods_page(session, TEST_PRINCIPAL, status=None)

        assert active.categories == ["sweets"]
        assert active.uncategorized_count == 0
        assert all_statuses.categories == ["other", "sweets"]
        assert all_statuses.uncategorized_count == 0
        assert any(
            statement.startswith("select distinct food.food_category_key")
            for statement in statements
        )


def assert_plan013_list_route_query_budgets(session: Session, size: int) -> None:
    for index in range(size):
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(name=f"Route Budget {index:03}")),
        )

    routes = {
        "legacy": ("/foods", 1 if size == 0 else 3),
        "public_page": (
            "/foods?page=1&page_size=100",
            3 if size == 0 else 5,
        ),
        "admin_page": (
            "/admin/foods?page=1&page_size=100",
            3 if size == 0 else 5,
        ),
    }
    with client_for_session(session) as client:
        for route_name, (path, expected_total_selects) in routes.items():
            with capture_application_selects(session) as statements:
                response = client.get(path, headers=auth_headers())

            assert response.status_code == 200, route_name
            body = response.json()
            items = body if route_name == "legacy" else body["items"]
            assert len(items) == size, route_name
            assert len(child_selects(statements)) == (0 if size == 0 else 2)
            assert len(statements) == expected_total_selects, route_name


@pytest.mark.parametrize("size", [0, 1, 20, 100])
def test_plan013_list_route_total_and_child_query_budgets(size: int) -> None:
    with session_fixture() as session:
        assert_plan013_list_route_query_budgets(session, size)


@pytest.fixture
def isolated_postgresql_session():
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL query budgets.")
    if make_url(url).get_backend_name() != "postgresql":
        pytest.fail("PostgreSQL query budgets require a PostgreSQL TEST_DATABASE_URL.")

    schema_name = f"isolated_foods_{uuid4().hex}"
    admin_engine = create_engine(url, isolation_level="AUTOCOMMIT")
    test_engine = None
    schema_created = False
    try:
        with admin_engine.connect() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
            schema_created = True
        test_engine = create_engine(
            url,
            connect_args={"options": f"-csearch_path={schema_name}"},
        )
        SQLModel.metadata.create_all(test_engine)
        with Session(test_engine) as session:
            session.add(Principal(id=TEST_PRINCIPAL_ID))
            session.commit()
            yield session
    finally:
        if test_engine is not None:
            test_engine.dispose()
        if schema_created:
            with admin_engine.connect() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def plan013_postgresql_session(isolated_postgresql_session: Session):
    yield isolated_postgresql_session


@pytest.fixture
def plan014_postgresql_session(isolated_postgresql_session: Session):
    yield isolated_postgresql_session


@pytest.mark.parametrize("size", [0, 1, 20, 100])
def test_plan013_postgresql_list_route_total_and_child_query_budgets(
    plan013_postgresql_session: Session, size: int
) -> None:
    assert_plan013_list_route_query_budgets(plan013_postgresql_session, size)


@pytest.mark.plan014
@pytest.mark.parametrize("history_size", [10, 1000])
def test_plan014_postgresql_picker_query_budget(
    plan014_postgresql_session: Session, history_size: int
) -> None:
    assert_plan014_picker_query_budget(plan014_postgresql_session, history_size)


@pytest.mark.plan014
def test_plan014_postgresql_recent_window_has_deterministic_tie_order(
    plan014_postgresql_session: Session,
) -> None:
    first = create_plan014_food(plan014_postgresql_session, "Postgres tie first")
    second = create_plan014_food(plan014_postgresql_session, "Postgres tie second")
    created_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
    first_entry = create_plan014_entry(
        plan014_postgresql_session, first, created_at=created_at
    )
    second_entry = create_plan014_entry(
        plan014_postgresql_session, second, created_at=created_at
    )

    result = list_food_picker(plan014_postgresql_session, TEST_PRINCIPAL)

    expected = [
        food_id
        for _, food_id in sorted(
            ((first_entry.id, first.id), (second_entry.id, second.id)), reverse=True
        )
    ]
    assert [item.id for item in result.recent_items] == expected


def test_plan013_detail_endpoint_keeps_single_item_response_path() -> None:
    with session_fixture() as session:
        food = create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(
                    name="Detail Regression",
                    group_contributions=[
                        {
                            "group_key": "fruits",
                            "amount_per_100_basis": 100,
                            "data_status": "known",
                        }
                    ],
                    analytical_traits=["sweetened"],
                )
            ),
        )

        with client_for_session(session) as client:
            with capture_application_selects(session) as statements:
                response = client.get(f"/foods/{food.id}", headers=auth_headers())

        assert response.status_code == 200
        assert response.json()["group_contributions"][0]["group_key"] == "fruits"
        assert response.json()["analytical_traits"] == ["sweetened"]
        assert len(child_selects(statements)) == 2
        assert len(statements) == 3


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
        json=food_json(name="Legacy Food", food_category_key="other"),
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
    assert body["categories"] == ["other"]
    assert body["items"][0]["name"] == "Legacy Food"


def test_food_page_combines_search_and_category_filters() -> None:
    with session_fixture() as session:
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(
                    name="Arabic Oats",
                    food_category_key="grains_starches",
                    grain_starch_type="oats",
                    grain_type="whole",
                )
            ),
        )
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(name="Other Oats", food_category_key="sweets")
            ),
        )
        create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(name="Plain Oats", food_category_key="other")
            ),
        )

        grains = list_foods_page(
            session, TEST_PRINCIPAL, search="oats", category="grains_starches"
        )
        assert [food.name for food in grains.items] == ["Arabic Oats"]
        assert grains.total == 1
        assert grains.categories == ["grains_starches", "other", "sweets"]
        assert grains.uncategorized_count == 0


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


@pytest.mark.parametrize("missing_field", ("food_category_key", "food_kind", "nutrition_source"))
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
        food_category_key="mixed_dish",
        food_kind="composite",
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


def test_group_status_and_completeness_are_derived_and_not_client_authoritative(
    api_client: TestClient,
) -> None:
    rejected = api_client.post(
        "/foods",
        json=food_json(name="Client status", group_data_status="known"),
        headers=auth_headers(),
    )
    assert rejected.status_code == 422

    created = api_client.post(
        "/foods",
        json=food_json(
            name="Derived status",
            group_contributions=[
                {
                    "group_key": "fruits",
                    "amount_per_100_basis": 60,
                    "data_status": "estimated",
                }
            ],
        ),
        headers=auth_headers(),
    )
    assert created.status_code == 201
    assert created.json()["group_data_status"] == "estimated"
    assert created.json()["group_data_completeness"] == "partial"


@pytest.mark.parametrize(
    ("category", "details"),
    [
        ("baked_goods", {"baked_good_type": "arabic_bread", "grain_type": "whole"}),
        ("grains_starches", {"grain_starch_type": "rice", "grain_type": "refined"}),
    ],
)
def test_food_taxonomy_v2_requires_structured_category_details(
    api_client: TestClient, category: str, details: dict
) -> None:
    missing = api_client.post(
        "/foods",
        json=food_json(name=f"Missing {category}", food_category_key=category),
        headers=auth_headers(),
    )
    assert missing.status_code == 422

    valid = api_client.post(
        "/foods",
        json=food_json(name=f"Valid {category}", food_category_key=category, **details),
        headers=auth_headers(),
    )
    assert valid.status_code == 201, valid.text
    for key, value in details.items():
        assert valid.json()[key] == value

    unrelated = api_client.post(
        "/foods",
        json=food_json(name=f"Unrelated {category}", food_category_key="fruits", **details),
        headers=auth_headers(),
    )
    assert unrelated.status_code == 422


def test_legacy_category_is_not_part_of_v2_food_contract(api_client: TestClient) -> None:
    payload = food_json(name="Legacy category rejected")
    payload["category"] = "Legacy"
    response = api_client.post("/foods", json=payload, headers=auth_headers())
    assert response.status_code == 422


def test_plan009_numeric_registry_matches_schema_and_database_models() -> None:
    def direct_float_fields(model) -> set[str]:
        return {
            name
            for name, field in model.model_fields.items()
            if field.annotation is float or float in get_args(field.annotation)
        }

    food_numeric_columns = {
        column.name
        for column in Food.__table__.columns
        if isinstance(column.type, Numeric)
    }
    group_numeric_columns = {
        column.name
        for column in FoodGroupContribution.__table__.columns
        if isinstance(column.type, Numeric)
    }

    assert set(FOOD_NUMERIC_COLUMNS) == food_numeric_columns
    assert set(FOOD_GROUP_NUMERIC_COLUMNS) == group_numeric_columns
    assert set(FOOD_GROUP_NUMERIC_FIELDS) == group_numeric_columns
    assert set(FOOD_GROUP_NUMERIC_FIELDS) == direct_float_fields(
        FoodGroupContributionInput
    )
    assert set(FOOD_NUMERIC_FIELDS) == direct_float_fields(FoodCreate)
    assert set(FOOD_NUMERIC_FIELDS) == direct_float_fields(FoodUpdate)
    assert set(FOOD_NUMERIC_FIELDS) | set(
        FOOD_RESPONSE_DERIVED_NUMERIC_FIELDS
    ) == direct_float_fields(FoodResponse)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("field", FOOD_NUMERIC_FIELDS)
def test_plan009_create_rejects_every_non_finite_food_number(
    api_client: TestClient, field: str, constant: str
) -> None:
    payload = food_json(name=f"Non finite create {field} {constant}")
    payload[field] = 1
    raw = json.dumps(payload, separators=(",", ":")).replace(
        f'"{field}":1', f'"{field}":{constant}', 1
    )

    response = api_client.post(
        "/foods",
        content=raw,
        headers={**auth_headers(), "Content-Type": "application/json"},
    )

    errors = error_by_field(response)
    assert errors[field]["field"] == field
    assert errors[field]["code"] == "invalid_number"
    assert api_client.get("/foods", headers=auth_headers()).json() == []


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("field", FOOD_NUMERIC_FIELDS)
def test_plan009_partial_update_rejects_non_finite_without_mutation(
    api_client: TestClient, field: str, constant: str
) -> None:
    created = api_client.post(
        "/foods",
        json=food_json(name=f"Non finite update {field} {constant}"),
        headers=auth_headers(),
    )
    assert created.status_code == 201
    food_id = created.json()["id"]
    before = created.json()[field]

    response = api_client.put(
        f"/foods/{food_id}",
        content=f'{{"{field}":{constant}}}',
        headers={**auth_headers(), "Content-Type": "application/json"},
    )

    errors = error_by_field(response)
    assert errors[field]["field"] == field
    assert errors[field]["code"] == "invalid_number"
    stored = api_client.get(f"/foods/{food_id}", headers=auth_headers())
    assert stored.status_code == 200
    assert stored.json()[field] == before


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_plan009_nested_group_amount_rejects_non_finite(
    api_client: TestClient, constant: str
) -> None:
    payload = food_json(
        name=f"Non finite group {constant}",
        group_contributions=[
            {
                "group_key": "fruits",
                "amount_per_100_basis": 1,
                "data_status": "known",
            }
        ],
    )
    raw = json.dumps(payload, separators=(",", ":")).replace(
        '"amount_per_100_basis":1',
        f'"amount_per_100_basis":{constant}',
        1,
    )

    response = api_client.post(
        "/foods",
        content=raw,
        headers={**auth_headers(), "Content-Type": "application/json"},
    )

    errors = error_by_field(response)
    assert errors["amount_per_100_basis"]["field"] == "amount_per_100_basis"


def test_plan009_zero_null_and_inclusive_bounds_remain_valid(api_client: TestClient) -> None:
    created = api_client.post(
        "/foods",
        json=food_json(
            name="Finite boundaries",
            unit_amount=2000,
            calories=3000,
            protein_g=300,
            carb_g=500,
            fat_g=300,
            fiber_g=0,
            sugar_g=None,
            sodium_mg=50000,
            group_contributions=[
                {
                    "group_key": "fruits",
                    "amount_per_100_basis": 100,
                    "data_status": "known",
                }
            ],
        ),
        headers=auth_headers(),
    )

    assert created.status_code == 201, created.text
    assert created.json()["fiber_g"] == 0
    assert created.json()["sugar_g"] is None
    assert created.json()["group_contributions"][0]["amount_per_100_basis"] == 100


@pytest.mark.parametrize(
    ("field", "minimum", "maximum"),
    [
        ("unit_amount", 0.01, 2000),
        ("calories", 0, 3000),
        ("protein_g", 0, 300),
        ("carb_g", 0, 500),
        ("fat_g", 0, 300),
        *[(field, 0, maximum) for field, maximum in OPTIONAL_NUTRIENT_MAX.items()],
    ],
)
def test_plan009_numeric_boundaries_are_enforced(
    field: str, minimum: float, maximum: float
) -> None:
    dependencies = {
        "carb_g": 500,
        "fat_g": 300,
        "fiber_g": None,
        "sugar_g": 100,
        "saturated_fat_g": None,
    }
    FoodCreate.model_validate(food_payload(**(dependencies | {field: minimum})))
    FoodCreate.model_validate(food_payload(**(dependencies | {field: maximum})))

    invalid_minimum = 0 if field == "unit_amount" else -0.01
    with pytest.raises(ValidationError):
        FoodCreate.model_validate(food_payload(**(dependencies | {field: invalid_minimum})))
    with pytest.raises(ValidationError):
        FoodCreate.model_validate(food_payload(**(dependencies | {field: maximum + 0.01})))


def test_plan009_create_response_failure_rolls_back_parent_and_children(monkeypatch) -> None:
    with session_fixture() as session:
        def fail_response(*_args, **_kwargs):
            raise RuntimeError("injected response validation failure")

        monkeypatch.setattr("app.services.food.to_food_response", fail_response)
        payload = FoodCreate.model_validate(
            food_payload(
                name="Rollback create",
                group_contributions=[
                    {
                        "group_key": "fruits",
                        "amount_per_100_basis": 100,
                        "data_status": "known",
                    }
                ],
            )
        )

        with pytest.raises(RuntimeError, match="injected response validation failure"):
            create_food_response(session, TEST_PRINCIPAL, payload)

        assert session.exec(select(Food).where(Food.name == "Rollback create")).first() is None
        assert session.exec(select(FoodGroupContribution)).all() == []


def test_plan009_update_response_failure_rolls_back_parent_and_children(monkeypatch) -> None:
    with session_fixture() as session:
        food = create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(
                food_payload(
                    name="Rollback update original",
                    group_contributions=[
                        {
                            "group_key": "fruits",
                            "amount_per_100_basis": 100,
                            "data_status": "known",
                        }
                    ],
                )
            ),
        )

        def fail_response(*_args, **_kwargs):
            raise RuntimeError("injected response validation failure")

        monkeypatch.setattr("app.services.food.to_food_response", fail_response)
        update = FoodUpdate.model_validate(
            {
                "name": "Rollback update changed",
                "group_contributions": [
                    {
                        "group_key": "vegetables",
                        "amount_per_100_basis": 100,
                        "data_status": "known",
                    }
                ],
            }
        )

        with pytest.raises(RuntimeError, match="injected response validation failure"):
            update_food_response(session, TEST_PRINCIPAL, food.id, update)

        session.expire_all()
        stored = session.get(Food, food.id)
        contributions = session.exec(
            select(FoodGroupContribution).where(FoodGroupContribution.food_id == food.id)
        ).all()
        assert stored is not None
        assert stored.name == "Rollback update original"
        assert [item.group_key for item in contributions] == ["fruits"]


@pytest.mark.parametrize("constant", [float("nan"), float("inf"), float("-inf")])
def test_plan009_legacy_non_finite_food_response_fails_closed(constant: float) -> None:
    with session_fixture() as session:
        food = create_food(
            session,
            TEST_PRINCIPAL,
            FoodCreate.model_validate(food_payload(name="Legacy invalid response")),
        )
        food.calories = constant

        with session.no_autoflush:
            with pytest.raises(HTTPException) as invalid:
                to_food_response(session, TEST_PRINCIPAL, food)

        assert invalid.value.status_code == 409
        assert invalid.value.detail["code"] == "INVALID_FOOD_DATA"
        assert "nan" not in str(invalid.value.detail).lower()
        assert "inf" not in str(invalid.value.detail).lower()
