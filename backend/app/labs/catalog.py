from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from functools import lru_cache
from importlib.resources import files
from types import MappingProxyType
from typing import Any, Callable, Mapping, cast

from app.labs.types import (
    AgeBand,
    AgeRule,
    Catalog,
    Category,
    Conversion,
    DecisionBand,
    DecisionRule,
    InputPolicy,
    Panel,
    Provenance,
    RawRule,
    ReferenceRule,
    RuleBranch,
    RuleSlice,
    Sex,
    SexRule,
    StatusMetadata,
    TestDefinition,
    Tone,
    Zone,
)


_PLAIN_DECIMAL = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_SEXES: tuple[Sex, Sex] = ("male", "female")


def _status(code: str, label_ar: str, tone: Tone) -> StatusMetadata:
    return StatusMetadata(code=code, label_ar=label_ar, tone=tone)


STATUS_METADATA: Mapping[str, StatusMetadata] = MappingProxyType(
    {
        item.code: item
        for item in (
            _status("low", "منخفض", "outside"),
            _status("in_range", "ضمن النطاق", "within"),
            _status("high", "مرتفع", "outside"),
            _status("normal", "طبيعي", "within"),
            _status("prediabetes_range", "نطاق ما قبل السكري", "caution"),
            _status("diabetes_range", "نطاق السكري", "outside"),
            _status("desirable", "مرغوب", "within"),
            _status("above_desirable", "أعلى من المرغوب", "caution"),
            _status("borderline_high", "مرتفع حدّيًا", "caution"),
            _status("very_high", "مرتفع جدًا", "outside"),
            _status("acceptable", "مقبول", "within"),
            _status("deficient", "نطاق النقص", "outside"),
            _status("inadequate", "غير كافٍ", "caution"),
            _status("adequate_for_most", "كافٍ لمعظم الأشخاص", "within"),
            _status("borderline", "حدّي", "caution"),
            _status("in_reference", "ضمن النطاق المرجعي", "within"),
        )
    }
)


def _expect_fields(raw: Mapping[str, Any], expected: set[str], context: str) -> None:
    actual = set(raw)
    if actual != expected:
        unknown = sorted(actual - expected)
        missing = sorted(expected - actual)
        raise ValueError(f"{context} unknown fields={unknown} missing fields={missing}")


def _expect_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return value


def _expect_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be an array")
    return value


def _expect_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a nonempty string")
    return value


def _expect_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{context} must be boolean")
    return value


def _expect_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{context} must be an integer")
    return value


def _decimal(value: Any, context: str) -> Decimal:
    if not isinstance(value, str) or _PLAIN_DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{context} must be a plain decimal string")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - regex already excludes invalid forms
        raise ValueError(f"{context} must be a plain decimal string") from exc
    if not result.is_finite():
        raise ValueError(f"{context} must be a finite plain decimal string")
    return result


def _optional_decimal(value: Any, context: str) -> Decimal | None:
    return None if value is None else _decimal(value, context)


def _string_tuple(value: Any, context: str) -> tuple[str, ...]:
    items = tuple(_expect_string(item, f"{context} member") for item in _expect_list(value, context))
    if len(items) != len(set(items)):
        raise ValueError(f"{context} contains repeated members")
    return items


def _parse_reference(raw: Mapping[str, Any], context: str) -> ReferenceRule:
    _expect_fields(
        raw,
        {"kind", "low", "high", "low_inclusive", "high_inclusive"},
        context,
    )
    if raw["kind"] != "reference":
        raise ValueError(f"{context} must be reference")
    low = _decimal(raw["low"], f"{context}.low")
    high = _decimal(raw["high"], f"{context}.high")
    if low < 0 or high <= low:
        raise ValueError(f"{context} has invalid reference bounds")
    return ReferenceRule(
        kind="reference",
        low=low,
        high=high,
        low_inclusive=_expect_bool(raw["low_inclusive"], f"{context}.low_inclusive"),
        high_inclusive=_expect_bool(raw["high_inclusive"], f"{context}.high_inclusive"),
    )


