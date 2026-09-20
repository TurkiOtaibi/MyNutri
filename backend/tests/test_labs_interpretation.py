"""Independent clinical examples transcribed from the approved V1 fixture.

These cases catch wrong inclusivity, wrong sex/age branches, rounded classification,
and historical chart ranges incorrectly resolved using today's age.
"""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

import pytest

from app.labs.catalog import load_catalog
from app.labs.types import Zone


# Every approved reference branch, without consulting the production rule compiler.
# key, sex, age, lower, upper
REFERENCES = [
    ("wbc", "male", 18, "3.4", "9.6"),
    ("rbc", "male", 18, "4.35", "5.65"),
    ("rbc", "female", 18, "3.92", "5.13"),
    ("hemoglobin", "male", 18, "13.2", "16.6"),
    ("hemoglobin", "female", 18, "11.6", "15.0"),
    ("hematocrit", "male", 18, "38.3", "48.6"),
    ("hematocrit", "female", 18, "35.5", "44.9"),
    ("platelets", "male", 18, "135", "317"),
    ("platelets", "female", 18, "157", "371"),
    ("mcv", "male", 18, "78.2", "97.93"),
    ("mch", "male", 18, "27", "33"),
    ("mch", "female", 18, "26", "33"),
    ("mchc", "male", 18, "32", "36"),
    ("rdw", "male", 18, "11.8", "14.5"),
    ("rdw", "female", 18, "12.2", "16.1"),
    ("neutrophils_abs", "male", 18, "1.56", "6.45"),
    ("neutrophils_pct", "male", 18, "37", "80"),
    ("lymphocytes_abs", "male", 18, "0.95", "3.07"),
    ("lymphocytes_pct", "male", 18, "20", "50"),
    ("monocytes_abs", "male", 18, "0.26", "0.81"),
    ("monocytes_pct", "male", 18, "2", "8"),
    ("eosinophils_abs", "male", 18, "0.03", "0.48"),
    ("eosinophils_pct", "male", 18, "0", "5"),
    ("basophils_abs", "male", 18, "0.01", "0.08"),
    ("basophils_pct", "male", 18, "0", "2.5"),
    ("mpv", "male", 18, "8.34", "12.3"),
    ("ferritin", "male", 18, "31", "409"),
    ("ferritin", "female", 18, "6", "175"),
    ("ferritin", "female", 51, "11", "328"),
    ("serum_iron", "male", 18, "50", "150"),
    ("serum_iron", "female", 18, "35", "145"),
    ("tibc", "male", 18, "250", "400"),
    ("transferrin_saturation", "male", 18, "14", "50"),
    ("vitamin_b6_plp", "male", 18, "5", "50"),
    ("zinc", "male", 18, "60", "106"),
    ("creatinine", "male", 18, "0.74", "1.35"),
    ("creatinine", "female", 18, "0.59", "1.04"),
    ("bun", "male", 18, "8", "24"),
    ("bun", "female", 18, "6", "21"),
    ("uric_acid", "male", 18, "3.7", "8.0"),
    ("uric_acid", "female", 18, "2.7", "6.1"),
    ("sodium", "male", 18, "135", "145"),
    ("potassium", "male", 18, "3.6", "5.2"),
    ("chloride", "male", 18, "98", "107"),
    ("bicarbonate", "male", 18, "22", "29"),
    ("calcium_total", "male", 18, "8.6", "10.0"),
    ("calcium_total", "male", 60, "8.8", "10.2"),
    ("corrected_calcium", "male", 18, "8.6", "10.2"),
    ("magnesium", "male", 18, "1.7", "2.3"),
    ("alt", "male", 18, "7", "55"),
    ("alt", "female", 18, "7", "45"),
    ("ast", "male", 18, "8", "48"),
    ("ast", "female", 18, "8", "43"),
    ("alp", "male", 18, "55", "149"),
    ("alp", "male", 19, "40", "129"),
    ("alp", "female", 18, "35", "104"),
    ("total_bilirubin", "male", 18, "0", "1.2"),
    ("albumin", "male", 18, "3.5", "5.0"),
    ("tsh", "male", 18, "0.5", "4.3"),
    ("tsh", "male", 20, "0.3", "4.2"),
    ("free_t4", "male", 18, "1.0", "1.6"),
    ("free_t4", "male", 20, "0.9", "1.7"),
    ("free_t3", "male", 18, "3.3", "5.3"),
    ("free_t3", "male", 19, "2.0", "4.4"),
]

