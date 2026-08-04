from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import Event
from time import monotonic
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.models import (
    DefaultUnitType,
    Food,
    FoodTaxonomyV2MigrationAudit,
    NutritionBasis,
    Principal,
    UnitBasis,
)
from app.ops.reclassify_food_taxonomy import (
    REVIEW_REASON,
    apply_reviewed_mapping,
    parse_reviewed_mappings,
    publish_review_export,
    proposed_mappings,
)


PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000022")


def _food(food_id: UUID, name: str, *, review_required: bool = True) -> Food:
    return Food(
        id=food_id,
        principal_id=PRINCIPAL_ID,
        name=name,
        normalized_name=name.lower(),
        food_category_key="grains_starches",
        grain_type="whole",
        grain_starch_type="other",
        taxonomy_review_required=review_required,
        nutrition_basis=NutritionBasis.per_100g,
        default_unit_type=DefaultUnitType.g,
        unit_amount=100,
        unit_basis=UnitBasis.g,
        calories=100,
        protein_g=1,
        carb_g=20,
        fat_g=1,
    )


def _review_item(
    food_id: UUID,
    name: str,
    *,
    resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(food_id),
        "name": name,
        "food_category_key": "grains_starches",
        "grain_type": "whole",
        "baked_good_type": None,
        "grain_starch_type": "other",
        "taxonomy_review_required": True,
        "legacy_category": "legacy",
        "legacy_primary_category_key": "whole_grains",
        "resolution": resolution
        or {
            "food_category_key": "fruits",
            "grain_type": None,
            "baked_good_type": None,
            "grain_starch_type": None,
        },
        "reason": REVIEW_REASON,
    }


@pytest.fixture
def sqlite_engine() -> Engine:
    database_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(database_engine)
    with Session(database_engine) as session:
        session.add(Principal(id=PRINCIPAL_ID))
        session.commit()
    yield database_engine
    database_engine.dispose()


def _insert_review_food(database_engine: Engine, food_id: UUID, name: str) -> None:
    with Session(database_engine) as session:
        session.add(_food(food_id, name))
        session.add(
            FoodTaxonomyV2MigrationAudit(
                food_id=food_id,
                legacy_category="legacy",
                legacy_primary_category_key="whole_grains",
            )
        )
        session.commit()


def _food_state(database_engine: Engine, food_ids: list[UUID]) -> list[tuple[Any, ...]]:
    with Session(database_engine) as session:
        return list(
            session.execute(
                select(
                    Food.id,
                    Food.food_category_key,
                    Food.grain_type,
                    Food.baked_good_type,
                    Food.grain_starch_type,
                    Food.taxonomy_review_required,
                )
                .where(Food.id.in_(food_ids))
                .order_by(Food.id)
            ).all()
        )


def _full_food_state(database_engine: Engine, food_ids: list[UUID]) -> list[dict[str, Any]]:
    with Session(database_engine) as session:
        return [
            dict(row)
            for row in session.execute(
                select(*Food.__table__.c).where(Food.id.in_(food_ids)).order_by(Food.id)
            ).mappings()
        ]


def _assert_resolution_only_change(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    expected: dict[str, Any],
) -> None:
    allowed = {
        "food_category_key",
        "grain_type",
        "baked_good_type",
        "grain_starch_type",
        "taxonomy_review_required",
    }
    assert [row["id"] for row in after] == [row["id"] for row in before]
    for before_row, after_row in zip(before, after, strict=True):
        changed = {
            key for key in before_row if before_row[key] != after_row[key]
        }
        assert changed <= allowed
        assert {key: after_row[key] for key in allowed} == expected


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda item: item.pop("resolution"), "missing=['resolution']"),
        (lambda item: item.update(resolution=None), "Explicit resolution object required"),
        (lambda item: item.update(resolution="fruits"), "Explicit resolution object required"),
        (lambda item: item.update(resolution=[]), "Explicit resolution object required"),
        (
            lambda item: item["resolution"].pop("grain_type"),
            "missing=['grain_type']",
        ),
        (
            lambda item: item["resolution"].update(comment="approved"),
            "unknown=['comment']",
        ),
        (lambda item: item.update(comment="approved"), "unknown=['comment']"),
    ],
)
def test_plan022_closed_resolution_schema_rejects_invalid_rows_before_sql(
    sqlite_engine: Engine, mutation, message: str
) -> None:
    item = _review_item(uuid4(), "Schema food")
    mutation(item)
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement)

    event.listen(sqlite_engine, "before_cursor_execute", capture)
    try:
        with (
            Session(sqlite_engine) as session,
            pytest.raises(RuntimeError, match=re.escape(message)),
        ):
            apply_reviewed_mapping(session, [item])
    finally:
        event.remove(sqlite_engine, "before_cursor_execute", capture)

    assert statements == []


