from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError
from decimal import Decimal
from fractions import Fraction
from importlib.resources import files
from pathlib import Path

import pytest

from app.labs.catalog import _load_catalog_bytes, compile_rule_slices, get_catalog, load_catalog
from app.labs.types import DecisionRule, ReferenceRule


APPROVED_ARTIFACT_SHA256 = "d6f0d04cc8e623f4cb7427d1cbed5fc5a8580965dc87e2d0c5359578e0e956dc"
EXPECTED_KEYS = set(
    """hba1c total_cholesterol ldl_c hdl_c triglycerides wbc rbc hemoglobin
hematocrit platelets mcv mch mchc rdw neutrophils_abs neutrophils_pct lymphocytes_abs
lymphocytes_pct monocytes_abs monocytes_pct eosinophils_abs eosinophils_pct
basophils_abs basophils_pct mpv ferritin serum_iron tibc transferrin_saturation
vitamin_d_25oh vitamin_b12 vitamin_b6_plp zinc creatinine bun uric_acid sodium
potassium chloride bicarbonate calcium_total corrected_calcium magnesium alt ast alp
total_bilirubin albumin tsh free_t4 free_t3""".split()
)
EXPECTED_PANELS = {
    "lipid_panel": ("total_cholesterol", "ldl_c", "hdl_c", "triglycerides"),
    "cbc": (
        "wbc",
        "rbc",
        "hemoglobin",
        "hematocrit",
        "platelets",
        "mcv",
        "mch",
        "mchc",
        "rdw",
        "neutrophils_abs",
        "neutrophils_pct",
        "lymphocytes_abs",
        "lymphocytes_pct",
        "monocytes_abs",
        "monocytes_pct",
        "eosinophils_abs",
        "eosinophils_pct",
        "basophils_abs",
        "basophils_pct",
        "mpv",
    ),
    "iron_studies": ("ferritin", "serum_iron", "tibc", "transferrin_saturation"),
    "kidney_panel": ("creatinine", "bun"),
    "electrolytes_panel": (
        "sodium",
        "potassium",
        "chloride",
        "bicarbonate",
        "calcium_total",
        "corrected_calcium",
        "magnesium",
    ),
    "liver_panel": ("alt", "ast", "alp", "total_bilirubin", "albumin"),
    "thyroid_panel": ("tsh", "free_t4", "free_t3"),
}
EXPECTED_STATUS_METADATA = {
    "low": ("منخفض", "outside"),
    "in_range": ("ضمن النطاق", "within"),
    "high": ("مرتفع", "outside"),
    "normal": ("طبيعي", "within"),
    "prediabetes_range": ("نطاق ما قبل السكري", "caution"),
    "diabetes_range": ("نطاق السكري", "outside"),
    "desirable": ("مرغوب", "within"),
    "above_desirable": ("أعلى من المرغوب", "caution"),
    "borderline_high": ("مرتفع حدّيًا", "caution"),
    "very_high": ("مرتفع جدًا", "outside"),
    "acceptable": ("مقبول", "within"),
    "deficient": ("نطاق النقص", "outside"),
    "inadequate": ("غير كافٍ", "caution"),
    "adequate_for_most": ("كافٍ لمعظم الأشخاص", "within"),
    "borderline": ("حدّي", "caution"),
    "in_reference": ("ضمن النطاق المرجعي", "within"),
}
STANDALONE_KEYS = {
    "hba1c",
    "vitamin_d_25oh",
    "vitamin_b12",
    "vitamin_b6_plp",
    "zinc",
    "uric_acid",
}
EXCLUDED_KEYS = {
    "fasting_glucose",
    "ogtt",
    "fasting_insulin",
    "non_hdl_c",
    "egfr",
    "urine_acr",
    "hs_crp",
    "folate",
    "phosphorus",
    "ggt",
    "total_protein",
    "urea",
    "mentzer_index",
}
_APPROVED_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "labs_catalog_v1_approved.json"
_APPROVED_FIXTURE = json.loads(_APPROVED_FIXTURE_PATH.read_text(encoding="utf-8"))
EXPECTED_CONVERSIONS = tuple(
    (test["test_key"], test["alternate_unit_conversion"])
    for test in _APPROVED_FIXTURE["approved_catalog"]["tests"]
    if test["alternate_unit_conversion"] is not None
)
_SPECIAL_AGE_BANDS = {
    ("ferritin", "female"): ((18, 51), (51, None)),
    ("calcium_total", "male"): ((18, 60), (60, None)),
    ("calcium_total", "female"): ((18, 60), (60, None)),
    ("alp", "male"): ((18, 19), (19, None)),
    ("tsh", "male"): ((18, 20), (20, None)),
    ("tsh", "female"): ((18, 20), (20, None)),
    ("free_t4", "male"): ((18, 20), (20, None)),
    ("free_t4", "female"): ((18, 20), (20, None)),
    ("free_t3", "male"): ((18, 19), (19, None)),
    ("free_t3", "female"): ((18, 19), (19, None)),
}
EXPECTED_SLICE_INDEX = tuple(
    (key, sex, minimum, maximum)
    for key in sorted(EXPECTED_KEYS)
    for sex in ("male", "female")
    for minimum, maximum in _SPECIAL_AGE_BANDS.get((key, sex), ((18, None),))
)