# key, sex, boundary, below, exactly, above; eight independent decision branches.
DECISIONS = [
    ("hba1c", "male", "5.7", "normal", "prediabetes_range", "prediabetes_range"),
    ("hba1c", "male", "6.5", "prediabetes_range", "diabetes_range", "diabetes_range"),
    ("total_cholesterol", "male", "200", "desirable", "borderline_high", "borderline_high"),
    ("total_cholesterol", "male", "240", "borderline_high", "high", "high"),
    ("ldl_c", "male", "100", "desirable", "above_desirable", "above_desirable"),
    ("ldl_c", "male", "130", "above_desirable", "borderline_high", "borderline_high"),
    ("ldl_c", "male", "160", "borderline_high", "high", "high"),
    ("ldl_c", "male", "190", "high", "very_high", "very_high"),
    ("hdl_c", "male", "40", "low", "acceptable", "acceptable"),
    ("hdl_c", "female", "50", "low", "acceptable", "acceptable"),
    ("triglycerides", "male", "150", "normal", "borderline_high", "borderline_high"),
    ("triglycerides", "male", "200", "borderline_high", "high", "high"),
    ("triglycerides", "male", "500", "high", "very_high", "very_high"),
    ("vitamin_d_25oh", "male", "12", "deficient", "inadequate", "inadequate"),
    ("vitamin_d_25oh", "male", "20", "inadequate", "adequate_for_most", "adequate_for_most"),
    ("vitamin_d_25oh", "male", "50", "adequate_for_most", "adequate_for_most", "high"),
    ("vitamin_b12", "male", "150", "deficient", "borderline", "borderline"),
    ("vitamin_b12", "male", "400", "borderline", "borderline", "in_reference"),
    ("vitamin_b12", "male", "914", "in_reference", "in_reference", "high"),
]


def _boundary_examples():
    for key, sex, age, low, high in REFERENCES:
        for bound, statuses in (
            (low, ("low", "in_range", "in_range")),
            (high, ("in_range", "in_range", "high")),
        ):
            for delta, expected in zip(("-0.001", "0", "0.001"), statuses, strict=True):
                value = Decimal(bound) + Decimal(delta)
                yield key, sex, age, str(value), expected if value >= 0 else None
    for key, sex, bound, below, exact, above in DECISIONS:
        for delta, expected in zip(("-0.001", "0", "0.001"), (below, exact, above), strict=True):
            yield key, sex, 18, str(Decimal(bound) + Decimal(delta)), expected


BOUNDARIES = list(_boundary_examples())
assert len(REFERENCES) == 64
assert len(BOUNDARIES) == 147 * 3


@pytest.mark.parametrize(
    "key,value,expected",
    [
        ("hba1c", "5.699", "normal"),
        ("hba1c", "5.700", "prediabetes_range"),
        ("hba1c", "6.499", "prediabetes_range"),
        ("hba1c", "6.500", "diabetes_range"),
        ("mpv", "8.339", "low"),
        ("mpv", "8.340", "in_range"),
        ("mpv", "12.300", "in_range"),
        ("mpv", "12.301", "high"),
        ("neutrophils_pct", "36.99", "low"),
        ("neutrophils_pct", "37", "in_range"),
        ("neutrophils_pct", "80", "in_range"),
        ("neutrophils_pct", "80.01", "high"),
        ("eosinophils_pct", "0", "in_range"),
        ("eosinophils_pct", "5", "in_range"),
        ("eosinophils_pct", "5.01", "high"),
        ("basophils_pct", "0", "in_range"),
        ("basophils_pct", "2.5", "in_range"),
        ("basophils_pct", "2.51", "high"),
        ("vitamin_b12", "150", "borderline"),
        ("vitamin_b12", "400", "borderline"),
        ("vitamin_b12", "400.001", "in_reference"),
        ("vitamin_b12", "914", "in_reference"),
        ("vitamin_b12", "914.001", "high"),
        ("vitamin_d_25oh", "50", "adequate_for_most"),
        ("vitamin_d_25oh", "50.001", "high"),
    ],
)
def test_approved_examples(key, value, expected):
    from app.labs.interpretation import interpret

    test = load_catalog().tests[key]
    result = interpret(
        test,
        Decimal(value),
        test.canonical_unit,
        date(1990, 1, 1),
        "male",
        date(2026, 9, 19),
        "mynutri-labs-v1.0",
    )
    assert result.status_code == expected


