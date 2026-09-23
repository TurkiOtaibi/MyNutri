"""Exact approved transforms and adversarial decimal inputs, independent of engine output."""

from datetime import date
from decimal import Decimal, getcontext, localcontext
from fractions import Fraction

import pytest

from app.labs.catalog import load_catalog


# Canonical and alternate values are literal, exact physical equivalents.
TRANSFORMS = [
    ("hba1c", "5.700", "38.79795", "prediabetes_range"),
    ("total_cholesterol", "3867", "100", "high"),
    ("ldl_c", "3867", "100", "very_high"),
    ("hdl_c", "3867", "100", "acceptable"),
    ("triglycerides", "8857", "100", "very_high"),
    ("wbc", "100", "100", "high"),
    ("rbc", "100", "100", "high"),
    ("hemoglobin", "100", "1000", "high"),
    ("hematocrit", "100", "1", "high"),
    ("platelets", "100", "100", "low"),
    ("mchc", "100", "1000", "high"),
    ("neutrophils_abs", "100", "100", "high"),
    ("lymphocytes_abs", "100", "100", "high"),
    ("ferritin", "100", "100", "in_range"),
    ("serum_iron", "100", "17.91", "in_range"),
    ("tibc", "100", "17.91", "low"),
    ("vitamin_d_25oh", "100", "249.6", "high"),
    ("vitamin_b12", "100", "73.78", "deficient"),
    ("zinc", "100", "15.30", "in_range"),
    ("creatinine", "100", "8840", "high"),
    ("uric_acid", "100", "5948", "high"),
    ("sodium", "100", "100", "low"),
    ("potassium", "100", "100", "high"),
    ("chloride", "100", "100", "in_range"),
    ("bicarbonate", "100", "100", "high"),
    ("calcium_total", "100", "24.95", "high"),
    ("corrected_calcium", "100", "24.95", "high"),
    ("magnesium", "100", "41.14", "high"),
    ("total_bilirubin", "100", "1710", "high"),
    ("albumin", "100", "1000", "high"),
    ("tsh", "100", "100", "high"),
    ("free_t4", "100", "1287", "high"),
    ("free_t3", "100", "153.6", "high"),
]
assert len(TRANSFORMS) == 33


@pytest.mark.parametrize("key,canonical,alternate,status", TRANSFORMS)
def test_all_33_approved_transforms_and_physical_equivalence(key, canonical, alternate, status):
    from app.labs.interpretation import interpret
    from app.labs.numbers import from_canonical, to_canonical

    test = load_catalog().tests[key]
    unit = test.conversion.to_unit
    assert from_canonical(test, Fraction(canonical), unit) == Fraction(alternate)
    assert to_canonical(test, Decimal(alternate), unit) == Fraction(canonical)
    for text, entered_unit in ((canonical, test.canonical_unit), (alternate, unit)):
        result = interpret(
            test,
            Decimal(text),
            entered_unit,
            date(1990, 1, 1),
            "male",
            date(2026, 9, 19),
            "mynutri-labs-v1.0",
        )
        assert result.canonical_exact == Fraction(canonical)
        assert result.status_code == status
        assert result.display_unit == test.canonical_unit


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0005.700", "5.700"),
        ("٠٠٥٫٧٠٠", "5.700"),
        ("۰۰۵٫۷۰۰", "5.700"),
        ("000", "0"),
        ("0.000", "0.000"),
        (" 5", "5"),
        ("5 ", "5"),
        ("5\n", "5"),
        (" \t0005.700\r\n", "5.700"),
        (" \t٠٠٥٫٧٠٠\n", "5.700"),
        ("\n۰۰۵٫۷۰۰ \t", "5.700"),
        ("9" * 128, "9" * 128),
        (" \t" + "9" * 128 + "\n", "9" * 128),
        ("\n٠٫" + "١" * 126 + " ", "0." + "1" * 126),
        ("0." + "1" * 126, "0." + "1" * 126),
        ("0." + "0" * 125 + "1", "0." + "0" * 125 + "1"),
    ],
)
def test_normalization_preserves_fractional_zeros_and_128_character_exactness(raw, expected):
    from app.labs.numbers import normalize_decimal_text, parse_entered_decimal

    assert normalize_decimal_text(raw) == expected
    assert format(parse_entered_decimal(raw), "f") == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "-1",
        "-0",
        "+1",
        "1e2",
        "1E-2",
        "NaN",
        "Infinity",
        "-Infinity",
        "1,000",
        "١٬٠٠٠",
        "1,5",
        "<5",
        ">=5",
        "1_000",
        ".5",
        "5.",
        "1..2",
        " \t\r\n",
        "5 0",
        "5\n0",
        "5. 700",
        " ٥٫٧ ٠٠ ",
        "²",
        "５",
        "9" * 129,
        "0." + "1" * 127,
        " \t" + "9" * 129 + "\n",
        "\n٠٫" + "١" * 127 + " ",
    ],
)
def test_rejects_non_plain_or_oversized_input(raw):
    from app.labs.numbers import parse_entered_decimal

    with pytest.raises(ValueError):
        parse_entered_decimal(raw)