@pytest.fixture(scope="module")
def approved_fixture() -> dict[str, object]:
    return _APPROVED_FIXTURE


def _mutable_approved_catalog(approved_fixture: dict[str, object]) -> dict[str, object]:
    return copy.deepcopy(approved_fixture["approved_catalog"])


def _load_mutation(raw: dict[str, object]) -> object:
    return _load_catalog_bytes(json.dumps(raw, ensure_ascii=False).encode("utf-8"))


def test_packaged_catalog_is_the_approved_golden_catalog(approved_fixture: dict[str, object]) -> None:
    assert approved_fixture["approved_artifact_sha256"] == APPROVED_ARTIFACT_SHA256
    raw = files("app.labs").joinpath("catalog.v1.json").read_bytes()
    assert json.loads(raw) == approved_fixture["approved_catalog"]
    assert load_catalog().content_sha256 == hashlib.sha256(raw).hexdigest()


def test_exact_approved_catalog() -> None:
    catalog = load_catalog()

    assert catalog.version == "mynutri-labs-v1.0"
    assert set(catalog.tests) == EXPECTED_KEYS
    assert len(catalog.categories) == 15
    assert [len(panel.test_keys) for panel in catalog.panels] == [4, 20, 4, 2, 7, 5, 3]
    assert {panel.key: panel.test_keys for panel in catalog.panels} == EXPECTED_PANELS
    assert isinstance(catalog.tests["mcv"].raw_rule, ReferenceRule)
    assert catalog.tests["mcv"].raw_rule.high == Decimal("97.93")
    assert isinstance(catalog.tests["mpv"].raw_rule, ReferenceRule)
    assert catalog.tests["mpv"].raw_rule.low == Decimal("8.34")
    assert catalog.tests["vitamin_d_25oh"].conversion.multiply == Decimal("2.496")
    assert catalog.tests["vitamin_b12"].conversion.multiply == Decimal("0.7378")


def test_catalog_retains_empty_categories_and_exact_membership_contract() -> None:
    catalog = load_catalog()
    used_categories = {test.primary_category for test in catalog.tests.values()}
    empty_categories = {category.key for category in catalog.categories} - used_categories
    panel_members = {key for panel in catalog.panels for key in panel.test_keys}

    assert empty_categories == {"hormones", "inflammation", "coagulation", "pancreas", "cardiac"}
    assert EXPECTED_KEYS - panel_members == STANDALONE_KEYS
    assert panel_members - EXPECTED_KEYS == set()
    assert set(catalog.tests).isdisjoint(EXCLUDED_KEYS)
    assert not hasattr(catalog, "derived_dependencies")