def _parse_decision(raw: Mapping[str, Any], context: str) -> DecisionRule:
    _expect_fields(raw, {"kind", "bands"}, context)
    if raw["kind"] != "decision_bands":
        raise ValueError(f"{context} must be decision_bands")
    parsed: list[DecisionBand] = []
    for index, value in enumerate(_expect_list(raw["bands"], f"{context}.bands")):
        band_raw = _expect_object(value, f"{context}.bands[{index}]")
        _expect_fields(
            band_raw,
            {"status", "min", "min_inclusive", "max", "max_inclusive"},
            f"{context}.bands[{index}]",
        )
        status = _expect_string(band_raw["status"], f"{context}.bands[{index}].status")
        if status not in STATUS_METADATA:
            raise ValueError(f"{context}.bands[{index}] has unknown status")
        minimum = _optional_decimal(band_raw["min"], f"{context}.bands[{index}].min")
        maximum = _optional_decimal(band_raw["max"], f"{context}.bands[{index}].max")
        if minimum is not None and minimum < 0:
            raise ValueError(f"{context}.bands[{index}] has a negative minimum")
        if minimum is not None and maximum is not None and maximum <= minimum:
            raise ValueError(f"{context}.bands[{index}] has invalid bounds")
        parsed.append(
            DecisionBand(
                status=status,
                minimum=minimum,
                min_inclusive=_expect_bool(
                    band_raw["min_inclusive"], f"{context}.bands[{index}].min_inclusive"
                ),
                maximum=maximum,
                max_inclusive=_expect_bool(
                    band_raw["max_inclusive"], f"{context}.bands[{index}].max_inclusive"
                ),
            )
        )
    if not parsed or parsed[0].minimum is not None or parsed[-1].maximum is not None:
        raise ValueError(f"{context} has incomplete decision zone coverage")
    for previous, following in zip(parsed, parsed[1:], strict=False):
        if previous.maximum != following.minimum:
            raise ValueError(f"{context} has gapped decision zones")
        if previous.max_inclusive == following.min_inclusive:
            raise ValueError(f"{context} has overlapping or gapped decision zone boundaries")
    return DecisionRule(kind="decision_bands", bands=tuple(parsed))


def _parse_age_rule(
    raw: Mapping[str, Any], context: str, minimum_age: int, maximum_age: int | None
) -> AgeRule:
    _expect_fields(raw, {"kind", "age_bands"}, context)
    if raw["kind"] != "age_reference":
        raise ValueError(f"{context} must be age_reference")
    parsed: list[AgeBand] = []
    for index, value in enumerate(_expect_list(raw["age_bands"], f"{context}.age_bands")):
        band_raw = _expect_object(value, f"{context}.age_bands[{index}]")
        _expect_fields(
            band_raw,
            {
                "min_age_inclusive",
                "max_age_exclusive",
                "kind",
                "low",
                "high",
                "low_inclusive",
                "high_inclusive",
            },
            f"{context}.age_bands[{index}]",
        )
        min_age = _expect_int(
            band_raw["min_age_inclusive"], f"{context}.age_bands[{index}].min_age_inclusive"
        )
        max_raw = band_raw["max_age_exclusive"]
        max_age = (
            None
            if max_raw is None
            else _expect_int(max_raw, f"{context}.age_bands[{index}].max_age_exclusive")
        )
        if min_age < minimum_age or (max_age is not None and max_age <= min_age):
            raise ValueError(f"{context} has invalid age coverage")
        reference_raw = {
            key: band_raw[key]
            for key in ("kind", "low", "high", "low_inclusive", "high_inclusive")
        }
        parsed.append(
            AgeBand(
                min_age=min_age,
                max_age_exclusive=max_age,
                rule=_parse_reference(reference_raw, f"{context}.age_bands[{index}].rule"),
            )
        )
    if not parsed or parsed[0].min_age != minimum_age or parsed[-1].max_age_exclusive != maximum_age:
        raise ValueError(f"{context} has invalid age coverage")
    for previous, following in zip(parsed, parsed[1:], strict=False):
        if previous.max_age_exclusive is None or previous.max_age_exclusive > following.min_age:
            raise ValueError(f"{context} has overlapping age bands")
        if previous.max_age_exclusive < following.min_age:
            raise ValueError(f"{context} has gapped age coverage")
    return AgeRule(kind="age_reference", age_bands=tuple(parsed))


