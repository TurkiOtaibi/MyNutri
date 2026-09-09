from __future__ import annotations

import hashlib
import json
from typing import Any

from app.nutrition_rules.policies import CALCULATION_POLICY
from app.nutrition_rules.registry import (
    FOOD_TAXONOMY,
    NUTRIENTS,
    NUTRITION_DATA_SOURCES,
    PRIMARY_CATEGORIES,
    TARGET_TYPES,
)
from app.nutrition_rules.versions import VERSIONS


def rules_manifest() -> dict[str, Any]:
    return {
        "versions": VERSIONS.as_dict(),
        "calculation_policy": CALCULATION_POLICY,
        "nutrients": [item.as_dict() for item in NUTRIENTS],
        "target_types": list(TARGET_TYPES),
        "primary_categories": list(PRIMARY_CATEGORIES),
        "food_taxonomy": [
            {
                "key": item["key"],
                "label_ar": item["label_ar"],
                "subcategories": [
                    {"key": key, "label_ar": label_ar}
                    for key, label_ar in item["subcategories"]
                ],
            }
            for item in FOOD_TAXONOMY
        ],
        "nutrition_data_sources": list(NUTRITION_DATA_SOURCES),
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
        "food_taxonomy": manifest["food_taxonomy"],
        "nutrition_data_sources": manifest["nutrition_data_sources"],
    }
