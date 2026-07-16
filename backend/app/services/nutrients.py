from app.nutrition_rules.registry import NUTRIENTS, NutrientDefinition

ADDITIONAL_NUTRIENTS = NUTRIENTS


def nutrient_target_payloads() -> list[dict[str, object]]:
    return [
        {
            "key": item.key,
            "label_ar": item.label_ar,
            "unit": item.unit,
            "precision": item.display_precision,
            "order": item.display_order,
            "target_type": item.target_type,
            "target_source": item.target_source,
            "target_value": item.target_rule.get("value"),
            "target_rule": item.target_rule,
        }
        for item in NUTRIENTS
    ]


__all__ = ["ADDITIONAL_NUTRIENTS", "NutrientDefinition", "nutrient_target_payloads"]
