from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier, Event
from time import monotonic
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, select

from app.core.auth import PrincipalContext
from app.models import (
    ContributionDataStatus,
    DefaultUnitType,
    DiaryEntry,
    Food,
    FoodAnalyticalTrait,
    FoodGroupContribution,
    FoodStatus,
    MealType,
    NutritionBasis,
    Principal,
    UnitBasis,
)
from app.schemas import DiaryEntryCreate, FoodUpdate
from app.services import diary as diary_service
from app.services import food as food_service

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
PRINCIPAL = PrincipalContext(PRINCIPAL_ID)
ENTRY_DATE = date(2026, 7, 22)


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL lock tests.")
    database = make_url(url).database or ""
    if not database.startswith("mynutri_test_"):
        pytest.fail("Concurrency tests refuse a database without the mynutri_test_ prefix.")
    return url


def _run_alembic(url: str, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def postgres_food() -> tuple[Engine, UUID]:
    url = _database_url()
    engine = create_engine(url)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    _run_alembic(url, "upgrade", "head")
    with Session(engine) as session:
        principal = Principal(id=PRINCIPAL_ID)
        food = Food(
            principal_id=PRINCIPAL_ID,
            name="Old complete",
            normalized_name="old complete",
            food_category_key="grains_starches",
            grain_type="whole",
            grain_starch_type="oats",
            nutrition_basis=NutritionBasis.per_100g,
            default_unit_type=DefaultUnitType.serving,
            unit_amount=50,
            unit_basis=UnitBasis.g,
            calories=200,
            protein_g=10,
            carb_g=20,
            fat_g=5,
            fiber_g=4,
        )
        session.add(principal)
        session.add(food)
        session.flush()
        session.add(
            FoodGroupContribution(
                principal_id=PRINCIPAL_ID,
                food_id=food.id,
                group_key="whole_grains",
                amount_per_100_basis=80,
                data_status=ContributionDataStatus.known,
                food_group_rules_version="1.0.0",
            )
        )
        session.add(
            FoodAnalyticalTrait(
                principal_id=PRINCIPAL_ID,
                food_id=food.id,
                trait_key="processed",
                food_group_rules_version="1.0.0",
            )
        )
        session.commit()
        food_id = food.id
    yield engine, food_id
    engine.dispose()


def _set_thread_name(session: Session, name: str) -> None:
    session.exec(text("SET LOCAL lock_timeout = '10s'"))
    session.exec(text("SELECT set_config('application_name', :name, true)").bindparams(name=name))


def _wait_for_lock_wait(engine: Engine, name: str) -> None:
    deadline = monotonic() + 10
    while monotonic() < deadline:
        with engine.connect() as connection:
            waiting = connection.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE application_name=:name AND wait_event_type='Lock'"
                ),
                {"name": name},
            ).scalar_one()
        if waiting:
            return
    pytest.fail(f"{name} never entered a PostgreSQL lock wait")


def _payload(food_id: UUID) -> DiaryEntryCreate:
    return DiaryEntryCreate(
        entry_date=ENTRY_DATE,
        food_id=food_id,
        quantity=1,
        meal_type=MealType.breakfast,
    )


def _new_food_payload() -> FoodUpdate:
    return FoodUpdate.model_validate(
        {
            "name": "New complete",
            "calories": 400,
            "fiber_g": 12,
            "group_contributions": [
                {
                    "group_key": "fruits",
                    "amount_per_100_basis": 60,
                    "data_status": "estimated",
                }
            ],
            "analytical_traits": ["salted"],
        }
    )


def _log(engine: Engine, food_id: UUID, name: str) -> UUID:
    with Session(engine) as session:
        _set_thread_name(session, name)
        return diary_service.create_entry(session, PRINCIPAL, _payload(food_id)).id


def _update(engine: Engine, food_id: UUID, name: str) -> None:
    with Session(engine) as session:
        _set_thread_name(session, name)
        food_service.update_food(session, PRINCIPAL, food_id, _new_food_payload())


def _archive(engine: Engine, food_id: UUID, name: str) -> None:
    with Session(engine) as session:
        _set_thread_name(session, name)
        food_service.archive_food(session, PRINCIPAL, food_id)


