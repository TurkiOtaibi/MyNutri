from __future__ import annotations

import hashlib
import json
from typing import Any

from app.nutrition_rules.policies import CALCULATION_POLICY
from app.nutrition_rules.registry import (
    FOOD_GROUPS,
    INGREDIENT_SOURCE_TYPES,
    NOVA,
    NUTRIENTS,
    PRIMARY_CATEGORIES,
    RELIABILITY_LEVELS,
    SOURCE_RELIABILITY,
    TARGET_TYPES,
    TRAITS,
)
from app.nutrition_rules.versions import VERSIONS


def rules_manifest() -> dict[str, Any]:
    return {
        "versions": VERSIONS.as_dict(),
        "calculation_policy": CALCULATION_POLICY,
        "nutrients": [item.as_dict() for item in NUTRIENTS],
        "target_types": list(TARGET_TYPES),
        "primary_categories": list(PRIMARY_CATEGORIES),
        "food_groups": list(FOOD_GROUPS),
        "traits": list(TRAITS),
        "source_types": list(SOURCE_RELIABILITY),
        "ingredient_source_types": list(INGREDIENT_SOURCE_TYPES),
        "reliability_levels": list(RELIABILITY_LEVELS),
        "nova": NOVA,
    }


def canonical_manifest_bytes() -> bytes:
    return json.dumps(
        rules_manifest(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def rules_manifest_hash() -> str:
    return hashlib.sha256(canonical_manifest_bytes()).hexdigest()


def registry_response() -> dict[str, Any]:
    manifest = rules_manifest()
    return {
        **manifest["versions"],
        "rules_manifest_hash": rules_manifest_hash(),
        "calculation_policy": manifest["calculation_policy"],
        "nutrients": manifest["nutrients"],
        "target_types": manifest["target_types"],
        "primary_categories": manifest["primary_categories"],
        "food_groups": manifest["food_groups"],
        "traits": manifest["traits"],
        "source_types": manifest["source_types"],
        "ingredient_source_types": manifest["ingredient_source_types"],
        "reliability_levels": manifest["reliability_levels"],
        "nova": manifest["nova"],
    }