@pytest.mark.parametrize("key,sex,age,value,expected", BOUNDARIES)
def test_all_147_approved_boundaries(key, sex, age, value, expected):
    from app.labs.interpretation import interpret

    test = load_catalog().tests[key]
    args = (
        test,
        Decimal(value),
        test.canonical_unit,
        date(2000, 1, 1),
        sex,
        date(2000 + age, 1, 1),
        "mynutri-labs-v1.0",
    )
    if expected is None:
        with pytest.raises(ValueError):
            interpret(*args)
    else:
        assert interpret(*args).status_code == expected


TRANSITIONS = [
    ("ferritin", "female", 51, "6", "175", "11", "328"),
    ("calcium_total", "male", 60, "8.6", "10.0", "8.8", "10.2"),
    ("calcium_total", "female", 60, "8.6", "10.0", "8.8", "10.2"),
    ("alp", "male", 19, "55", "149", "40", "129"),
    ("tsh", "male", 20, "0.5", "4.3", "0.3", "4.2"),
    ("tsh", "female", 20, "0.5", "4.3", "0.3", "4.2"),
    ("free_t4", "male", 20, "1.0", "1.6", "0.9", "1.7"),
    ("free_t4", "female", 20, "1.0", "1.6", "0.9", "1.7"),
    ("free_t3", "male", 19, "3.3", "5.3", "2.0", "4.4"),
    ("free_t3", "female", 19, "3.3", "5.3", "2.0", "4.4"),
]


def reference_bounds(zones):
    zone = next(zone for zone in zones if zone.status == "in_range")
    return zone.low, zone.high


@pytest.mark.parametrize("key,sex,age,old_low,old_high,new_low,new_high", TRANSITIONS)
@pytest.mark.parametrize("birth", [date(1960, 9, 20), date(1960, 2, 29)])
def test_actual_birthday_changes_rule_and_splits_chart(
    key, sex, age, old_low, old_high, new_low, new_high, birth
):
    from app.labs.interpretation import chart_zones, resolve_rule

    year = birth.year + age
    try:
        birthday = birth.replace(year=year)
    except ValueError:
        birthday = date(year, 3, 1)
    start, end = birthday - timedelta(days=1), birthday + timedelta(days=1)
    test = load_catalog().tests[key]
    old_bounds = (Fraction(old_low), Fraction(old_high))
    new_bounds = (Fraction(new_low), Fraction(new_high))
    assert reference_bounds(resolve_rule(test, birth, sex, start).zones) == old_bounds
    assert reference_bounds(resolve_rule(test, birth, sex, birthday).zones) == new_bounds
    segments = chart_zones(test, birth, sex, start, end)
    assert [(s.from_date, s.to_date_exclusive, s.age_min) for s in segments] == [
        (start, birthday, age - 1),
        (birthday, end + timedelta(days=1), age),
    ]
    assert [reference_bounds(s.zones) for s in segments] == [old_bounds, new_bounds]


