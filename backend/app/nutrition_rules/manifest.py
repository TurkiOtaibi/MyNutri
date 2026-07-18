from __future__ import annotations

import hashlib
import json
from typing import Any

from app.nutrition_rules.policies import CALCULATION_POLICY
from app.nutrition_rules.registry import (
    BAKED_GOOD_TYPE_DEFINITIONS,
    FOOD_GROUPS,
    FOOD_GROUP_LABELS_AR,
    FOOD_GROUP_SUBTYPE_LABELS_AR,
    GRAIN_STARCH_TYPE_DEFINITIONS,
    GRAIN_TYPE_DEFINITIONS,
    INGREDIENT_SOURCE_LABELS_AR,
    INGREDIENT_SOURCE_TYPES,
    NOVA,
    NUTRIENTS,
    FOOD_CATEGORIES,
    FOOD_CATEGORY_LABELS_AR,
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
        "food_categories": list(FOOD_CATEGORIES),
        "food_category_definitions": [
            {"key": key, "label_ar": FOOD_CATEGORY_LABELS_AR[key]} for key in FOOD_CATEGORIES
        ],
        "grain_type_definitions": list(GRAIN_TYPE_DEFINITIONS),
        "baked_good_type_definitions": list(BAKED_GOOD_TYPE_DEFINITIONS),
        "grain_starch_type_definitions": list(GRAIN_STARCH_TYPE_DEFINITIONS),
        "food_groups": list(FOOD_GROUPS),
        "food_group_definitions": [
            {
                "key": item["key"],
                "label_ar": FOOD_GROUP_LABELS_AR[item["key"]],
                "subtype_labels_ar": FOOD_GROUP_SUBTYPE_LABELS_AR.get(item["key"], {}),
                **item,
            }
            for item in FOOD_GROUPS
        ],
        "traits": list(TRAITS),
        "source_types": list(SOURCE_RELIABILITY),
        "ingredient_source_types": list(INGREDIENT_SOURCE_TYPES),
        "ingredient_source_definitions": [
            {"type": key, "label_ar": INGREDIENT_SOURCE_LABELS_AR[key]}
            for key in INGREDIENT_SOURCE_TYPES
        ],
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
        "food_categories": manifest["food_categories"],
        "food_category_definitions": manifest["food_category_definitions"],
        "grain_type_definitions": manifest["grain_type_definitions"],
        "baked_good_type_definitions": manifest["baked_good_type_definitions"],
        "grain_starch_type_definitions": manifest["grain_starch_type_definitions"],
        "food_groups": manifest["food_groups"],
        "food_group_definitions": manifest["food_group_definitions"],
        "traits": manifest["traits"],
        "source_types": manifest["source_types"],
        "ingredient_source_types": manifest["ingredient_source_types"],
        "ingredient_source_definitions": manifest["ingredient_source_definitions"],
        "reliability_levels": manifest["reliability_levels"],
        "nova": manifest["nova"],
    }
