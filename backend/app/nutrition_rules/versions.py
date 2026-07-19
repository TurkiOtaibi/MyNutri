from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RuleVersions:
    nutrition_registry_version: str = "2.0.0"
    calculation_engine_version: str = "2.0.0"
    food_group_rules_version: str = "1.0.0"
    source_reliability_rules_version: str = "1.0.0"
    nova_rules_version: str = "1.0.0"
    registry_schema_version: int = 2
    snapshot_schema_version: int = 3
    analysis_rules_version: None = None
    analysis_rules_status: str = "reserved_for_wave_3"

    def as_dict(self) -> dict[str, str | int | None]:
        return asdict(self)


VERSIONS = RuleVersions()