def test_plan022_parser_rejects_non_list_duplicate_and_malformed_food_ids(
    sqlite_engine: Engine,
) -> None:
    with pytest.raises(RuntimeError, match="root must be a list"):
        parse_reviewed_mappings({})

    empty_batch_message = "must contain at least one explicit resolution"
    with pytest.raises(RuntimeError, match=empty_batch_message):
        parse_reviewed_mappings([])

    food_id = uuid4()
    _insert_review_food(sqlite_engine, food_id, "Empty batch guard")
    before = _full_food_state(sqlite_engine, [food_id])
    statements: list[str] = []
    commit_count = 0

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement)

    def count_commit(_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1

    event.listen(sqlite_engine, "before_cursor_execute", capture)
    try:
        with Session(sqlite_engine) as session:
            event.listen(session, "after_commit", count_commit)
            with pytest.raises(RuntimeError, match=empty_batch_message):
                apply_reviewed_mapping(session, [])
            assert session.is_active
            assert not session.in_transaction()
    finally:
        event.remove(sqlite_engine, "before_cursor_execute", capture)

    assert statements == []
    assert commit_count == 0
    assert _full_food_state(sqlite_engine, [food_id]) == before

    malformed = _review_item(uuid4(), "Malformed")
    malformed["id"] = "not-a-uuid"
    with pytest.raises(RuntimeError, match="Invalid Food UUID"):
        parse_reviewed_mappings([malformed])
    duplicate = _review_item(uuid4(), "Duplicate")
    with pytest.raises(RuntimeError, match="Duplicate Food UUID"):
        parse_reviewed_mappings([duplicate, deepcopy(duplicate)])


@pytest.mark.parametrize(
    ("resolution", "message"),
    [
        (
            {
                "food_category_key": "not_registered",
                "grain_type": None,
                "baked_good_type": None,
                "grain_starch_type": None,
            },
            "Invalid food_category_key",
        ),
        (
            {
                "food_category_key": "grains_starches",
                "grain_type": "invented",
                "baked_good_type": None,
                "grain_starch_type": "rice",
            },
            "Invalid grain_type",
        ),
        (
            {
                "food_category_key": "fruits",
                "grain_type": "whole",
                "baked_good_type": None,
                "grain_starch_type": None,
            },
            "Incompatible taxonomy resolution",
        ),
    ],
)
def test_plan022_invalid_vocabulary_or_combination_executes_zero_sql(
    sqlite_engine: Engine, resolution: dict[str, Any], message: str
) -> None:
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement)

    event.listen(sqlite_engine, "before_cursor_execute", capture)
    try:
        with Session(sqlite_engine) as session, pytest.raises(RuntimeError, match=message):
            apply_reviewed_mapping(
                session, [_review_item(uuid4(), "Invalid vocabulary", resolution=resolution)]
            )
    finally:
        event.remove(sqlite_engine, "before_cursor_execute", capture)

    assert statements == []