def _parse_rule(raw_value: Any, context: str, minimum_age: int, maximum_age: int | None) -> RawRule:
    raw = _expect_object(raw_value, context)
    kind = raw.get("kind")
    if kind == "reference":
        return _parse_reference(raw, context)
    if kind == "decision_bands":
        return _parse_decision(raw, context)
    if kind == "age_reference":
        return _parse_age_rule(raw, context, minimum_age, maximum_age)

    child_parser: Callable[[Mapping[str, Any], str], RuleBranch]
    if kind == "sex_reference":
        expected_child_kind = "reference"
        child_parser = _parse_reference
    elif kind == "sex_decision":
        expected_child_kind = "decision_bands"
        child_parser = _parse_decision
    elif kind == "sex_age_reference":
        expected_child_kind = "age_reference"

        def child_parser(value: Mapping[str, Any], child_context: str) -> RuleBranch:
            return _parse_age_rule(value, child_context, minimum_age, maximum_age)

    else:
        raise ValueError(f"{context} has unsupported rule kind")
    _expect_fields(raw, {"kind", "male", "female"}, context)
    children: dict[Sex, RuleBranch] = {}
    for sex in _SEXES:
        child_raw = _expect_object(raw[sex], f"{context}.{sex}")
        if child_raw.get("kind") != expected_child_kind:
            raise ValueError(f"{context} has mixed inappropriate sex branches")
        children[sex] = child_parser(child_raw, f"{context}.{sex}")
    return SexRule(kind=kind, male=children["male"], female=children["female"])


def _reference_zones(rule: ReferenceRule, omit_unreachable_low: bool) -> tuple[Zone, ...]:
    low = Fraction(rule.low)
    high = Fraction(rule.high)
    zones: list[Zone] = []
    if not omit_unreachable_low:
        zones.append(
            Zone(
                status="low",
                low=None,
                high=low,
                low_inclusive=False,
                high_inclusive=not rule.low_inclusive,
            )
        )
    zones.extend(
        (
            Zone(
                status="in_range",
                low=low,
                high=high,
                low_inclusive=rule.low_inclusive,
                high_inclusive=rule.high_inclusive,
            ),
            Zone(
                status="high",
                low=high,
                high=None,
                low_inclusive=not rule.high_inclusive,
                high_inclusive=False,
            ),
        )
    )
    return tuple(zones)


def _branch_slices(
    branch: RuleBranch,
    sex: Sex,
    minimum_age: int,
    maximum_age: int | None,
    omit_unreachable_low: bool,
) -> tuple[RuleSlice, ...]:
    if isinstance(branch, ReferenceRule):
        return (
            RuleSlice(
                sex=sex,
                min_age=minimum_age,
                max_age_exclusive=maximum_age,
                zones=_reference_zones(branch, omit_unreachable_low),
            ),
        )
    if isinstance(branch, DecisionRule):
        return (
            RuleSlice(
                sex=sex,
                min_age=minimum_age,
                max_age_exclusive=maximum_age,
                zones=tuple(
                    Zone(
                        status=band.status,
                        low=None if band.minimum is None else Fraction(band.minimum),
                        high=None if band.maximum is None else Fraction(band.maximum),
                        low_inclusive=band.min_inclusive,
                        high_inclusive=band.max_inclusive,
                    )
                    for band in branch.bands
                ),
            ),
        )
    return tuple(
        RuleSlice(
            sex=sex,
            min_age=band.min_age,
            max_age_exclusive=band.max_age_exclusive,
            zones=_reference_zones(band.rule, omit_unreachable_low),
        )
        for band in branch.age_bands
    )