@pytest.mark.parametrize("key,sex,age,low,high", REFERENCES)
def test_single_point_chart_uses_each_approved_reference_branch(key, sex, age, low, high):
    from app.labs.interpretation import chart_zones

    point = date(2000 + age, 1, 1)
    segments = chart_zones(load_catalog().tests[key], date(2000, 1, 1), sex, point, point)
    assert len(segments) == 1
    assert (segments[0].from_date, segments[0].to_date_exclusive) == (
        point,
        point + timedelta(days=1),
    )
    assert reference_bounds(segments[0].zones) == (Fraction(low), Fraction(high))
    assert segments[0].zones[-1].high is None
    assert (segments[0].zones[0].status == "low") == (Decimal(low) > 0)


@pytest.mark.parametrize("key,sex,bound,below,exact,above", DECISIONS)
def test_chart_decision_zone_boundary_inclusivity_matches_approved_cases(
    key, sex, bound, below, exact, above
):
    from app.labs.interpretation import chart_zones

    segments = chart_zones(
        load_catalog().tests[key], date(1990, 1, 1), sex, date(2026, 1, 1), date(2026, 9, 19)
    )
    assert len(segments) == 1
    zones = segments[0].zones
    lower = next(z for z in zones if z.status == below)
    upper = next(z for z in zones if z.status == above)
    assert lower.high == upper.low == Fraction(bound)
    assert lower.high_inclusive == (exact == below)
    assert upper.low_inclusive == (exact == above)
    assert zones[0].low is None and zones[-1].high is None


@pytest.mark.parametrize(
    "key,sex,age,low,high",
    [
        ("ferritin", "male", 51, "31", "409"),
        ("alp", "female", 19, "35", "104"),
    ],
)
def test_unaffected_sex_does_not_split_on_other_sex_transition(key, sex, age, low, high):
    from app.labs.interpretation import chart_zones

    birthday = date(1960 + age, 1, 1)
    segments = chart_zones(
        load_catalog().tests[key], date(1960, 1, 1), sex, birthday - timedelta(days=1), birthday
    )
    assert len(segments) == 1
    assert reference_bounds(segments[0].zones) == (Fraction(low), Fraction(high))


@pytest.mark.parametrize(
    "birth,before,adult",
    [
        (date(2008, 9, 20), date(2026, 9, 19), date(2026, 9, 20)),
        (date(2008, 2, 29), date(2026, 2, 28), date(2026, 3, 1)),
    ],
)
def test_adult_eligibility_and_neutral_age_preserve_leap_behavior(birth, before, adult):
    from app.core.calendar import age_on
    from app.labs.interpretation import resolve_rule

    test = load_catalog().tests["hba1c"]
    assert age_on(birth, before) == 17
    with pytest.raises(ValueError):
        resolve_rule(test, birth, "male", before)
    assert resolve_rule(test, birth, "male", adult).age_years == 18


def test_fresh_rules_reinterpret_unchanged_entered_facts():
    from app.labs.interpretation import interpret

    test = load_catalog().tests["hba1c"]
    facts = (Decimal("5.700"), "%", date(1990, 1, 1), "male", date(2026, 9, 19))
    before = interpret(test, *facts, "mynutri-labs-v1.0")
    zones = (
        Zone("normal", None, Fraction(6), False, False),
        Zone("prediabetes_range", Fraction(6), None, True, False),
    )
    revised = replace(test, rule_slices=tuple(replace(s, zones=zones) for s in test.rule_slices))
    after = interpret(revised, *facts, "synthetic-revision")
    assert (before.status_code, after.status_code) == ("prediabetes_range", "normal")
    assert before.canonical_exact == after.canonical_exact == Fraction(57, 10)
    assert before.display_value == after.display_value == "5.700"
    assert after.rule.zones == zones
    assert after.medical_rules_version == "synthetic-revision"


def test_invalid_sex_and_inverted_chart_interval_are_rejected():
    from app.labs.interpretation import chart_zones, resolve_rule

    test = load_catalog().tests["hba1c"]
    with pytest.raises(ValueError):
        resolve_rule(test, date(1990, 1, 1), "unknown", date(2026, 1, 1))
    with pytest.raises(ValueError):
        chart_zones(test, date(1990, 1, 1), "male", date(2026, 1, 2), date(2026, 1, 1))
