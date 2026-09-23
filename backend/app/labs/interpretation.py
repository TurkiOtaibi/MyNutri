"""Resolve current rules using age on the result date, before display rounding."""

from datetime import date, timedelta
from decimal import Decimal
from fractions import Fraction

from app.core.calendar import age_on
from app.labs.numbers import format_canonical, to_canonical
from app.labs.types import ChartZoneSegment, Interpretation, ResolvedRule, TestDefinition, Zone


def resolve_rule(test: TestDefinition, birth_date: date, sex: str, test_date: date) -> ResolvedRule:
    age = age_on(birth_date, test_date)
    for rule in test.rule_slices:
        if (
            rule.sex == sex
            and rule.min_age <= age
            and (rule.max_age_exclusive is None or age < rule.max_age_exclusive)
        ):
            return ResolvedRule(test.key, age, rule.zones)
    raise ValueError("No approved rule for this age and sex")


def _contains(zone: Zone, value: Fraction) -> bool:
    return (
        zone.low is None or value > zone.low or (zone.low_inclusive and value == zone.low)
    ) and (zone.high is None or value < zone.high or (zone.high_inclusive and value == zone.high))


def interpret(
    test: TestDefinition,
    entered: Decimal,
    unit: str,
    birth_date: date,
    sex: str,
    test_date: date,
    rules_version: str,
) -> Interpretation:
    rule = resolve_rule(test, birth_date, sex, test_date)
    value = to_canonical(test, entered, unit)
    status = next((zone.status for zone in rule.zones if _contains(zone, value)), None)
    if status is None:
        raise ValueError("Value is outside the approved rule zones")
    conversion = test.conversion
    identity = unit == test.canonical_unit or (
        conversion is not None
        and conversion.pre_offset == 0
        and conversion.multiply == conversion.divide
    )
    display, approximate = format_canonical(value, rule, entered, identity)
    return Interpretation(
        value, display, test.canonical_unit, approximate, status, rule, rules_version
    )


def _birthday(birth_date: date, age: int) -> date:
    year = birth_date.year + age
    try:
        return birth_date.replace(year=year)
    except ValueError:
        # Same March 1 anniversary as age_on for February 29 in non-leap years.
        return date(year, 3, 1)


def chart_zones(
    test: TestDefinition,
    birth_date: date,
    sex: str,
    first_date: date,
    last_date: date,
) -> tuple[ChartZoneSegment, ...]:
    if first_date > last_date:
        raise ValueError("The chart interval is inverted")
    resolve_rule(test, birth_date, sex, first_date)
    end = last_date + timedelta(days=1)
    transitions = {first_date, end}
    for rule in test.rule_slices:
        if rule.sex == sex and birth_date.year + rule.min_age <= date.max.year:
            birthday = _birthday(birth_date, rule.min_age)
            if first_date < birthday < end:
                transitions.add(birthday)
    points = sorted(transitions)
    segments = []
    for start, stop in zip(points, points[1:]):
        resolved = resolve_rule(test, birth_date, sex, start)
        segments.append(ChartZoneSegment(start, stop, resolved.age_years, resolved.zones))
    return tuple(segments)