def _delete(engine: Engine, food_id: UUID, name: str) -> bool:
    with Session(engine) as session:
        _set_thread_name(session, name)
        return food_service.delete_food(session, PRINCIPAL, food_id)


def _assert_snapshot(snapshot: dict, version: str) -> None:
    if version == "old":
        assert snapshot["food"]["name"] == "Old complete"
        assert snapshot["nutrition"]["calories"] == 100
        assert snapshot["nutrition"]["fiber_g"] == 2
        assert snapshot["food_groups"]["contributions"] == [
            {
                "group_key": "whole_grains",
                "subtype_key": None,
                "amount_per_captured_unit": 40,
                "data_status": "known",
            }
        ]
        assert snapshot["food_groups"]["traits"] == ["processed"]
    else:
        assert snapshot["food"]["name"] == "New complete"
        assert snapshot["nutrition"]["calories"] == 200
        assert snapshot["nutrition"]["fiber_g"] == 6
        assert snapshot["food_groups"]["contributions"] == [
            {
                "group_key": "fruits",
                "subtype_key": None,
                "amount_per_captured_unit": 30,
                "data_status": "estimated",
            }
        ]
        assert snapshot["food_groups"]["traits"] == ["salted"]


def _entry_snapshot(engine: Engine, entry_id: UUID) -> dict:
    with Session(engine) as session:
        entry = session.get(DiaryEntry, entry_id)
        assert entry is not None
        return entry.nutrition_snapshot


def _not_found(future: Future[UUID]) -> None:
    with pytest.raises(HTTPException) as error:
        future.result(timeout=15)
    assert error.value.status_code == 404


@pytest.mark.migration
def test_update_race_logger_first_is_old_then_new(postgres_food, monkeypatch) -> None:
    engine, food_id = postgres_food
    locked = Event()
    release = Event()
    original = diary_service._create_snapshot_v3_from_locked_food

    def paused_builder(session, food):
        locked.set()
        assert release.wait(10)
        return original(session, food)

    monkeypatch.setattr(diary_service, "_create_snapshot_v3_from_locked_food", paused_builder)
    with ThreadPoolExecutor(max_workers=2) as executor:
        logged = executor.submit(_log, engine, food_id, "logger-first")
        assert locked.wait(10)
        written = executor.submit(_update, engine, food_id, "writer-waits")
        _wait_for_lock_wait(engine, "writer-waits")
        release.set()
        first_id = logged.result(timeout=15)
        written.result(timeout=15)

    _assert_snapshot(_entry_snapshot(engine, first_id), "old")
    monkeypatch.setattr(diary_service, "_create_snapshot_v3_from_locked_food", original)
    _assert_snapshot(_entry_snapshot(engine, _log(engine, food_id, "later-log")), "new")


@pytest.mark.migration
def test_update_race_writer_first_logger_reloads_complete_new(postgres_food, monkeypatch) -> None:
    engine, food_id = postgres_food
    locked = Event()
    release = Event()
    original = food_service._validated_update_data

    def paused_validation(session, principal, food, payload):
        locked.set()
        assert release.wait(10)
        return original(session, principal, food, payload)

    monkeypatch.setattr(food_service, "_validated_update_data", paused_validation)
    with ThreadPoolExecutor(max_workers=2) as executor:
        written = executor.submit(_update, engine, food_id, "writer-first")
        assert locked.wait(10)
        logged = executor.submit(_log, engine, food_id, "logger-waits")
        _wait_for_lock_wait(engine, "logger-waits")
        release.set()
        written.result(timeout=15)
        entry_id = logged.result(timeout=15)

    _assert_snapshot(_entry_snapshot(engine, entry_id), "new")


@pytest.mark.migration
def test_archive_race_logger_first_logs_then_archives(postgres_food, monkeypatch) -> None:
    engine, food_id = postgres_food
    locked = Event()
    release = Event()
    original = diary_service._create_snapshot_v3_from_locked_food

    def paused_builder(session, food):
        locked.set()
        assert release.wait(10)
        return original(session, food)

    monkeypatch.setattr(diary_service, "_create_snapshot_v3_from_locked_food", paused_builder)
    with ThreadPoolExecutor(max_workers=2) as executor:
        logged = executor.submit(_log, engine, food_id, "archive-log-first")
        assert locked.wait(10)
        archived = executor.submit(_archive, engine, food_id, "archive-waits")
        _wait_for_lock_wait(engine, "archive-waits")
        release.set()
        entry_id = logged.result(timeout=15)
        archived.result(timeout=15)

    _assert_snapshot(_entry_snapshot(engine, entry_id), "old")
    with Session(engine) as session:
        assert session.get(Food, food_id).status == FoodStatus.archived