def compile_rule_slices(test: TestDefinition) -> tuple[RuleSlice, ...]:
    """Compile a validated raw test rule into exact immutable sex/age slices."""
    if isinstance(test.raw_rule, SexRule):
        branches = {"male": test.raw_rule.male, "female": test.raw_rule.female}
    else:
        branches = {sex: test.raw_rule for sex in _SEXES}
    return tuple(
        rule_slice
        for sex in _SEXES
        for rule_slice in _branch_slices(
            branches[sex],
            sex,
            test.min_age,
            test.max_age_exclusive,
            test.omit_unreachable_low,
        )
    )


def _parse_conversion(value: Any, supported_units: tuple[str, ...], canonical_unit: str) -> Conversion | None:
    if value is None:
        if len(supported_units) != 1:
            raise ValueError("multiple supported units require a conversion")
        return None
    raw = _expect_object(value, "alternate_unit_conversion")
    _expect_fields(raw, {"from", "to", "formula", "pre_offset", "multiply", "divide", "inverse"}, "alternate_unit_conversion")
    from_unit = _expect_string(raw["from"], "alternate_unit_conversion.from")
    to_unit = _expect_string(raw["to"], "alternate_unit_conversion.to")
    if from_unit != canonical_unit or to_unit not in supported_units or to_unit == from_unit:
        raise ValueError("conversion units do not match supported canonical and alternate units")
    divisor = _decimal(raw["divide"], "alternate_unit_conversion.divide")
    if divisor == 0:
        raise ValueError("zero conversion divisor")
    return Conversion(
        from_unit=from_unit,
        to_unit=to_unit,
        formula=_expect_string(raw["formula"], "alternate_unit_conversion.formula"),
        pre_offset=_decimal(raw["pre_offset"], "alternate_unit_conversion.pre_offset"),
        multiply=_decimal(raw["multiply"], "alternate_unit_conversion.multiply"),
        divide=divisor,
        inverse=_expect_string(raw["inverse"], "alternate_unit_conversion.inverse"),
    )


def _parse_input_policy(value: Any) -> InputPolicy:
    raw = _expect_object(value, "input_validation")
    _expect_fields(
        raw,
        {
            "finite_decimal",
            "entered_min_inclusive",
            "canonical_min_inclusive",
            "medical_max",
            "max_plain_decimal_characters",
            "no_fixed_scale",
        },
        "input_validation",
    )
    policy = InputPolicy(
        finite_decimal=_expect_bool(raw["finite_decimal"], "input_validation.finite_decimal"),
        entered_min_inclusive=_decimal(
            raw["entered_min_inclusive"], "input_validation.entered_min_inclusive"
        ),
        canonical_min_inclusive=_decimal(
            raw["canonical_min_inclusive"], "input_validation.canonical_min_inclusive"
        ),
        medical_max=_optional_decimal(raw["medical_max"], "input_validation.medical_max"),
        max_plain_decimal_characters=_expect_int(
            raw["max_plain_decimal_characters"], "input_validation.max_plain_decimal_characters"
        ),
        no_fixed_scale=_expect_bool(raw["no_fixed_scale"], "input_validation.no_fixed_scale"),
    )
    if policy != InputPolicy(True, Decimal(0), Decimal(0), None, 128, True):
        raise ValueError("input_validation does not match the approved input policy")
    return policy


def _parse_provenance(value: Any) -> Provenance:
    raw = _expect_object(value, "provenance")
    _expect_fields(
        raw,
        {"authority", "source_id", "rule_revision", "origin", "external_clinical_endorsement_claimed"},
        "provenance",
    )
    return Provenance(
        authority=_expect_string(raw["authority"], "provenance.authority"),
        source_id=_expect_string(raw["source_id"], "provenance.source_id"),
        rule_revision=_expect_string(raw["rule_revision"], "provenance.rule_revision"),
        origin=_expect_string(raw["origin"], "provenance.origin"),
        external_clinical_endorsement_claimed=_expect_bool(
            raw["external_clinical_endorsement_claimed"],
            "provenance.external_clinical_endorsement_claimed",
        ),
    )