def test_hba1c_inverse_domain_does_not_increase_approved_input_minimum():
    from app.labs.numbers import from_canonical, to_canonical

    test = load_catalog().tests["hba1c"]
    assert to_canonical(test, Decimal("0"), "%") == 0
    assert to_canonical(test, Decimal("0"), "mmol/mol") == Fraction("2.15")
    assert from_canonical(test, Fraction("2.15"), "mmol/mol") == 0
    with pytest.raises(ValueError):
        from_canonical(test, Fraction("2.149"), "mmol/mol")


@pytest.mark.parametrize(
    "key,boundary,ratio,below,above,low_status,high_status",
    [
        (
            "total_cholesterol",
            "200",
            Fraction(20000, 3867),
            "5.171967",
            "5.171968",
            "desirable",
            "borderline_high",
        ),
        (
            "triglycerides",
            "150",
            Fraction(15000, 8857),
            "1.693575",
            "1.693576",
            "normal",
            "borderline_high",
        ),
    ],
)
def test_repeating_alternate_thresholds_have_exact_rational_brackets(
    key, boundary, ratio, below, above, low_status, high_status
):
    from app.labs.interpretation import interpret
    from app.labs.numbers import from_canonical

    test = load_catalog().tests[key]
    unit = test.conversion.to_unit
    assert from_canonical(test, Fraction(boundary), unit) == ratio
    assert Fraction(below) < ratio < Fraction(above)
    for text, expected in ((below, low_status), (above, high_status)):
        result = interpret(
            test,
            Decimal(text),
            unit,
            date(1990, 1, 1),
            "male",
            date(2026, 9, 19),
            "mynutri-labs-v1.0",
        )
        assert result.status_code == expected


def test_display_expands_precision_to_preserve_each_side_of_boundary():
    from app.labs.interpretation import resolve_rule
    from app.labs.numbers import format_canonical

    rule = resolve_rule(load_catalog().tests["hba1c"], date(1990, 1, 1), "male", date(2026, 9, 19))
    boundary = Fraction("5.7")
    for value in (boundary - Fraction(1, 3 * 10**130), boundary + Fraction(1, 3 * 10**130)):
        display, approximate = format_canonical(value, rule, Decimal("1"), False)
        assert approximate
        assert (Fraction(display) < boundary) == (value < boundary)
        assert (Fraction(display) > boundary) == (value > boundary)
        assert len(display) > 128