@pytest.mark.migration
def test_archive_race_archive_first_prevents_logging(postgres_food, monkeypatch) -> None:
    engine, food_id = postgres_food
    locked = Event()
    release = Event()
    original = food_service._archive_locked_food

    def paused_archive(principal, food):
        locked.set()
        assert release.wait(10)
        return original(principal, food)

    monkeypatch.setattr(food_service, "_archive_locked_food", paused_archive)
    with ThreadPoolExecutor(max_workers=2) as executor:
        archived = executor.submit(_archive, engine, food_id, "archive-first")
        assert locked.wait(10)
        logged = executor.submit(_log, engine, food_id, "archive-logger-waits")
        _wait_for_lock_wait(engine, "archive-logger-waits")
        release.set()
        archived.result(timeout=15)
        _not_found(logged)


@pytest.mark.migration
def test_delete_race_logger_first_archives_used_food(postgres_food, monkeypatch) -> None:
    engine, food_id = postgres_food
    locked = Event()
    release = Event()
    original = diary_service._create_snapshot_v3_from_locked_food

    def paused_builder(session, food):
        locked.set()
        assert release.wait(10)
        return original(session, food)

    monkeypatch.setattr(diary_service, "_create_snapshot_v3_from_locked_food", paused_builder)
    with ThreadPoolExecutor(max_workers=2) as executor:
        logged = executor.submit(_log, engine, food_id, "delete-log-first")
        assert locked.wait(10)
        deleted = executor.submit(_delete, engine, food_id, "delete-waits")
        _wait_for_lock_wait(engine, "delete-waits")
        release.set()
        logged.result(timeout=15)
        assert deleted.result(timeout=15) is False

    with Session(engine) as session:
        assert session.get(Food, food_id).status == FoodStatus.archived
        assert session.exec(select(DiaryEntry).where(DiaryEntry.food_id == food_id)).first()


@pytest.mark.migration
def test_delete_race_delete_first_prevents_logging_missing_food(postgres_food, monkeypatch) -> None:
    engine, food_id = postgres_food
    locked = Event()
    release = Event()
    original = food_service.get_food_for_update

    def paused_loader(session, principal, target_id, *, include_archived=False):
        food = original(
            session, principal, target_id, include_archived=include_archived
        )
        locked.set()
        assert release.wait(10)
        return food

    monkeypatch.setattr(food_service, "get_food_for_update", paused_loader)
    with ThreadPoolExecutor(max_workers=2) as executor:
        deleted = executor.submit(_delete, engine, food_id, "delete-first")
        assert locked.wait(10)
        logged = executor.submit(_log, engine, food_id, "delete-logger-waits")
        _wait_for_lock_wait(engine, "delete-logger-waits")
        release.set()
        assert deleted.result(timeout=15) is True
        _not_found(logged)

    with Session(engine) as session:
        assert session.get(Food, food_id) is None


@pytest.mark.migration
def test_two_concurrent_diary_readers_share_food_lock(postgres_food, monkeypatch) -> None:
    engine, food_id = postgres_food
    readers = Barrier(2, timeout=10)
    original = diary_service._create_snapshot_v3_from_locked_food

    def synchronized_builder(session, food):
        readers.wait()
        return original(session, food)

    monkeypatch.setattr(
        diary_service, "_create_snapshot_v3_from_locked_food", synchronized_builder
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(_log, engine, food_id, "reader-one")
        second = executor.submit(_log, engine, food_id, "reader-two")
        first_id = first.result(timeout=15)
        second_id = second.result(timeout=15)

    _assert_snapshot(_entry_snapshot(engine, first_id), "old")
    _assert_snapshot(_entry_snapshot(engine, second_id), "old")