def test_catalog_context_and_unit_counts_are_exact() -> None:
    catalog = load_catalog()

    assert {test.key for test in catalog.tests.values() if test.fasting_assumption == "fasting"} == {
        "total_cholesterol",
        "ldl_c",
        "hdl_c",
        "triglycerides",
        "ferritin",
        "serum_iron",
        "tibc",
        "transferrin_saturation",
    }
    assert sum(test.conversion is not None for test in catalog.tests.values()) == 33
    assert sum(len(test.supported_units) == 1 for test in catalog.tests.values()) == 18


@pytest.mark.parametrize(
    ("key", "raw_conversion"), EXPECTED_CONVERSIONS, ids=[item[0] for item in EXPECTED_CONVERSIONS]
)
def test_each_approved_conversion_preserves_exact_decimal_coefficients(
    key: str, raw_conversion: dict[str, object]
) -> None:
    catalog = load_catalog()

    assert len(EXPECTED_CONVERSIONS) == 33
    conversion = catalog.tests[key].conversion
    assert conversion is not None, key
    assert conversion.from_unit == raw_conversion["from"], key
    assert conversion.to_unit == raw_conversion["to"], key
    assert conversion.pre_offset == Decimal(raw_conversion["pre_offset"]), key
    assert conversion.multiply == Decimal(raw_conversion["multiply"]), key
    assert conversion.divide == Decimal(raw_conversion["divide"]), key


def test_compiled_slice_index_matches_every_approved_test_sex_and_age_band() -> None:
    catalog = load_catalog()
    slices = [rule_slice for test in catalog.tests.values() for rule_slice in test.rule_slices]

    assert len(slices) == 112
    assert {
        (test.key, rule_slice.sex, rule_slice.min_age, rule_slice.max_age_exclusive)
        for test in catalog.tests.values()
        for rule_slice in test.rule_slices
    } == set(EXPECTED_SLICE_INDEX)


@pytest.mark.parametrize(
    ("key", "sex", "minimum", "maximum"),
    EXPECTED_SLICE_INDEX,
    ids=[f"{key}-{sex}-{minimum}-{maximum or 'open'}" for key, sex, minimum, maximum in EXPECTED_SLICE_INDEX],
)
def test_each_test_sex_and_age_slice_has_contiguous_compiled_zones(
    key: str, sex: str, minimum: int, maximum: int | None
) -> None:
    test = load_catalog().tests[key]
    assert compile_rule_slices(test) == test.rule_slices
    matches = [
        rule_slice
        for rule_slice in test.rule_slices
        if rule_slice.sex == sex
        and rule_slice.min_age == minimum
        and rule_slice.max_age_exclusive == maximum
    ]
    assert len(matches) == 1
    rule_slice = matches[0]
    if test.omit_unreachable_low:
        assert rule_slice.zones[0].low == Fraction(0)
    else:
        assert rule_slice.zones[0].low is None
    assert rule_slice.zones[-1].high is None
    for previous, following in zip(rule_slice.zones, rule_slice.zones[1:], strict=False):
        assert previous.high == following.low
        assert previous.high_inclusive != following.low_inclusive


def test_reference_compilation_omits_only_unreachable_zero_low_zones() -> None:
    catalog = load_catalog()

    for key in ("eosinophils_pct", "basophils_pct", "total_bilirubin"):
        zones = catalog.tests[key].rule_slices[0].zones
        assert [zone.status for zone in zones] == ["in_range", "high"]
        assert zones[0].low == Fraction(0)
        assert zones[0].low_inclusive is True

    zones = catalog.tests["mcv"].rule_slices[0].zones
    assert [(zone.status, zone.low, zone.high) for zone in zones] == [
        ("low", None, Fraction(391, 5)),
        ("in_range", Fraction(391, 5), Fraction(9793, 100)),
        ("high", Fraction(9793, 100), None),
    ]


