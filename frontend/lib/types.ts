export type Sex = "male" | "female";
export type ActivityLevel = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type Goal = "cut" | "maintain" | "bulk";
export type NutritionBasis = "per_100g" | "per_100ml";
export type DefaultUnitType = "g" | "ml" | "cup" | "slice" | "piece" | "scoop" | "serving" | "tablespoon" | "teaspoon";
export type UnitBasis = "g" | "ml";

export interface TargetResponse {
  bmr: number;
  tdee: number;
  target_calories: number;
  calories: number;
  selected_cut_intensity: 0.15 | 0.2 | 0.25;
  requested_deficit_kcal: number;
  applied_deficit_kcal: number;
  deficit_cap_applied: boolean;
  final_target_calories: number;
  safety_outcome: "normal" | "specialist_review_required" | "very_low_energy_blocked";
  can_activate: boolean;
  protein_g: number;
  protein_calculation: {
    basis: "actual_weight" | "adjusted_weight";
    bmi_used: number;
    actual_weight_kg: number;
    reference_weight_kg: number | null;
    calculation_weight_kg: number;
    protein_per_kg: number;
    target_g: number;
    explanation_ar: string;
    reference_weight_label_ar: string;
    calculation_engine_version: string;
  };
  fat_g: number;
  carb_g: number;
  carb_clamped: boolean;
  calculation_warnings: CalculationWarning[];
  additional_targets?: AdditionalNutrientTarget[];
  calculation_engine_version: string;
  nutrition_registry_version: string;
}

export type NutrientTargetType = "minimum" | "maximum" | "adequate" | "recommended" | "range" | "monitor_only" | "minimize";

export interface AdditionalNutrientTarget {
  key: string;
  label_ar: string;
  unit: string;
  precision: number;
  order: number;
  target_type: NutrientTargetType;
  target_source: string;
  target_value: number | null;
  target_rule: Record<string, unknown>;
}

export interface CalculationWarning {
  code: "CARBOHYDRATE_BELOW_GENERAL_REFERENCE" | "CARBOHYDRATE_VERY_LOW";
  severity: "info" | "warning";
  dimension: "carbohydrate";
  value: number;
  reference_value: number;
  message_ar: string;
}

export interface ProfileInput {
  sex: Sex;
  birth_date: string;
  height_cm: number;
  weight_kg: number;
  activity_level: ActivityLevel;
  goal: Goal;
  protein_per_kg: number;
  fat_pct: number;
  selected_cut_intensity?: 0.15 | 0.2 | 0.25;
}

export interface NutritionRegistryResponse {
  registry_schema_version: 1;
  nutrition_registry_version: string;
  calculation_engine_version: string;
  food_group_rules_version: string;
  source_reliability_rules_version: string;
  nova_rules_version: string;
  snapshot_schema_version: 2;
  analysis_rules_version: null;
  analysis_rules_status: "reserved_for_wave_3";
  rules_manifest_hash: string;
  nutrients: Array<{
    key: string;
    storage_field: string;
    label_ar: string;
    unit: string;
    display_precision: number;
    display_order: number;
    target_type: NutrientTargetType;
    target_source: string;
    target_rule: Record<string, unknown>;
    completeness_participation: boolean;
    diary_coverage_participation: boolean;
  }>;
}

export interface ProfileResponse extends ProfileInput {
  id: string;
  updated_at: string;
  targets: TargetResponse;
}

export interface FoodInput {
  name: string;
  brand: string | null;
  category: string | null;
  nutrition_basis: NutritionBasis;
  default_unit_type: DefaultUnitType;
  unit_amount: number;
  unit_basis: UnitBasis;
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  fiber_g: number | null;
  sugar_g: number | null;
  added_sugar_g: number | null;
  saturated_fat_g: number | null;
  trans_fat_g: number | null;
  sodium_mg: number | null;
  cholesterol_mg: number | null;
  potassium_mg: number | null;
  calcium_mg: number | null;
  iron_mg: number | null;
  magnesium_mg: number | null;
  zinc_mg: number | null;
  vitamin_d_mcg: number | null;
  vitamin_b12_mcg: number | null;
  vitamin_c_mg: number | null;
  vitamin_a_mcg: number | null;
  folate_mcg: number | null;
  vitamin_k_mcg: number | null;
  notes: string | null;
  data_source: string | null;
}

export interface FoodResponse extends FoodInput {
  id: string;
  net_carbs_g: number;
  created_at: string;
  updated_at: string;
}

export type FoodSort = "name" | "recent" | "calories" | "protein";

export interface FoodListResponse {
  items: FoodResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  categories: string[];
  uncategorized_count: number;
}

export interface NutritionSnapshot extends Partial<FoodInput> {
  food_id: string | null;
  name: string;
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  log_mode?: string | null;
  logged_quantity?: number | null;
  calculated_totals?: Partial<NutritionTotals> | null;
  serving_label?: string | null;
  serving_grams?: number | null;
  total_sugars_g?: number | null;
}

export interface NutritionTotals {
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  saturated_fat_g: number | null;
  trans_fat_g: number | null;
  cholesterol_mg: number | null;
  sodium_mg: number | null;
  fiber_g: number | null;
  sugar_g: number | null;
  added_sugar_g: number | null;
  potassium_mg: number | null;
  calcium_mg: number | null;
  iron_mg: number | null;
  magnesium_mg: number | null;
  zinc_mg: number | null;
  vitamin_d_mcg: number | null;
  vitamin_b12_mcg: number | null;
  vitamin_c_mg: number | null;
  vitamin_a_mcg: number | null;
  folate_mcg: number | null;
  vitamin_k_mcg: number | null;
  total_sugars_g?: number | null;
  net_carbs_g: number;
}

export type MealType = "breakfast" | "lunch" | "dinner" | "snack" | "unspecified";

export interface DiaryEntryInput {
  id?: string;
  entry_date: string;
  food_id: string;
  quantity: number;
  meal_type: MealType;
}

export interface DiaryEntryResponse {
  id: string;
  entry_date: string;
  food_id: string;
  quantity: number;
  meal_type: MealType;
  nutrition_snapshot: NutritionSnapshot;
  totals: NutritionTotals;
  created_at: string;
}

export interface DaySummary {
  date: string;
  totals: NutritionTotals;
  targets: TargetResponse | null;
}

export interface WeekSummary {
  start: string;
  end: string;
  days: DaySummary[];
  weekly_totals: NutritionTotals;
  targets: TargetResponse | null;
}
