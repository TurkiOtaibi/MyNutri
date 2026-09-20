from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction
from typing import Literal, Mapping, TypeAlias


Sex: TypeAlias = Literal["male", "female"]
Tone: TypeAlias = Literal["within", "caution", "outside"]


@dataclass(frozen=True, slots=True)
class Zone:
    status: str
    low: Fraction | None
    high: Fraction | None
    low_inclusive: bool
    high_inclusive: bool


@dataclass(frozen=True, slots=True)
class ResolvedRule:
    test_key: str
    age_years: int
    zones: tuple[Zone, ...]


@dataclass(frozen=True, slots=True)
class Interpretation:
    canonical_exact: Fraction
    display_value: str
    display_unit: str
    display_is_approximate: bool
    status_code: str
    rule: ResolvedRule
    medical_rules_version: str


@dataclass(frozen=True, slots=True)
class ChartZoneSegment:
    from_date: date
    to_date_exclusive: date
    age_min: int
    zones: tuple[Zone, ...]


@dataclass(frozen=True, slots=True)
class RuleSlice:
    sex: Sex
    min_age: int
    max_age_exclusive: int | None
    zones: tuple[Zone, ...]


@dataclass(frozen=True, slots=True)
class StatusMetadata:
    code: str
    label_ar: str
    tone: Tone


@dataclass(frozen=True, slots=True)
class Category:
    key: str
    name_ar: str
    order: int


@dataclass(frozen=True, slots=True)
class Panel:
    key: str
    name_ar: str
    name_en: str
    test_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Conversion:
    from_unit: str
    to_unit: str
    formula: str
    pre_offset: Decimal
    multiply: Decimal
    divide: Decimal
    inverse: str


@dataclass(frozen=True, slots=True)
class InputPolicy:
    finite_decimal: bool
    entered_min_inclusive: Decimal
    canonical_min_inclusive: Decimal
    medical_max: Decimal | None
    max_plain_decimal_characters: int
    no_fixed_scale: bool


@dataclass(frozen=True, slots=True)
class Provenance:
    authority: str
    source_id: str
    rule_revision: str
    origin: str
    external_clinical_endorsement_claimed: bool


@dataclass(frozen=True, slots=True)
class ReferenceRule:
    kind: Literal["reference"]
    low: Decimal
    high: Decimal
    low_inclusive: bool
    high_inclusive: bool


@dataclass(frozen=True, slots=True)
class DecisionBand:
    status: str
    minimum: Decimal | None
    min_inclusive: bool
    maximum: Decimal | None
    max_inclusive: bool


@dataclass(frozen=True, slots=True)
class DecisionRule:
    kind: Literal["decision_bands"]
    bands: tuple[DecisionBand, ...]


@dataclass(frozen=True, slots=True)
class AgeBand:
    min_age: int
    max_age_exclusive: int | None
    rule: ReferenceRule


@dataclass(frozen=True, slots=True)
class AgeRule:
    kind: Literal["age_reference"]
    age_bands: tuple[AgeBand, ...]


RuleBranch: TypeAlias = ReferenceRule | DecisionRule | AgeRule


@dataclass(frozen=True, slots=True)
class SexRule:
    kind: Literal["sex_reference", "sex_decision", "sex_age_reference"]
    male: RuleBranch
    female: RuleBranch


RawRule: TypeAlias = RuleBranch | SexRule


@dataclass(frozen=True, slots=True)
class TestDefinition:
    key: str
    name_ar: str
    name_en: str
    abbreviation: str | None
    primary_category: str
    measurement: str
    specimen_context: str
    min_age: int
    max_age_exclusive: int | None
    sex_applicability: tuple[Sex, ...]
    pregnancy_rules: bool
    fasting_assumption: str
    canonical_unit: str
    default_input_unit: str
    supported_units: tuple[str, ...]
    conversion: Conversion | None
    input_policy: InputPolicy
    raw_rule: RawRule
    omit_unreachable_low: bool
    panels: tuple[str, ...]
    provenance: Provenance
    rule_slices: tuple[RuleSlice, ...] = ()


@dataclass(frozen=True, slots=True)
class Catalog:
    version: str
    content_sha256: str
    categories: tuple[Category, ...]
    panels: tuple[Panel, ...]
    tests: Mapping[str, TestDefinition]
    statuses: Mapping[str, StatusMetadata]