def test_identity_retains_zeros_and_terminating_conversion_is_exact_beyond_input_limit():
    from app.labs.interpretation import resolve_rule
    from app.labs.numbers import format_canonical, to_canonical

    test = load_catalog().tests["hba1c"]
    rule = resolve_rule(test, date(1990, 1, 1), "male", date(2026, 9, 19))
    assert format_canonical(Fraction("5.7"), rule, Decimal("5.700"), True) == ("5.700", False)
    huge = Fraction(10**140 + 1, 10**140)
    display, approximate = format_canonical(huge, rule, Decimal("1"), False)
    assert Fraction(display) == huge
    assert len(display) == 142
    assert approximate is False
    test = load_catalog().tests["creatinine"]
    entered = Decimal("9" * 128)
    assert to_canonical(test, entered, "µmol/L") == Fraction(entered) * Fraction(5, 442)


@pytest.mark.parametrize(
    "entered,expected_status",
    [
        ("674.3491" + "9" * 120, "in_reference"),
        ("674.3492" + "0" * 119 + "1", "high"),
    ],
)
def test_128_character_converted_inputs_keep_exact_side_after_display_rounding(
    entered, expected_status
):
    from app.labs.interpretation import interpret
    from app.labs.numbers import parse_entered_decimal

    assert len(entered) == 128
    result = interpret(
        load_catalog().tests["vitamin_b12"],
        parse_entered_decimal(entered),
        "pmol/L",
        date(1990, 1, 1),
        "male",
        date(2026, 9, 19),
        "mynutri-labs-v1.0",
    )
    assert result.status_code == expected_status
    assert result.canonical_exact == Fraction(entered) * Fraction(5000, 3689)
    assert (Fraction(result.display_value) > 914) == (expected_status == "high")
    assert (Fraction(result.display_value) < 914) == (expected_status == "in_reference")
    assert result.display_is_approximate


def test_global_decimal_precision_rounding_and_flags_are_unchanged():
    from app.labs.interpretation import interpret

    with localcontext() as context:
        context.prec = 3
        context.clear_flags()
        before = context.copy()
        result = interpret(
            load_catalog().tests["hba1c"],
            Decimal("38.79795"),
            "mmol/mol",
            date(1990, 1, 1),
            "male",
            date(2026, 9, 19),
            "mynutri-labs-v1.0",
        )
        assert result.canonical_exact == Fraction(57, 10)
        assert result.status_code == "prediabetes_range"
        repeated = interpret(
            load_catalog().tests["hba1c"],
            Decimal("1"),
            "mmol/mol",
            date(1990, 1, 1),
            "male",
            date(2026, 9, 19),
            "mynutri-labs-v1.0",
        )
        assert repeated.display_is_approximate
        assert repeated.display_value == "2.24150"
        assert getcontext().prec == before.prec
        assert getcontext().rounding == before.rounding
        assert getcontext().flags == before.flags


@pytest.mark.parametrize(
    "value,unit", [("-1", "%"), ("NaN", "%"), ("Infinity", "%"), ("1", "invalid")]
)
def test_conversion_rejects_invalid_decimal_domain_and_units(value, unit):
    from app.labs.numbers import to_canonical

    with pytest.raises(ValueError):
        to_canonical(load_catalog().tests["hba1c"], Decimal(value), unit)


def test_calendar_compatibility_keeps_old_clock_monkeypatch_seam(monkeypatch):
    from app.core import calendar
    from app.nutrition_rules import calculation
    from app.services import target_plans

    monkeypatch.setattr(calculation, "current_diary_date", lambda: date(2026, 9, 19))
    assert calculation.age_on(date(2008, 9, 20)) == 17
    monkeypatch.setattr(calendar, "current_diary_date", lambda: date(2026, 9, 20))
    assert calendar.age_on(date(2008, 9, 20)) == 18

    class Session:
        def get_bind(self):
            class Bind:
                class dialect:
                    name = "sqlite"

            return Bind()

    monkeypatch.setattr(target_plans, "current_diary_date", lambda: date(2026, 9, 18))
    assert target_plans._database_riyadh_date(Session()) == date(2026, 9, 18)
    assert calendar.database_calendar_date(Session()) == date(2026, 9, 20)
