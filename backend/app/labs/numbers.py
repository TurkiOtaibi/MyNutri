"""Exact medical arithmetic; decimal quantization is for display only."""

from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import re

from app.labs.types import ResolvedRule, TestDefinition


_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫", "01234567890123456789.")
_PLAIN = re.compile(r"[0-9]+(?:\.[0-9]+)?", re.ASCII)


def normalize_decimal_text(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("A plain decimal string is required")
    normalized = raw.strip().translate(_DIGITS)
    if _PLAIN.fullmatch(normalized) is None:
        raise ValueError("A nonnegative plain decimal is required")
    integer, dot, fractional = normalized.partition(".")
    normalized = (integer.lstrip("0") or "0") + dot + fractional
    if len(normalized) > 128:
        raise ValueError("The normalized decimal exceeds 128 characters")
    return normalized


def parse_entered_decimal(raw: str) -> Decimal:
    return Decimal(normalize_decimal_text(raw))


def _check_unit(test: TestDefinition, unit: str) -> None:
    if unit not in test.supported_units:
        raise ValueError("Unsupported unit")


def to_canonical(test: TestDefinition, entered: Decimal, unit: str) -> Fraction:
    _check_unit(test, unit)
    if not entered.is_finite() or entered < test.input_policy.entered_min_inclusive:
        raise ValueError("Entered value is outside the permitted domain")
    value = Fraction(entered)
    if unit != test.canonical_unit:
        conversion = test.conversion
        if conversion is None:
            raise ValueError("No approved conversion")
        value = value * Fraction(conversion.divide) / Fraction(conversion.multiply) - Fraction(
            conversion.pre_offset
        )
    if value < Fraction(test.input_policy.canonical_min_inclusive):
        raise ValueError("Canonical value is outside the permitted domain")
    return value


def from_canonical(test: TestDefinition, value: Fraction, unit: str) -> Fraction:
    _check_unit(test, unit)
    if value < Fraction(test.input_policy.canonical_min_inclusive):
        raise ValueError("Canonical value is outside the permitted domain")
    if unit != test.canonical_unit:
        conversion = test.conversion
        if conversion is None:
            raise ValueError("No approved conversion")
        value = (
            (value + Fraction(conversion.pre_offset))
            * Fraction(conversion.multiply)
            / Fraction(conversion.divide)
        )
    if value < Fraction(test.input_policy.entered_min_inclusive):
        raise ValueError("Converted value is outside the entered domain")
    return value


def _terminating_text(value: Fraction) -> str | None:
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    if denominator != 1:
        return None
    places = max(twos, fives)
    scaled = abs(value.numerator) * 2 ** (places - twos) * 5 ** (places - fives)
    digits = str(scaled).zfill(places + 1)
    sign = "-" if value < 0 else ""
    if not places:
        return sign + digits
    return sign + digits[:-places] + "." + digits[-places:]


def format_canonical(
    value: Fraction, rule: ResolvedRule, entered: Decimal, identity: bool
) -> tuple[str, bool]:
    if identity:
        return format(entered, "f"), False
    exact = _terminating_text(value)
    if exact is not None:
        return exact, False
    boundaries = {
        bound for zone in rule.zones for bound in (zone.low, zone.high) if bound is not None
    }
    # Preserve <, ==, > against every boundary, even when two sides share a Status.
    for precision in range(6, 161):
        with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
            rounded = Decimal(value.numerator) / Decimal(value.denominator)
        displayed = Fraction(rounded)
        if all(
            (value > bound) - (value < bound) == (displayed > bound) - (displayed < bound)
            for bound in boundaries
        ):
            return format(rounded, "f"), True
    raise ValueError("Cannot safely display the value within 160 significant digits")