def _parse_test(value: Any, index: int) -> TestDefinition:
    context = f"tests[{index}]"
    raw = _expect_object(value, context)
    _expect_fields(
        raw,
        {
            "test_key",
            "name_ar",
            "name_en",
            "abbreviation",
            "primary_category",
            "measurement",
            "specimen_context",
            "min_age_inclusive",
            "max_age_exclusive",
            "sex_applicability",
            "pregnancy_rules",
            "fasting_assumption",
            "canonical_unit",
            "default_input_unit",
            "supported_units",
            "alternate_unit_conversion",
            "input_validation",
            "rule",
            "omit_unreachable_low",
            "panels",
            "provenance",
        },
        context,
    )
    abbreviation = raw["abbreviation"]
    if abbreviation is not None:
        abbreviation = _expect_string(abbreviation, f"{context}.abbreviation")
    minimum_age = _expect_int(raw["min_age_inclusive"], f"{context}.min_age_inclusive")
    max_raw = raw["max_age_exclusive"]
    maximum_age = (
        None if max_raw is None else _expect_int(max_raw, f"{context}.max_age_exclusive")
    )
    if minimum_age != 18 or maximum_age is not None:
        raise ValueError(f"{context} has invalid age coverage")
    sex_values = _string_tuple(raw["sex_applicability"], f"{context}.sex_applicability")
    if sex_values != _SEXES:
        raise ValueError(f"{context} has mixed inappropriate sex branches")
    supported_units = _string_tuple(raw["supported_units"], f"{context}.supported_units")
    canonical_unit = _expect_string(raw["canonical_unit"], f"{context}.canonical_unit")
    default_unit = _expect_string(raw["default_input_unit"], f"{context}.default_input_unit")
    if default_unit not in supported_units:
        raise ValueError(f"{context} has unsupported default unit")
    if canonical_unit not in supported_units:
        raise ValueError(f"{context} has unsupported canonical unit")
    raw_rule = _parse_rule(raw["rule"], f"{context}.rule", minimum_age, maximum_age)
    omit_unreachable_low = _expect_bool(
        raw["omit_unreachable_low"], f"{context}.omit_unreachable_low"
    )
    if omit_unreachable_low:
        branches: tuple[RuleBranch, ...]
        if isinstance(raw_rule, SexRule):
            branches = (raw_rule.male, raw_rule.female)
        else:
            branches = (raw_rule,)
        reference_rules = tuple(
            band.rule
            for branch in branches
            for band in (branch.age_bands if isinstance(branch, AgeRule) else ())
        ) + tuple(branch for branch in branches if isinstance(branch, ReferenceRule))
        if not reference_rules or any(rule.low != 0 for rule in reference_rules):
            raise ValueError(f"{context} cannot omit a reachable low zone")
    test = TestDefinition(
        key=_expect_string(raw["test_key"], f"{context}.test_key"),
        name_ar=_expect_string(raw["name_ar"], f"{context}.name_ar"),
        name_en=_expect_string(raw["name_en"], f"{context}.name_en"),
        abbreviation=abbreviation,
        primary_category=_expect_string(raw["primary_category"], f"{context}.primary_category"),
        measurement=_expect_string(raw["measurement"], f"{context}.measurement"),
        specimen_context=_expect_string(raw["specimen_context"], f"{context}.specimen_context"),
        min_age=minimum_age,
        max_age_exclusive=maximum_age,
        sex_applicability=cast(tuple[Sex, ...], sex_values),
        pregnancy_rules=_expect_bool(raw["pregnancy_rules"], f"{context}.pregnancy_rules"),
        fasting_assumption=_expect_string(
            raw["fasting_assumption"], f"{context}.fasting_assumption"
        ),
        canonical_unit=canonical_unit,
        default_input_unit=default_unit,
        supported_units=supported_units,
        conversion=_parse_conversion(raw["alternate_unit_conversion"], supported_units, canonical_unit),
        input_policy=_parse_input_policy(raw["input_validation"]),
        raw_rule=raw_rule,
        omit_unreachable_low=omit_unreachable_low,
        panels=_string_tuple(raw["panels"], f"{context}.panels"),
        provenance=_parse_provenance(raw["provenance"]),
    )
    if test.pregnancy_rules or test.fasting_assumption not in {"fasting", "not_required"}:
        raise ValueError(f"{context} has unsupported interpretation context")
    return replace(test, rule_slices=compile_rule_slices(test))


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_catalog_bytes(raw_bytes: bytes) -> Catalog:
    try:
        decoded = json.loads(raw_bytes, object_pairs_hook=_reject_duplicate_json_keys)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("catalog must be valid UTF-8 JSON") from exc
    raw = _expect_object(decoded, "catalog")
    _expect_fields(raw, {"catalog_version", "categories", "panels", "tests"}, "catalog")

    categories: list[Category] = []
    category_keys: set[str] = set()
    for index, value in enumerate(_expect_list(raw["categories"], "categories")):
        item = _expect_object(value, f"categories[{index}]")
        _expect_fields(item, {"key", "name_ar", "order"}, f"categories[{index}]")
        key = _expect_string(item["key"], f"categories[{index}].key")
        if key in category_keys:
            raise ValueError(f"duplicate category key: {key}")
        category_keys.add(key)
        categories.append(
            Category(
                key=key,
                name_ar=_expect_string(item["name_ar"], f"categories[{index}].name_ar"),
                order=_expect_int(item["order"], f"categories[{index}].order"),
            )
        )

    panels: list[Panel] = []
    panel_keys: set[str] = set()
    for index, value in enumerate(_expect_list(raw["panels"], "panels")):
        item = _expect_object(value, f"panels[{index}]")
        _expect_fields(item, {"key", "name_ar", "name_en", "test_keys"}, f"panels[{index}]")
        key = _expect_string(item["key"], f"panels[{index}].key")
        if key in panel_keys:
            raise ValueError(f"duplicate panel key: {key}")
        panel_keys.add(key)
        members = tuple(
            _expect_string(member, f"panels[{index}].test_keys member")
            for member in _expect_list(item["test_keys"], f"panels[{index}].test_keys")
        )
        if len(members) != len(set(members)):
            raise ValueError(f"repeated panel member in {key}")
        panels.append(
            Panel(
                key=key,
                name_ar=_expect_string(item["name_ar"], f"panels[{index}].name_ar"),
                name_en=_expect_string(item["name_en"], f"panels[{index}].name_en"),
                test_keys=members,
            )
        )

    tests: dict[str, TestDefinition] = {}
    for index, value in enumerate(_expect_list(raw["tests"], "tests")):
        test = _parse_test(value, index)
        if test.key in tests:
            raise ValueError(f"duplicate test key: {test.key}")
        tests[test.key] = test

    for test in tests.values():
        if test.primary_category not in category_keys:
            raise ValueError(f"test {test.key} references an absent category")
        unknown_panels = set(test.panels) - panel_keys
        if unknown_panels:
            raise ValueError(f"test {test.key} references an orphan panel")
    for panel in panels:
        for member in panel.test_keys:
            if member not in tests:
                raise ValueError(f"orphan panel member {member}")
            if panel.key not in tests[member].panels:
                raise ValueError(f"panel membership mismatch for {member}")
    for test in tests.values():
        for panel_key in test.panels:
            panel = next(panel for panel in panels if panel.key == panel_key)
            if test.key not in panel.test_keys:
                raise ValueError(f"panel membership mismatch for {test.key}")

    return Catalog(
        version=_expect_string(raw["catalog_version"], "catalog_version"),
        content_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        categories=tuple(categories),
        panels=tuple(panels),
        tests=MappingProxyType(tests),
        statuses=STATUS_METADATA,
    )


def load_catalog() -> Catalog:
    """Load and strictly validate the packaged Medical Catalog V1 resource."""
    return _load_catalog_bytes(files("app.labs").joinpath("catalog.v1.json").read_bytes())


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    """Return the process-wide immutable compiled catalog."""
    return load_catalog()
