from copy import deepcopy
from uuid import UUID

from sqlmodel import Session, SQLModel, create_engine

from app.core.auth import PrincipalContext
from app.models import Principal

from scripts.import_foods_batch_001 import (
    MappingDecisionNeeded,
    apply_import,
    calculate_unit_values,
    dry_run,
    map_record,
)

TEST_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000001")
TEST_PRINCIPAL = PrincipalContext(TEST_PRINCIPAL_ID)


def sample_record(**overrides):
    record = {
        "name": "طعام تجريبي",
        "nutrition_basis_amount": 100,
        "nutrition_basis_unit": "g",
        "calories": 200,
        "protein_g": 10,
        "carbohydrates_g": 20,
        "fat_g": 8,
        "default_unit_name": "حصة",
        "default_unit_amount": 25,
        "default_unit_base": "g",
        "fiber_g": None,
        "total_sugar_g": 0,
        "notes": "ملاحظة المصدر.",
        "data_source": "مصدر تجريبي.",
        "data_quality": "estimated",
    }
    record.update(overrides)
    return record


def test_transport_mapping_preserves_null_and_explicit_zero() -> None:
    mapped = map_record(sample_record())

    assert mapped["nutrition_basis"] == "per_100g"
    assert mapped["default_unit_type"] == "serving"
    assert mapped["carb_g"] == 20
    assert mapped["sugar_g"] == 0
    assert mapped["fiber_g"] is None
    assert mapped["added_sugar_g"] is None
    assert mapped["notes"].startswith("جودة البيانات: تقديرية.")


def test_arabic_unit_mapping_and_unsupported_container() -> None:
    assert map_record(sample_record(default_unit_name="شريحة"))["default_unit_type"] == "slice"
    assert map_record(sample_record(default_unit_name="حبة"))["default_unit_type"] == "piece"
    assert map_record(sample_record(default_unit_name="قطعة"))["default_unit_type"] == "piece"

    try:
        map_record(sample_record(default_unit_name="علبة"))
    except MappingDecisionNeeded as error:
        assert "Decision Needed" in str(error)
    else:
        raise AssertionError("علبة must remain blocked until Product decides its mapping.")


def test_default_unit_calculation_uses_per_100_values() -> None:
    values = calculate_unit_values(map_record(sample_record()))

    assert values["calories"] == 50
    assert values["protein_g"] == 2.5
    assert values["carb_g"] == 5
    assert values["fat_g"] == 2
    assert values["fiber_g"] is None
    assert values["sugar_g"] == 0


def test_apply_import_is_idempotent() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    dataset = {"record_count": 1, "foods": [sample_record()]}
    with Session(engine) as session:
        session.add(Principal(id=TEST_PRINCIPAL_ID))
        session.commit()
        first = apply_import(session, TEST_PRINCIPAL, deepcopy(dataset))
        second = apply_import(session, TEST_PRINCIPAL, deepcopy(dataset))

    assert first[0].status == "inserted"
    assert second[0].status == "duplicate"
    assert second[0].food_id == first[0].food_id


def test_dry_run_blocks_only_unsupported_unit() -> None:
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    dataset = {
        "record_count": 2,
        "foods": [sample_record(), sample_record(name="عبوة تجريبية", default_unit_name="علبة")],
    }
    with Session(engine) as session:
        session.add(Principal(id=TEST_PRINCIPAL_ID))
        session.commit()
        results = dry_run(session, TEST_PRINCIPAL, dataset)

    assert [result.status for result in results] == ["valid", "blocked_decision"]
