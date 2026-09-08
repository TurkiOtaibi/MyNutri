from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class RuleVersions:
    nutrition_registry_version: str = "4.0.0"
    calculation_engine_version: str = "2.0.0"
    registry_schema_version: int = 4

    def as_dict(self) -> dict[str, str | int | None]:
        return asdict(self)


VERSIONS = RuleVersions()