def test_decision_and_age_boundaries_compile_exactly() -> None:
    catalog = load_catalog()
    hba1c = catalog.tests["hba1c"]
    assert isinstance(hba1c.raw_rule, DecisionRule)
    assert [
        (zone.status, zone.low, zone.low_inclusive, zone.high, zone.high_inclusive)
        for zone in hba1c.rule_slices[0].zones
    ] == [
        ("normal", None, False, Fraction(57, 10), False),
        ("prediabetes_range", Fraction(57, 10), True, Fraction(13, 2), False),
        ("diabetes_range", Fraction(13, 2), True, None, False),
    ]
    female_ferritin = [
        rule_slice
        for rule_slice in catalog.tests["ferritin"].rule_slices
        if rule_slice.sex == "female"
    ]
    assert [(item.min_age, item.max_age_exclusive) for item in female_ferritin] == [
        (18, 51),
        (51, None),
    ]
    male_alp = [
        rule_slice for rule_slice in catalog.tests["alp"].rule_slices if rule_slice.sex == "male"
    ]
    assert [(item.min_age, item.max_age_exclusive) for item in male_alp] == [
        (18, 19),
        (19, None),
    ]


def test_status_metadata_has_approved_arabic_labels_and_calm_tones() -> None:
    catalog = load_catalog()
    assert {
        code: (metadata.label_ar, metadata.tone) for code, metadata in catalog.statuses.items()
    } == EXPECTED_STATUS_METADATA


def test_catalog_graph_is_immutable() -> None:
    catalog = get_catalog()
    assert get_catalog() is catalog

    with pytest.raises(TypeError):
        catalog.tests["new"] = catalog.tests["hba1c"]
    with pytest.raises(TypeError):
        catalog.statuses["low"] = catalog.statuses["high"]
    with pytest.raises(FrozenInstanceError):
        catalog.tests["hba1c"].name_en = "changed"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda raw: raw.update({"unknown": True}), "unknown fields"),
        (
            lambda raw: raw["categories"].append(copy.deepcopy(raw["categories"][0])),
            "duplicate category key",
        ),
        (
            lambda raw: raw["tests"][0].update({"primary_category": "missing"}),
            "absent category",
        ),
        (
            lambda raw: raw["panels"][0]["test_keys"].append("missing"),
            "orphan panel member",
        ),
        (
            lambda raw: raw["panels"][0]["test_keys"].append(raw["panels"][0]["test_keys"][0]),
            "repeated panel member",
        ),
        (
            lambda raw: raw["tests"][0].update({"default_input_unit": "unsupported"}),
            "unsupported default unit",
        ),
        (
            lambda raw: raw["tests"][0].update({"canonical_unit": "unsupported"}),
            "unsupported canonical unit",
        ),
        (
            lambda raw: raw["tests"][0]["alternate_unit_conversion"].update(
                {"multiply": 10.929}
            ),
            "plain decimal string",
        ),
        (
            lambda raw: raw["tests"][0]["alternate_unit_conversion"].update({"divide": "0"}),
            "zero conversion divisor",
        ),
        (
            lambda raw: raw["tests"][40]["rule"]["age_bands"][0].update(
                {"min_age_inclusive": 19}
            ),
            "age coverage",
        ),
        (
            lambda raw: raw["tests"][40]["rule"]["age_bands"][1].update(
                {"min_age_inclusive": 59}
            ),
            "overlapping age bands",
        ),
        (
            lambda raw: raw["tests"][0]["rule"]["bands"][1].update({"min": "5.8"}),
            "gapped decision zones",
        ),
        (
            lambda raw: raw["tests"][0].update(
                {
                    "rule": {
                        "kind": "sex_decision",
                        "male": copy.deepcopy(raw["tests"][0]["rule"]),
                    }
                }
            ),
            "unknown fields",
        ),
    ],
)
def test_strict_loader_rejects_invalid_catalog_mutations(
    approved_fixture: dict[str, object], mutation: object, message: str
) -> None:
    raw = _mutable_approved_catalog(approved_fixture)
    mutation(raw)

    with pytest.raises(ValueError, match=message):
        _load_mutation(raw)


def test_strict_loader_rejects_duplicate_json_object_keys() -> None:
    duplicated = b'{"catalog_version":"one","catalog_version":"two","categories":[],"panels":[],"tests":[]}'

    with pytest.raises(ValueError, match="duplicate JSON key"):
        _load_catalog_bytes(duplicated)