def test_plan022_valid_multi_row_batch_locks_sorted_and_commits_once(
    sqlite_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    low = UUID("00000000-0000-0000-0000-000000000221")
    high = UUID("00000000-0000-0000-0000-000000000229")
    _insert_review_food(sqlite_engine, low, "Low")
    _insert_review_food(sqlite_engine, high, "High")
    statements: list[tuple[str, Any]] = []
    original_commit = Session.commit
    commit_count = 0

    def count_commit(self: Session) -> None:
        nonlocal commit_count
        commit_count += 1
        original_commit(self)

    def capture(_conn, _cursor, statement, parameters, _context, _executemany) -> None:
        statements.append((statement, parameters))

    event.listen(sqlite_engine, "before_cursor_execute", capture)
    monkeypatch.setattr(Session, "commit", count_commit)
    try:
        with Session(sqlite_engine) as session:
            result = apply_reviewed_mapping(
                session, [_review_item(high, "High"), _review_item(low, "Low")]
            )
    finally:
        event.remove(sqlite_engine, "before_cursor_execute", capture)

    assert result == {"applied_count": 2, "food_ids": [str(low), str(high)]}
    assert commit_count == 1
    assert _food_state(sqlite_engine, [low, high]) == [
        (low, "fruits", None, None, None, False),
        (high, "fruits", None, None, None, False),
    ]
    lock_parameters = next(
        parameters for statement, parameters in statements if "ORDER BY food.id" in statement
    )
    assert tuple(lock_parameters) == (low.hex, high.hex)
    assert sum(statement.lstrip().upper().startswith("UPDATE") for statement, _ in statements) == 2


@pytest.mark.parametrize("stale_kind", ["changed", "already_reviewed", "missing", "missing_audit"])
def test_plan022_stale_or_missing_context_aborts_before_updates(
    sqlite_engine: Engine, stale_kind: str
) -> None:
    food_id = uuid4()
    if stale_kind != "missing":
        _insert_review_food(sqlite_engine, food_id, "Current name")
    item = _review_item(food_id, "Current name")
    if stale_kind == "changed":
        item["grain_type"] = "refined"
    elif stale_kind == "already_reviewed":
        with Session(sqlite_engine) as session:
            food = session.get(Food, food_id)
            assert food is not None
            food.taxonomy_review_required = False
            session.add(food)
            session.commit()
    elif stale_kind == "missing_audit":
        with Session(sqlite_engine) as session:
            audit = session.get(FoodTaxonomyV2MigrationAudit, food_id)
            assert audit is not None
            session.delete(audit)
            session.commit()
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        statements.append(statement)

    event.listen(sqlite_engine, "before_cursor_execute", capture)
    try:
        with (
            Session(sqlite_engine) as session,
            pytest.raises(
                RuntimeError,
                match=(
                    "Stale taxonomy review context|Missing taxonomy review Foods|"
                    "Missing taxonomy review audit"
                ),
            ),
        ):
            apply_reviewed_mapping(session, [item])
    finally:
        event.remove(sqlite_engine, "before_cursor_execute", capture)

    assert not any(statement.lstrip().upper().startswith("UPDATE") for statement in statements)


def test_plan022_final_row_failure_rolls_back_every_earlier_update(
    sqlite_engine: Engine,
) -> None:
    first = UUID("00000000-0000-0000-0000-000000000231")
    final = UUID("00000000-0000-0000-0000-000000000239")
    _insert_review_food(sqlite_engine, first, "First")
    _insert_review_food(sqlite_engine, final, "Final")
    before = _full_food_state(sqlite_engine, [first, final])
    update_count = 0

    def fail_final_update(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        nonlocal update_count
        if statement.lstrip().upper().startswith("UPDATE"):
            update_count += 1
            if update_count == 2:
                raise RuntimeError("synthetic final-row failure")

    event.listen(sqlite_engine, "before_cursor_execute", fail_final_update)
    try:
        with (
            Session(sqlite_engine) as session,
            pytest.raises(RuntimeError, match="synthetic final-row failure"),
        ):
            apply_reviewed_mapping(
                session, [_review_item(first, "First"), _review_item(final, "Final")]
            )
    finally:
        event.remove(sqlite_engine, "before_cursor_execute", fail_final_update)

    assert update_count == 2
    assert _full_food_state(sqlite_engine, [first, final]) == before


def test_plan022_output_is_read_only_and_parser_accepts_documented_shape(
    sqlite_engine: Engine,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    food_id = uuid4()
    _insert_review_food(sqlite_engine, food_id, "Output food")
    before = _full_food_state(sqlite_engine, [food_id])
    writes: list[str] = []
    commit_count = 0

    def capture(_conn, _cursor, statement, _parameters, _context, _executemany) -> None:
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    def count_commit(_session: Session) -> None:
        nonlocal commit_count
        commit_count += 1

    event.listen(sqlite_engine, "before_cursor_execute", capture)
    try:
        with Session(sqlite_engine) as session:
            event.listen(session, "after_commit", count_commit)
            output = proposed_mappings(session)
    finally:
        event.remove(sqlite_engine, "before_cursor_execute", capture)

    assert writes == []
    assert commit_count == 0
    assert _full_food_state(sqlite_engine, [food_id]) == before
    assert output[0]["resolution"] is None
    destination = tmp_path / "review.json"
    publish_review_export(destination, output)
    serialized = destination.read_bytes()
    assert serialized.endswith(b"\n")
    assert json.loads(serialized.decode("utf-8")) == output
    assert list(tmp_path.iterdir()) == [destination]

    sentinel = tmp_path / "sentinel.json"
    sentinel_bytes = b"sentinel-export-must-remain-unchanged\n"
    sentinel.write_bytes(sentinel_bytes)
    with pytest.raises(RuntimeError, match="export already exists"):
        publish_review_export(sentinel, output)
    assert sentinel.read_bytes() == sentinel_bytes
    assert not list(tmp_path.glob(".*.tmp"))

    directory_target = tmp_path / "existing-directory"
    directory_target.mkdir()
    with pytest.raises(RuntimeError, match="export already exists"):
        publish_review_export(directory_target, output)
    assert directory_target.is_dir()
    assert not list(tmp_path.glob(".*.tmp"))

    missing_parent = tmp_path / "missing-parent" / "review.json"
    with pytest.raises(FileNotFoundError):
        publish_review_export(missing_parent, output)
    assert not missing_parent.parent.exists()

    interrupted = tmp_path / "interrupted.json"

    def fail_atomic_publish(_source: Path, _destination: Path) -> None:
        raise OSError("synthetic atomic publication failure")

    monkeypatch.setattr(os, "link", fail_atomic_publish)
    with pytest.raises(OSError, match="synthetic atomic publication failure"):
        publish_review_export(interrupted, output)
    assert not interrupted.exists()
    assert not list(tmp_path.glob(".*.tmp"))
    assert _full_food_state(sqlite_engine, [food_id]) == before
    assert capsys.readouterr().out == ""

    reviewed = deepcopy(output[0])
    reviewed["resolution"] = {
        "food_category_key": "fruits",
        "grain_type": None,
        "baked_good_type": None,
        "grain_starch_type": None,
    }
    assert parse_reviewed_mappings([reviewed])[0].food_id == food_id
    with pytest.raises(RuntimeError, match="Explicit resolution object required"):
        parse_reviewed_mappings(output)


def test_plan022_documented_example_matches_parser_and_unresolved_variant_fails() -> None:
    document = (
        Path(__file__).parents[2] / "docs/product/v2/06_DATA_MIGRATION_AND_CUTOVER.md"
    ).read_text(encoding="utf-8")
    example = json.loads(document.split("```json", 1)[1].split("```", 1)[0])

    assert len(parse_reviewed_mappings(example)) == 1
    example[0]["resolution"] = None
    with pytest.raises(RuntimeError, match="Explicit resolution object required"):
        parse_reviewed_mappings(example)


def _postgres_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL Plan 022 cases.")
    parsed = make_url(url)
    database = parsed.database or ""
    if parsed.host not in {"localhost", "127.0.0.1", "::1"} or not database.startswith(
        "mynutri_test_"
    ):
        pytest.fail("Plan 022 refuses a non-loopback or non-disposable PostgreSQL database.")
    return url


def _run_alembic(url: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def plan022_postgres() -> tuple[Engine, list[UUID]]:
    url = _postgres_url()
    database_engine = create_engine(url)
    with database_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    _run_alembic(url)
    ids = [
        UUID("00000000-0000-0000-0000-000000000241"),
        UUID("00000000-0000-0000-0000-000000000249"),
    ]
    with Session(database_engine) as session:
        try:
            session.add(Principal(id=PRINCIPAL_ID))
            session.flush()
            foods = [
                _food(food_id, name)
                for food_id, name in zip(
                    ids,
                    ("Postgres first", "Postgres final"),
                    strict=True,
                )
            ]
            session.add_all(foods)
            session.flush()
            session.add_all(
                [
                    FoodTaxonomyV2MigrationAudit(
                        food_id=food.id,
                        legacy_category="legacy",
                        legacy_primary_category_key="whole_grains",
                    )
                    for food in foods
                ]
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

    with Session(database_engine) as verification:
        assert verification.execute(
            select(Principal.id).where(Principal.id == PRINCIPAL_ID)
        ).scalars().all() == [PRINCIPAL_ID]
        assert verification.execute(
            select(
                Food.id,
                Food.created_by_principal_id,
                Food.food_category_key,
                Food.grain_type,
                Food.baked_good_type,
                Food.grain_starch_type,
                Food.taxonomy_review_required,
            )
            .where(Food.id.in_(ids))
            .order_by(Food.id)
        ).all() == [
            (
                food_id,
                PRINCIPAL_ID,
                "grains_starches",
                "whole",
                None,
                "other",
                True,
            )
            for food_id in ids
        ]
        assert verification.execute(
            select(FoodTaxonomyV2MigrationAudit.food_id)
            .where(FoodTaxonomyV2MigrationAudit.food_id.in_(ids))
            .order_by(FoodTaxonomyV2MigrationAudit.food_id)
        ).scalars().all() == ids
    yield database_engine, ids
    database_engine.dispose()


def _set_application_name(session: Session, name: str) -> None:
    session.execute(text("SET LOCAL lock_timeout = '10s'"))
    session.execute(text("SELECT set_config('application_name', :name, true)"), {"name": name})


def _wait_for_lock(database_engine: Engine, name: str) -> None:
    deadline = monotonic() + 10
    while monotonic() < deadline:
        with database_engine.connect() as connection:
            waiting = connection.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE application_name=:name AND wait_event_type='Lock'"
                ),
                {"name": name},
            ).scalar_one()
        if waiting:
            return
    pytest.fail(f"{name} never entered the deterministic PostgreSQL lock wait")


def test_plan022_postgresql_overlapping_reversed_batches_lock_deterministically(
    plan022_postgres: tuple[Engine, list[UUID]],
) -> None:
    database_engine, food_ids = plan022_postgres
    canonical_order = sorted(food_ids)
    before = _full_food_state(database_engine, canonical_order)
    batch_a_locked = Event()
    input_orders = {
        "batch-a": list(canonical_order),
        "batch-b": list(reversed(canonical_order)),
    }
    locked_orders: dict[str, list[UUID]] = {}
    phases: dict[str, str] = {}
    outcomes: dict[str, str] = {}
    transactions = {
        "batch-a": {"commit": 0, "rollback": 0},
        "batch-b": {"commit": 0, "rollback": 0},
    }
    batch_b_resolution = {
        "food_category_key": "grains_starches",
        "grain_type": "refined",
        "baked_good_type": None,
        "grain_starch_type": "rice",
    }

    def run_batch(name: str) -> None:
        with Session(database_engine) as session:
            _set_application_name(session, f"plan022-{name}")

            def observe_lock(execute_state):
                if getattr(execute_state.statement, "_for_update_arg", None) is None:
                    return execute_state.invoke_statement()
                result = execute_state.invoke_statement()
                frozen = result.freeze()
                locked_orders[name] = [row["id"] for row in frozen().mappings().all()]
                phases[name] = "rows-locked"
                if name == "batch-a":
                    batch_a_locked.set()
                    _wait_for_lock(database_engine, "plan022-batch-b")
                return frozen()

            event.listen(session, "do_orm_execute", observe_lock, retval=True)
            event.listen(
                session,
                "after_commit",
                lambda _session: transactions[name].__setitem__(
                    "commit", transactions[name]["commit"] + 1
                ),
            )
            event.listen(
                session,
                "after_rollback",
                lambda _session: transactions[name].__setitem__(
                    "rollback", transactions[name]["rollback"] + 1
                ),
            )
            if name == "batch-b":
                assert batch_a_locked.wait(timeout=10)
            phases[name] = "applying"
            resolution = None if name == "batch-a" else batch_b_resolution
            mappings = [
                _review_item(
                    food_id,
                    "Postgres first" if food_id == food_ids[0] else "Postgres final",
                    resolution=resolution,
                )
                for food_id in input_orders[name]
            ]
            try:
                apply_reviewed_mapping(session, mappings)
                outcomes[name] = "success"
            except RuntimeError as exc:
                assert "Stale taxonomy review context" in str(exc)
                outcomes[name] = "stale"
            phases[name] = "finished"

    with ThreadPoolExecutor(max_workers=2) as executor:
        batch_a = executor.submit(run_batch, "batch-a")
        batch_b = executor.submit(run_batch, "batch-b")
        batch_a.result(timeout=20)
        batch_b.result(timeout=20)

    assert input_orders["batch-a"] != input_orders["batch-b"]
    assert locked_orders == {
        "batch-a": canonical_order,
        "batch-b": canonical_order,
    }
    assert phases == {"batch-a": "finished", "batch-b": "finished"}
    assert outcomes == {"batch-a": "success", "batch-b": "stale"}
    assert transactions == {
        "batch-a": {"commit": 1, "rollback": 0},
        "batch-b": {"commit": 0, "rollback": 1},
    }
    after = _full_food_state(database_engine, canonical_order)
    _assert_resolution_only_change(
        before,
        after,
        {
            "food_category_key": "fruits",
            "grain_type": None,
            "baked_good_type": None,
            "grain_starch_type": None,
            "taxonomy_review_required": False,
        },
    )


def test_plan022_postgresql_failure_rolls_back_then_retry_commits_once(
    plan022_postgres: tuple[Engine, list[UUID]], monkeypatch: pytest.MonkeyPatch
) -> None:
    database_engine, food_ids = plan022_postgres
    before = _full_food_state(database_engine, food_ids)
    original_execute = Session.execute
    update_count = 0
    transaction_events = {"commit": 0, "rollback": 0}

    def count_commit(_session: Session) -> None:
        transaction_events["commit"] += 1

    def count_rollback(_session: Session) -> None:
        transaction_events["rollback"] += 1

    def fail_final(self, statement, *args, **kwargs):
        nonlocal update_count
        if getattr(statement, "is_update", False):
            update_count += 1
            if update_count == 2:
                raise RuntimeError("synthetic PostgreSQL final-row failure")
        return original_execute(self, statement, *args, **kwargs)

    reviewed = [
        _review_item(food_ids[1], "Postgres final"),
        _review_item(food_ids[0], "Postgres first"),
    ]
    with monkeypatch.context() as failure:
        failure.setattr(Session, "execute", fail_final)
        with Session(database_engine) as session:
            event.listen(session, "after_commit", count_commit)
            event.listen(session, "after_rollback", count_rollback)
            with pytest.raises(RuntimeError, match="synthetic PostgreSQL final-row failure"):
                apply_reviewed_mapping(session, reviewed)
            assert session.is_active
            assert not session.in_transaction()

    assert update_count == 2
    assert transaction_events == {"commit": 0, "rollback": 1}
    assert _full_food_state(database_engine, food_ids) == before

    with Session(database_engine) as session:
        event.listen(session, "after_commit", count_commit)
        event.listen(session, "after_rollback", count_rollback)
        result = apply_reviewed_mapping(session, reviewed)
    assert result == {"applied_count": 2, "food_ids": [str(value) for value in food_ids]}
    assert transaction_events == {"commit": 1, "rollback": 1}
    after_retry = _full_food_state(database_engine, food_ids)
    _assert_resolution_only_change(
        before,
        after_retry,
        {
            "food_category_key": "fruits",
            "grain_type": None,
            "baked_good_type": None,
            "grain_starch_type": None,
            "taxonomy_review_required": False,
        },
    )

    with Session(database_engine) as session:
        event.listen(session, "after_commit", count_commit)
        event.listen(session, "after_rollback", count_rollback)
        with pytest.raises(RuntimeError, match="Stale taxonomy review context"):
            apply_reviewed_mapping(session, reviewed)
    assert transaction_events == {"commit": 1, "rollback": 2}
    assert _full_food_state(database_engine, food_ids) == after_retry


def test_plan022_postgresql_valid_batch_commits_all_once(
    plan022_postgres: tuple[Engine, list[UUID]],
) -> None:
    database_engine, food_ids = plan022_postgres
    with Session(database_engine) as session:
        result = apply_reviewed_mapping(
            session,
            [
                _review_item(food_ids[1], "Postgres final"),
                _review_item(food_ids[0], "Postgres first"),
            ],
        )

    assert result == {"applied_count": 2, "food_ids": [str(value) for value in food_ids]}
    assert _food_state(database_engine, food_ids) == [
        (food_ids[0], "fruits", None, None, None, False),
        (food_ids[1], "fruits", None, None, None, False),
    ]
