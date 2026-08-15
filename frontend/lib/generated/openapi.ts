/* eslint-disable */
/* tslint:disable */
// @ts-nocheck
/*
 * ---------------------------------------------------------------
 * ## THIS FILE WAS GENERATED VIA SWAGGER-TYPESCRIPT-API        ##
 * ##                                                           ##
 * ## AUTHOR: acacode                                           ##
 * ## SOURCE: https://github.com/acacode/swagger-typescript-api ##
 * ---------------------------------------------------------------
 */

/** AccountResponse */
export interface AccountResponse {
  /**
   * Auth User Id
   * @format uuid
   */
  auth_user_id: string;
  /** Display Name */
  display_name: string | null;
  /** Email */
  email: string | null;
  /**
   * Principal Id
   * @format uuid
   */
  principal_id: string;
  role: PrincipalRole;
  status: PrincipalStatus;
}

/** ActivityLevel */
export type ActivityLevel =
  | "sedentary"
  | "light"
  | "moderate"
  | "active"
  | "very_active";

/** AdditionalNutrientTarget */
export interface AdditionalNutrientTarget {
  /** Key */
  key: string;
  /** Label Ar */
  label_ar: string;
  /** Order */
  order: number;
  /** Precision */
  precision: number;
  /** Target Rule */
  target_rule?: Record<string, any>;
  /** Target Source */
  target_source: string;
  /** Target Type */
  target_type:
    | "minimum"
    | "maximum"
    | "adequate"
    | "recommended"
    | "range"
    | "monitor_only"
    | "minimize";
  /** Target Value */
  target_value?: number | null;
  /** Unit */
  unit: string;
}

/** AdminDiaryItem */
export interface AdminDiaryItem {
  /**
   * Entry Date
   * @format date
   */
  entry_date: string;
  /** Food Name */
  food_name: string;
  /**
   * Id
   * @format uuid
   */
  id: string;
  meal_type: MealType;
  /** Quantity */
  quantity: number;
}

/** AdminDiaryPage */
export interface AdminDiaryPage {
  /** Items */
  items: AdminDiaryItem[];
  /** Next Cursor */
  next_cursor: string | null;
}

/** AdminUserDetail */
export interface AdminUserDetail {
  account: AdminUserSummary;
  current_target: TargetSourceResponse | null;
  pending_plan: TargetPlanSummary | null;
  plan_history: TargetPlanHistoryResponse;
  profile: ProfileResponse | null;
}

/** AdminUserListResponse */
export interface AdminUserListResponse {
  /** Items */
  items: AdminUserSummary[];
  /** Page */
  page: number;
  /** Page Size */
  page_size: number;
  /** Total */
  total: number;
  /** Total Pages */
  total_pages: number;
}

/** AdminUserSummary */
export interface AdminUserSummary {
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  current_goal: Goal | null;
  /** Display Name */
  display_name: string | null;
  /** Email */
  email: string | null;
  /** Last Activity At */
  last_activity_at: string | null;
  /**
   * Principal Id
   * @format uuid
   */
  principal_id: string;
  /** Profile Complete */
  profile_complete: boolean;
  role: PrincipalRole;
  status: PrincipalStatus;
}

/** BakedGoodType */
export type BakedGoodType =
  | "arabic_bread"
  | "toast"
  | "rolls_wraps"
  | "burger_bun"
  | "flatbread"
  | "pastries"
  | "cake"
  | "biscuits_cookies"
  | "other";

/** CalculationWarningResponse */
export interface CalculationWarningResponse {
  /** Code */
  code: "CARBOHYDRATE_BELOW_GENERAL_REFERENCE" | "CARBOHYDRATE_VERY_LOW";
  /** Dimension */
  dimension: "carbohydrate";
  /** Message Ar */
  message_ar: string;
  /** Reference Value */
  reference_value: number;
  /** Severity */
  severity: "info" | "warning";
  /** Value */
  value: number;
}

/** CalendarAuthorityResponse */
export interface CalendarAuthorityResponse {
  /** Calendar Timezone */
  calendar_timezone: string;
  /**
   * Current Diary Date
   * @format date
   */
  current_diary_date: string;
  /**
   * Next Rollover At
   * @format date-time
   */
  next_rollover_at: string;
}

/** ContributionDataStatus */
export type ContributionDataStatus = "known" | "estimated";

/** DaySummary */
export interface DaySummary {
  /**
   * Date
   * @format date
   */
  date: string;
  /** Nutrient Aggregates */
  nutrient_aggregates: DiaryNutrientAggregate[];
  /** Overall Nutrient Coverage Percent */
  overall_nutrient_coverage_percent: number | null;
  /** Target Provenance */
  target_provenance:
    | "versioned_plan"
    | "legacy_unversioned"
    | "no_target_source";
  targets?: TargetResponse | null;
  totals: NutritionTotals;
}

/** DefaultUnitType */
export type DefaultUnitType =
  | "g"
  | "ml"
  | "cup"
  | "slice"
  | "piece"
  | "scoop"
  | "serving"
  | "tablespoon"
  | "teaspoon";

/** DiaryEntryResponse */
export interface DiaryEntryResponse {
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /**
   * Entry Date
   * @format date
   */
  entry_date: string;
  /** Food Id */
  food_id: string | null;
  /**
   * Id
   * @format uuid
   */
  id: string;
  meal_type: MealType;
  nutrition_snapshot: NutritionSnapshot;
  /** Quantity */
  quantity: number;
  /** Snapshot Schema Version */
  snapshot_schema_version: number | null;
  /** Target Plan Id */
  target_plan_id: string | null;
  /** Target Provenance */
  target_provenance:
    | "versioned_plan"
    | "legacy_unversioned"
    | "no_target_source";
  totals: NutritionTotals;
}

/** DiaryNutrientAggregate */
export interface DiaryNutrientAggregate {
  /** Amount */
  amount: number | null;
  /** Amount Qualifier */
  amount_qualifier: "unavailable" | "at_least" | "exact";
  /** Available */
  available?: number | null;
  /** Coverage Percent */
  coverage_percent: number | null;
  /** Coverage State */
  coverage_state: "no_entries" | "all_unknown" | "partial" | "complete";
  /** Evaluation */
  evaluation?: string | null;
  /** Key */
  key: string;
  /** Known Entry Count */
  known_entry_count: number;
  /** Progress Percent */
  progress_percent?: number | null;
  /** Remaining */
  remaining?: number | null;
  target?: DiaryNutrientTarget | null;
  /** Total Entry Count */
  total_entry_count: number;
}

/** DiaryNutrientTarget */
export interface DiaryNutrientTarget {
  /** Lower */
  lower?: number | null;
  /** Source */
  source: "versioned_plan" | "legacy_unversioned";
  /** Type */
  type:
    | "minimum"
    | "maximum"
    | "adequate"
    | "recommended"
    | "range"
    | "monitor_only"
    | "minimize";
  /** Unit */
  unit: string;
  /** Upper */
  upper?: number | null;
  /** Value */
  value?: number | null;
}

/** FoodDeleteResponse */
export interface FoodDeleteResponse {
  /** Disposition */
  disposition: "deleted" | "archived";
}

/** FoodGroupContributionInput */
export interface FoodGroupContributionInput {
  /**
   * Amount Per 100 Basis
   * @exclusiveMin 0
   * @max 100
   */
  amount_per_100_basis: number;
  data_status: ContributionDataStatus;
  /** Group Key */
  group_key: string;
  /** Subtype Key */
  subtype_key?: string | null;
}

/** FoodGroupContributionResponse */
export interface FoodGroupContributionResponse {
  /**
   * Amount Per 100 Basis
   * @exclusiveMin 0
   * @max 100
   */
  amount_per_100_basis: number;
  data_status: ContributionDataStatus;
  /** Food Group Rules Version */
  food_group_rules_version: string;
  /** Group Key */
  group_key: string;
  /** Subtype Key */
  subtype_key?: string | null;
}

/** FoodKind */
export type FoodKind = "simple" | "composite" | "unknown";

/** FoodListResponse */
export interface FoodListResponse {
  /** Categories */
  categories: string[];
  /** Items */
  items: FoodResponse[];
  /** Page */
  page: number;
  /** Page Size */
  page_size: number;
  /** Total */
  total: number;
  /** Total Pages */
  total_pages: number;
  /** Uncategorized Count */
  uncategorized_count: number;
}

/** FoodPickerItem */
export interface FoodPickerItem {
  /** Brand */
  brand: string | null;
  /** Calories */
  calories: number;
  /** Carb G */
  carb_g: number;
  default_unit_type: DefaultUnitType;
  /** Fat G */
  fat_g: number;
  /**
   * Id
   * @format uuid
   */
  id: string;
  /** Name */
  name: string;
  nutrition_basis: NutritionBasis;
  /** Protein G */
  protein_g: number;
  /** Unit Amount */
  unit_amount: number;
  unit_basis: UnitBasis;
}

/** FoodPickerResponse */
export interface FoodPickerResponse {
  /** Items */
  items: FoodPickerItem[];
  /** Next Cursor */
  next_cursor: string | null;
  /** Recent Items */
  recent_items: FoodPickerItem[];
}

/** FoodResponse */
export interface FoodResponse {
  /** Vitamin B12 Mcg */
  vitamin_b12_mcg?: number | null;
  /** Added Sugar G */
  added_sugar_g?: number | null;
  /** Analytical Traits */
  analytical_traits: string[];
  /** Archived At */
  archived_at: string | null;
  baked_good_type?: BakedGoodType | null;
  /** Brand */
  brand?: string | null;
  /** Calcium Mg */
  calcium_mg?: number | null;
  /**
   * Calories
   * @min 0
   * @max 3000
   */
  calories: number;
  /**
   * Carb G
   * @min 0
   * @max 500
   */
  carb_g: number;
  /** Cholesterol Mg */
  cholesterol_mg?: number | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /** Data Source */
  data_source?: string | null;
  default_unit_type: DefaultUnitType;
  /**
   * Fat G
   * @min 0
   * @max 300
   */
  fat_g: number;
  /** Fiber G */
  fiber_g?: number | null;
  /** Folate Dfe Mcg */
  folate_dfe_mcg?: number | null;
  /** Folate Mcg */
  folate_mcg?: number | null;
  /** Food Category Key */
  food_category_key: string;
  /** @default "unknown" */
  food_kind?: FoodKind;
  grain_starch_type?: GrainStarchType | null;
  grain_type?: GrainType | null;
  /** Group Contributions */
  group_contributions: FoodGroupContributionResponse[];
  group_data_completeness: GroupDataCompleteness;
  group_data_status: GroupDataStatus;
  /**
   * Id
   * @format uuid
   */
  id: string;
  ingredients?: IngredientsInput;
  /** Iodine Mcg */
  iodine_mcg?: number | null;
  /** Iron Mg */
  iron_mg?: number | null;
  legacy_nutrition: LegacyNutritionResponse;
  /** Magnesium Mg */
  magnesium_mg?: number | null;
  /** Name */
  name: string;
  /** Net Carbs G */
  net_carbs_g: number;
  /** Notes */
  notes?: string | null;
  nova: NovaResponse;
  nutrition_basis: NutritionBasis;
  nutrition_source: NutritionSourceResponse;
  /** Potassium Mg */
  potassium_mg?: number | null;
  /**
   * Protein G
   * @min 0
   * @max 300
   */
  protein_g: number;
  /** Saturated Fat G */
  saturated_fat_g?: number | null;
  /** Selenium Mcg */
  selenium_mcg?: number | null;
  /** Sodium Mg */
  sodium_mg?: number | null;
  status: FoodStatus;
  /** Sugar G */
  sugar_g?: number | null;
  /** Taxonomy Review Required */
  taxonomy_review_required: boolean;
  /** Trans Fat G */
  trans_fat_g?: number | null;
  /**
   * Unit Amount
   * @exclusiveMin 0
   * @max 2000
   */
  unit_amount: number;
  unit_basis: UnitBasis;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /** Vitamin A Mcg */
  vitamin_a_mcg?: number | null;
  /** Vitamin A Rae Mcg */
  vitamin_a_rae_mcg?: number | null;
  /** Vitamin C Mg */
  vitamin_c_mg?: number | null;
  /** Vitamin D Mcg */
  vitamin_d_mcg?: number | null;
  /** Vitamin K Mcg */
  vitamin_k_mcg?: number | null;
  /** Zinc Mg */
  zinc_mg?: number | null;
}

/** FoodStatus */
export type FoodStatus = "active" | "archived";

/** Goal */
export type Goal = "cut" | "maintain" | "bulk";

/** GrainStarchType */
export type GrainStarchType =
  | "rice"
  | "pasta"
  | "oats"
  | "breakfast_cereal"
  | "bulgur"
  | "quinoa"
  | "flour"
  | "other";

/** GrainType */
export type GrainType =
  | "whole"
  | "refined"
  | "mixed"
  | "grain_free"
  | "unknown";

/** GroupDataCompleteness */
export type GroupDataCompleteness = "complete" | "partial" | "unknown";

/** GroupDataStatus */
export type GroupDataStatus = "known" | "estimated" | "unknown";

/** HTTPValidationError */
export interface HTTPValidationError {
  /** Detail */
  detail?: ValidationError[];
}

/** IngredientsInput */
export interface IngredientsInput {
  /** Source Name */
  source_name?: string | null;
  /** Source Reference */
  source_reference?: string | null;
  source_type?: IngredientsSourceType | null;
  /** Text */
  text?: string | null;
}

/** IngredientsSourceType */
export type IngredientsSourceType =
  | "official_product_label"
  | "manufacturer_website"
  | "official_food_database"
  | "official_restaurant"
  | "calculated_recipe"
  | "manual_entry"
  | "multiple_sources"
  | "unknown";

/** LegacyNutritionResponse */
export interface LegacyNutritionResponse {
  /** Folate Mcg */
  folate_mcg: number | null;
  /**
   * Meaning Ar
   * @default "قيمة قديمة غير محددة المعيار"
   */
  meaning_ar?: string;
  /** Vitamin A Mcg */
  vitamin_a_mcg: number | null;
}

/** MealType */
export type MealType =
  | "breakfast"
  | "lunch"
  | "dinner"
  | "snack"
  | "unspecified";

/** NovaClassification */
export type NovaClassification = "1" | "2" | "3" | "4" | "unknown";

/** NovaInput */
export interface NovaInput {
  classification: NovaClassification;
}

/** NovaResponse */
export interface NovaResponse {
  classification: NovaClassification;
  review_status: NovaReviewStatus;
  /** Rules Version */
  rules_version: string;
}

/** NovaReviewStatus */
export type NovaReviewStatus = "unreviewed" | "reviewed";

/** NutritionBasis */
export type NutritionBasis = "per_100g" | "per_100ml";

/** NutritionRegistryResponse */
export interface NutritionRegistryResponse {
  /** Analysis Rules Status */
  analysis_rules_status: "reserved_for_wave_3";
  /** Analysis Rules Version */
  analysis_rules_version: null;
  /** Baked Good Type Definitions */
  baked_good_type_definitions: RegistryLabelDefinition[];
  /** Calculation Engine Version */
  calculation_engine_version: string;
  /** Calculation Policy */
  calculation_policy: Record<string, any>;
  /** Food Categories */
  food_categories: string[];
  /** Food Category Definitions */
  food_category_definitions: RegistryLabelDefinition[];
  /** Food Group Definitions */
  food_group_definitions: RegistryFoodGroupDefinition[];
  /** Food Group Rules Version */
  food_group_rules_version: string;
  /** Food Groups */
  food_groups: Record<string, any>[];
  /** Grain Starch Type Definitions */
  grain_starch_type_definitions: RegistryLabelDefinition[];
  /** Grain Type Definitions */
  grain_type_definitions: RegistryLabelDefinition[];
  /** Ingredient Source Definitions */
  ingredient_source_definitions: RegistryIngredientSourceDefinition[];
  /** Ingredient Source Types */
  ingredient_source_types: IngredientsSourceType[];
  nova: RegistryNovaDefinition;
  /** Nova Rules Version */
  nova_rules_version: string;
  /** Nutrients */
  nutrients: RegistryNutrientDefinition[];
  /** Nutrition Registry Version */
  nutrition_registry_version: string;
  /** Registry Schema Version */
  registry_schema_version: 2;
  /** Reliability Levels */
  reliability_levels: RegistryLabelDefinition[];
  /** Rules Manifest Hash */
  rules_manifest_hash: string;
  /** Snapshot Schema Version */
  snapshot_schema_version: 3;
  /** Source Reliability Rules Version */
  source_reliability_rules_version: string;
  /** Source Types */
  source_types: RegistrySourceTypeDefinition[];
  /** Target Types */
  target_types: string[];
  /** Traits */
  traits: RegistryLabelDefinition[];
}

/** NutritionSnapshot */
export interface NutritionSnapshot {
  /** Vitamin B12 Mcg */
  vitamin_b12_mcg?: number | null;
  /** Added Sugar G */
  added_sugar_g?: number | null;
  /** Brand */
  brand?: string | null;
  /** Calcium Mg */
  calcium_mg?: number | null;
  /** Calculated Totals */
  calculated_totals?: Record<string, any> | null;
  /** Calories */
  calories: number;
  /** Carb G */
  carb_g: number;
  /** Category */
  category?: string | null;
  /** Cholesterol Mg */
  cholesterol_mg?: number | null;
  /** Data Source */
  data_source?: string | null;
  default_unit_type?: DefaultUnitType | null;
  /** Fat G */
  fat_g: number;
  /** Fiber G */
  fiber_g?: number | null;
  /** Folate Dfe Mcg */
  folate_dfe_mcg?: number | null;
  /** Folate Mcg */
  folate_mcg?: number | null;
  /** Food Id */
  food_id?: string | null;
  /** Iodine Mcg */
  iodine_mcg?: number | null;
  /** Iron Mg */
  iron_mg?: number | null;
  /** Log Mode */
  log_mode?: string | null;
  /** Logged Quantity */
  logged_quantity?: number | null;
  /** Magnesium Mg */
  magnesium_mg?: number | null;
  /** Name */
  name: string;
  /** Notes */
  notes?: string | null;
  nutrition_basis?: NutritionBasis | null;
  /** Potassium Mg */
  potassium_mg?: number | null;
  /** Protein G */
  protein_g: number;
  /** Saturated Fat G */
  saturated_fat_g?: number | null;
  /** Selenium Mcg */
  selenium_mcg?: number | null;
  /** Serving Grams */
  serving_grams?: number | null;
  /** Serving Label */
  serving_label?: string | null;
  /** Sodium Mg */
  sodium_mg?: number | null;
  /** Sugar G */
  sugar_g?: number | null;
  /** Total Sugars G */
  total_sugars_g?: number | null;
  /** Trans Fat G */
  trans_fat_g?: number | null;
  /** Unit Amount */
  unit_amount?: number | null;
  unit_basis?: UnitBasis | null;
  /** Vitamin A Mcg */
  vitamin_a_mcg?: number | null;
  /** Vitamin A Rae Mcg */
  vitamin_a_rae_mcg?: number | null;
  /** Vitamin C Mg */
  vitamin_c_mg?: number | null;
  /** Vitamin D Mcg */
  vitamin_d_mcg?: number | null;
  /** Vitamin K Mcg */
  vitamin_k_mcg?: number | null;
  /** Zinc Mg */
  zinc_mg?: number | null;
}

/** NutritionSourceInput */
export interface NutritionSourceInput {
  /** Name */
  name?: string | null;
  /** Reference */
  reference?: string | null;
  /** @default "unknown" */
  type?: NutritionSourceType;
}

/** NutritionSourceResponse */
export interface NutritionSourceResponse {
  /** Name */
  name?: string | null;
  /** Reference */
  reference?: string | null;
  /** Reliability */
  reliability: "high" | "medium" | "low" | "mixed" | "unknown";
  /** Reliability Rules Version */
  reliability_rules_version: string;
  /** @default "unknown" */
  type?: NutritionSourceType;
}

/** NutritionSourceType */
export type NutritionSourceType =
  | "laboratory_analysis"
  | "official_food_database"
  | "official_product_label"
  | "manufacturer_website"
  | "official_restaurant"
  | "calculated_recipe"
  | "manual_estimate"
  | "multiple_sources"
  | "unknown";

/** NutritionTotals */
export interface NutritionTotals {
  /** Vitamin B12 Mcg */
  vitamin_b12_mcg?: number | null;
  /** Added Sugar G */
  added_sugar_g?: number | null;
  /** Calcium Mg */
  calcium_mg?: number | null;
  /**
   * Calories
   * @default 0
   */
  calories?: number;
  /**
   * Carb G
   * @default 0
   */
  carb_g?: number;
  /** Cholesterol Mg */
  cholesterol_mg?: number | null;
  /**
   * Fat G
   * @default 0
   */
  fat_g?: number;
  /** Fiber G */
  fiber_g?: number | null;
  /** Folate Dfe Mcg */
  folate_dfe_mcg?: number | null;
  /** Folate Mcg */
  folate_mcg?: number | null;
  /** Iodine Mcg */
  iodine_mcg?: number | null;
  /** Iron Mg */
  iron_mg?: number | null;
  /** Magnesium Mg */
  magnesium_mg?: number | null;
  /**
   * Net Carbs G
   * @default 0
   */
  net_carbs_g?: number;
  /** Potassium Mg */
  potassium_mg?: number | null;
  /**
   * Protein G
   * @default 0
   */
  protein_g?: number;
  /** Saturated Fat G */
  saturated_fat_g?: number | null;
  /** Selenium Mcg */
  selenium_mcg?: number | null;
  /** Sodium Mg */
  sodium_mg?: number | null;
  /** Sugar G */
  sugar_g?: number | null;
  /** Total Sugars G */
  total_sugars_g?: number | null;
  /** Trans Fat G */
  trans_fat_g?: number | null;
  /** Vitamin A Mcg */
  vitamin_a_mcg?: number | null;
  /** Vitamin A Rae Mcg */
  vitamin_a_rae_mcg?: number | null;
  /** Vitamin C Mg */
  vitamin_c_mg?: number | null;
  /** Vitamin D Mcg */
  vitamin_d_mcg?: number | null;
  /** Vitamin K Mcg */
  vitamin_k_mcg?: number | null;
  /** Zinc Mg */
  zinc_mg?: number | null;
}

/** PrincipalRole */
export type PrincipalRole = "user" | "admin";

/** PrincipalStatus */
export type PrincipalStatus = "active" | "disabled";

/** ProfilePreview */
export interface ProfilePreview {
  activity_level: ActivityLevel;
  /**
   * Birth Date
   * @format date
   */
  birth_date: string;
  /**
   * Fat Pct
   * @min 0.15
   * @max 0.4
   * @default 0.25
   */
  fat_pct?: number;
  goal: Goal;
  /**
   * Height Cm
   * @min 100
   * @max 250
   */
  height_cm: number;
  /**
   * Protein Per Kg
   * @min 1
   * @max 3
   * @default 1.2
   */
  protein_per_kg?: number;
  /**
   * Selected Cut Intensity
   * @default 0.2
   */
  selected_cut_intensity?: 0.15 | 0.2 | 0.25;
  sex: Sex;
  /**
   * Weight Kg
   * @min 20
   * @max 300
   */
  weight_kg: number;
}

/** ProfileResponse */
export interface ProfileResponse {
  activity_level: ActivityLevel;
  /**
   * Birth Date
   * @format date
   */
  birth_date: string;
  effective_plan?: TargetPlanSummary | null;
  /**
   * Fat Pct
   * @min 0.15
   * @max 0.4
   * @default 0.25
   */
  fat_pct?: number;
  goal: Goal;
  /**
   * Height Cm
   * @min 100
   * @max 250
   */
  height_cm: number;
  /**
   * Id
   * @format uuid
   */
  id: string;
  pending_plan?: TargetPlanSummary | null;
  /**
   * Protein Per Kg
   * @min 1
   * @max 3
   * @default 1.2
   */
  protein_per_kg?: number;
  /**
   * Selected Cut Intensity
   * @default 0.2
   */
  selected_cut_intensity?: 0.15 | 0.2 | 0.25;
  sex: Sex;
  /**
   * Target Provenance
   * @default "legacy_unversioned"
   */
  target_provenance?: "versioned_plan" | "legacy_unversioned";
  targets: TargetResponse;
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /**
   * Weight Kg
   * @min 20
   * @max 300
   */
  weight_kg: number;
}

/** ProfileUpsert */
export interface ProfileUpsert {
  activity_level: ActivityLevel;
  /**
   * Birth Date
   * @format date
   */
  birth_date: string;
  /**
   * Fat Pct
   * @min 0.15
   * @max 0.4
   * @default 0.25
   */
  fat_pct?: number;
  goal: Goal;
  /**
   * Height Cm
   * @min 100
   * @max 250
   */
  height_cm: number;
  /**
   * Protein Per Kg
   * @min 1
   * @max 3
   * @default 1.2
   */
  protein_per_kg?: number;
  /**
   * Selected Cut Intensity
   * @default 0.2
   */
  selected_cut_intensity?: 0.15 | 0.2 | 0.25;
  sex: Sex;
  /**
   * Weight Kg
   * @min 20
   * @max 300
   */
  weight_kg: number;
}

/** ProteinCalculationResponse */
export interface ProteinCalculationResponse {
  /** Actual Weight Kg */
  actual_weight_kg: number;
  /** Basis */
  basis: "actual_weight" | "adjusted_weight";
  /** Bmi Used */
  bmi_used: number;
  /** Calculation Engine Version */
  calculation_engine_version: string;
  /** Calculation Weight Kg */
  calculation_weight_kg: number;
  /** Explanation Ar */
  explanation_ar: string;
  /** Protein Per Kg */
  protein_per_kg: number;
  /** Reference Weight Kg */
  reference_weight_kg: number | null;
  /** Reference Weight Label Ar */
  reference_weight_label_ar: string;
  /** Target G */
  target_g: number;
}

/** RegistryFoodGroupDefinition */
export interface RegistryFoodGroupDefinition {
  /** Key */
  key: string;
  /** Label Ar */
  label_ar: string;
  /** Subtype Labels Ar */
  subtype_labels_ar: Record<string, string>;
  /** Subtypes */
  subtypes?: Record<string, any> | string[] | null;
  [key: string]: any;
}

/** RegistryIngredientSourceDefinition */
export interface RegistryIngredientSourceDefinition {
  /** Label Ar */
  label_ar: string;
  type: IngredientsSourceType;
}

/** RegistryLabelDefinition */
export interface RegistryLabelDefinition {
  /** Key */
  key: string;
  /** Label Ar */
  label_ar: string;
}

/** RegistryNovaDefinition */
export interface RegistryNovaDefinition {
  /** Automated Suggestions */
  automated_suggestions: false;
  /** Classifications */
  classifications: (number | "unknown")[];
  /** Labels Ar */
  labels_ar: Record<string, string>;
  /** Review Statuses */
  review_statuses: ("unreviewed" | "reviewed")[];
}

/** RegistryNutrientDefinition */
export interface RegistryNutrientDefinition {
  /** Completeness Participation */
  completeness_participation: boolean;
  /** Diary Coverage Participation */
  diary_coverage_participation: boolean;
  /** Display Order */
  display_order: number;
  /** Display Precision */
  display_precision: number;
  /** Key */
  key: string;
  /** Label Ar */
  label_ar: string;
  /** Storage Field */
  storage_field: string;
  /** Target Rule */
  target_rule: Record<string, any>;
  /** Target Source */
  target_source: string;
  /** Target Type */
  target_type:
    | "minimum"
    | "maximum"
    | "adequate"
    | "recommended"
    | "range"
    | "monitor_only"
    | "minimize";
  /** Unit */
  unit: string;
}

/** RegistrySourceTypeDefinition */
export interface RegistrySourceTypeDefinition {
  /** Label Ar */
  label_ar: string;
  /** Reliability */
  reliability: "high" | "medium" | "low" | "mixed" | "unknown";
  type: NutritionSourceType;
}

/** Sex */
export type Sex = "male" | "female";

/** TargetPlanActivationRequest */
export interface TargetPlanActivationRequest {
  activity_level: ActivityLevel;
  /**
   * Birth Date
   * @format date
   */
  birth_date: string;
  /** Confirmed */
  confirmed: true;
  /**
   * Expected Preview Hash
   * @minLength 64
   * @maxLength 64
   * @pattern ^[0-9a-f]{64}$
   */
  expected_preview_hash: string;
  /**
   * Fat Pct
   * @min 0.15
   * @max 0.4
   * @default 0.25
   */
  fat_pct?: number;
  goal: Goal;
  /**
   * Height Cm
   * @min 100
   * @max 250
   */
  height_cm: number;
  /**
   * Protein Per Kg
   * @min 1
   * @max 3
   * @default 1.2
   */
  protein_per_kg?: number;
  /**
   * Selected Cut Intensity
   * @default 0.2
   */
  selected_cut_intensity?: 0.15 | 0.2 | 0.25;
  sex: Sex;
  /**
   * Weight Kg
   * @min 20
   * @max 300
   */
  weight_kg: number;
}

/** TargetPlanActivationResponse */
export interface TargetPlanActivationResponse {
  plan: TargetPlanSummary;
  replaced_plan?: TargetPlanSummary | null;
}

/** TargetPlanHistoryResponse */
export interface TargetPlanHistoryResponse {
  /** Items */
  items: TargetPlanSummary[];
  /** Next Cursor */
  next_cursor?: string | null;
}

/** TargetPlanReplacementRequest */
export interface TargetPlanReplacementRequest {
  activity_level: ActivityLevel;
  /**
   * Birth Date
   * @format date
   */
  birth_date: string;
  /**
   * Expected Preview Hash
   * @minLength 64
   * @maxLength 64
   * @pattern ^[0-9a-f]{64}$
   */
  expected_preview_hash: string;
  /**
   * Fat Pct
   * @min 0.15
   * @max 0.4
   * @default 0.25
   */
  fat_pct?: number;
  goal: Goal;
  /**
   * Height Cm
   * @min 100
   * @max 250
   */
  height_cm: number;
  /**
   * Protein Per Kg
   * @min 1
   * @max 3
   * @default 1.2
   */
  protein_per_kg?: number;
  /** Replace Confirmed */
  replace_confirmed: true;
  /**
   * Selected Cut Intensity
   * @default 0.2
   */
  selected_cut_intensity?: 0.15 | 0.2 | 0.25;
  sex: Sex;
  /**
   * Weight Kg
   * @min 20
   * @max 300
   */
  weight_kg: number;
}

/** TargetPlanSummary */
export interface TargetPlanSummary {
  /** Activated At */
  activated_at: string | null;
  /** Calendar Timezone */
  calendar_timezone: string;
  /** Closed At */
  closed_at: string | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /**
   * Effective From
   * @format date
   */
  effective_from: string;
  /** Effective To */
  effective_to: string | null;
  /**
   * Id
   * @format uuid
   */
  id: string;
  /** Predecessor Plan Id */
  predecessor_plan_id: string | null;
  /** Status */
  status: "active" | "scheduled" | "closed" | "superseded_before_effective";
  /** Superseded At */
  superseded_at: string | null;
  /** Superseded By Plan Id */
  superseded_by_plan_id: string | null;
  targets: TargetResponse;
}

/** TargetResponse */
export interface TargetResponse {
  /** Additional Targets */
  additional_targets?: AdditionalNutrientTarget[];
  /** Applied Deficit Kcal */
  applied_deficit_kcal: number;
  /** Bmr */
  bmr: number;
  /** Calculation Engine Version */
  calculation_engine_version: string;
  /** Calculation Warnings */
  calculation_warnings?: CalculationWarningResponse[];
  /** Calories */
  calories: number;
  /** Can Activate */
  can_activate: boolean;
  /**
   * Carb Clamped
   * @default false
   */
  carb_clamped?: boolean;
  /** Carb G */
  carb_g: number;
  /** Deficit Cap Applied */
  deficit_cap_applied: boolean;
  /** Fat G */
  fat_g: number;
  /** Final Target Calories */
  final_target_calories: number;
  /** Nutrition Registry Version */
  nutrition_registry_version: string;
  /** Preview Hash */
  preview_hash?: string | null;
  protein_calculation: ProteinCalculationResponse;
  /** Protein G */
  protein_g: number;
  /** Requested Deficit Kcal */
  requested_deficit_kcal: number;
  /** Safety Outcome */
  safety_outcome:
    | "normal"
    | "specialist_review_required"
    | "very_low_energy_blocked";
  /** Selected Cut Intensity */
  selected_cut_intensity: number;
  /** Target Calories */
  target_calories: number;
  /** Tdee */
  tdee: number;
}

/** TargetSourceResponse */
export interface TargetSourceResponse {
  plan: TargetPlanSummary | null;
  /** Target Provenance */
  target_provenance:
    | "versioned_plan"
    | "legacy_unversioned"
    | "no_target_source";
  /** Target Source Detail */
  target_source_detail:
    | "effective_target_plan"
    | "legacy_transition_snapshot"
    | "no_preserved_target_source";
  targets: TargetResponse | null;
}

/** UnitBasis */
export type UnitBasis = "g" | "ml";

/** ValidationError */
export interface ValidationError {
  /** Context */
  ctx?: object;
  /** Input */
  input?: any;
  /** Location */
  loc: (string | number)[];
  /** Message */
  msg: string;
  /** Error Type */
  type: string;
}

/** WeekSummary */
export interface WeekSummary {
  /** Days */
  days: DaySummary[];
  /**
   * End
   * @format date
   */
  end: string;
  /**
   * Start
   * @format date
   */
  start: string;
  targets?: TargetResponse | null;
  weekly_totals: NutritionTotals;
}

export namespace Account {
  /**
   * No description
   * @tags account
   * @name CurrentAccountAccountMeGet
   * @summary Current Account
   * @request GET:/account/me
   * @secure
   */
  export namespace CurrentAccountAccountMeGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = AccountResponse;
  }

  /**
   * No description
   * @tags account
   * @name CurrentCalendarAccountCalendarGet
   * @summary Current Calendar
   * @request GET:/account/calendar
   * @secure
   */
  export namespace CurrentCalendarAccountCalendarGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = CalendarAuthorityResponse;
  }
}

export namespace Admin {
  /**
   * No description
   * @tags admin-foods
   * @name ArchiveAdminFoodAdminFoodsFoodIdArchivePost
   * @summary Archive Admin Food
   * @request POST:/admin/foods/{food_id}/archive
   * @secure
   */
  export namespace ArchiveAdminFoodAdminFoodsFoodIdArchivePost {
    export type RequestParams = {
      /**
       * Food Id
       * @format uuid
       */
      foodId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodResponse;
  }

  /**
   * No description
   * @tags admin-foods
   * @name DeleteAdminFoodAdminFoodsFoodIdDelete
   * @summary Delete Admin Food
   * @request DELETE:/admin/foods/{food_id}
   * @secure
   */
  export namespace DeleteAdminFoodAdminFoodsFoodIdDelete {
    export type RequestParams = {
      /**
       * Food Id
       * @format uuid
       */
      foodId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodDeleteResponse;
  }

  /**
   * No description
   * @tags admin
   * @name ListUsersAdminUsersGet
   * @summary List Users
   * @request GET:/admin/users
   * @secure
   */
  export namespace ListUsersAdminUsersGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /**
       * Page
       * @min 1
       * @default 1
       */
      page?: number;
      /**
       * Page Size
       * @min 1
       * @max 100
       * @default 20
       */
      page_size?: number;
      /** Search */
      search?: string | null;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = AdminUserListResponse;
  }

  /**
   * No description
   * @tags admin-foods
   * @name ReadAdminFoodAdminFoodsFoodIdGet
   * @summary Read Admin Food
   * @request GET:/admin/foods/{food_id}
   * @secure
   */
  export namespace ReadAdminFoodAdminFoodsFoodIdGet {
    export type RequestParams = {
      /**
       * Food Id
       * @format uuid
       */
      foodId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodResponse;
  }

  /**
   * No description
   * @tags admin-foods
   * @name ReadAdminFoodsAdminFoodsGet
   * @summary Read Admin Foods
   * @request GET:/admin/foods
   * @secure
   */
  export namespace ReadAdminFoodsAdminFoodsGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /** Category */
      category?: string | null;
      /**
       * Page
       * @min 1
       * @default 1
       */
      page?: number;
      /**
       * Page Size
       * @min 1
       * @max 100
       * @default 20
       */
      page_size?: number;
      /** Search */
      search?: string | null;
      /**
       * Sort
       * @default "name"
       */
      sort?: "name" | "recent" | "calories" | "protein";
      /** Status */
      status?: FoodStatus | null;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodListResponse;
  }

  /**
   * No description
   * @tags admin-foods
   * @name RestoreAdminFoodAdminFoodsFoodIdRestorePost
   * @summary Restore Admin Food
   * @request POST:/admin/foods/{food_id}/restore
   * @secure
   */
  export namespace RestoreAdminFoodAdminFoodsFoodIdRestorePost {
    export type RequestParams = {
      /**
       * Food Id
       * @format uuid
       */
      foodId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodResponse;
  }

  /**
   * No description
   * @tags admin
   * @name UserDetailAdminUsersPrincipalIdGet
   * @summary User Detail
   * @request GET:/admin/users/{principal_id}
   * @secure
   */
  export namespace UserDetailAdminUsersPrincipalIdGet {
    export type RequestParams = {
      /**
       * Principal Id
       * @format uuid
       */
      principalId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = AdminUserDetail;
  }

  /**
   * No description
   * @tags admin
   * @name UserDiaryAdminUsersPrincipalIdDiaryGet
   * @summary User Diary
   * @request GET:/admin/users/{principal_id}/diary
   * @secure
   */
  export namespace UserDiaryAdminUsersPrincipalIdDiaryGet {
    export type RequestParams = {
      /**
       * Principal Id
       * @format uuid
       */
      principalId: string;
    };
    export type RequestQuery = {
      /** Cursor */
      cursor?: string | null;
      /** Entry Date */
      entry_date?: string | null;
      /**
       * Limit
       * @min 1
       * @max 100
       * @default 50
       */
      limit?: number;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = AdminDiaryPage;
  }

  /**
   * No description
   * @tags admin
   * @name UserTargetPlansAdminUsersPrincipalIdTargetPlansGet
   * @summary User Target Plans
   * @request GET:/admin/users/{principal_id}/target-plans
   * @secure
   */
  export namespace UserTargetPlansAdminUsersPrincipalIdTargetPlansGet {
    export type RequestParams = {
      /**
       * Principal Id
       * @format uuid
       */
      principalId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = TargetPlanHistoryResponse;
  }

  /**
   * No description
   * @tags admin
   * @name UserWeekAdminUsersPrincipalIdDiaryWeekGet
   * @summary User Week
   * @request GET:/admin/users/{principal_id}/diary/week
   * @secure
   */
  export namespace UserWeekAdminUsersPrincipalIdDiaryWeekGet {
    export type RequestParams = {
      /**
       * Principal Id
       * @format uuid
       */
      principalId: string;
    };
    export type RequestQuery = {
      /**
       * Start
       * @format date
       */
      start: string;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = WeekSummary;
  }
}

export namespace Diary {
  /**
   * No description
   * @tags diary
   * @name AddEntryDiaryEntriesPost
   * @summary Add Entry
   * @request POST:/diary/entries
   * @secure
   */
  export namespace AddEntryDiaryEntriesPost {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = {
      /**
       * Entry Date
       * @format date
       */
      entry_date: string;
      /**
       * Food Id
       * @format uuid
       */
      food_id: string;
      /** Id */
      id?: string | null;
      /** @default "unspecified" */
      meal_type?: MealType;
      /**
       * Quantity
       * @exclusiveMin 0
       * @max 50
       */
      quantity: number;
    };
    export type RequestHeaders = {};
    export type ResponseBody = DiaryEntryResponse;
  }

  /**
   * No description
   * @tags diary
   * @name EditEntryDiaryEntriesEntryIdPatch
   * @summary Edit Entry
   * @request PATCH:/diary/entries/{entry_id}
   * @secure
   */
  export namespace EditEntryDiaryEntriesEntryIdPatch {
    export type RequestParams = {
      /**
       * Entry Id
       * @format uuid
       */
      entryId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = {
      meal_type?: MealType | null;
      /** Quantity */
      quantity?: number | null;
    };
    export type RequestHeaders = {};
    export type ResponseBody = DiaryEntryResponse;
  }

  /**
   * No description
   * @tags diary
   * @name ReadEntriesDiaryEntriesGet
   * @summary Read Entries
   * @request GET:/diary/entries
   * @secure
   */
  export namespace ReadEntriesDiaryEntriesGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /** Entry Date */
      entry_date?: string | null;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = DiaryEntryResponse[];
  }

  /**
   * No description
   * @tags diary
   * @name ReadEntryDiaryEntriesEntryIdGet
   * @summary Read Entry
   * @request GET:/diary/entries/{entry_id}
   * @secure
   */
  export namespace ReadEntryDiaryEntriesEntryIdGet {
    export type RequestParams = {
      /**
       * Entry Id
       * @format uuid
       */
      entryId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = DiaryEntryResponse;
  }

  /**
   * No description
   * @tags diary
   * @name ReadWeekDiaryWeekGet
   * @summary Read Week
   * @request GET:/diary/week
   * @secure
   */
  export namespace ReadWeekDiaryWeekGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /**
       * Start
       * @format date
       */
      start: string;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = WeekSummary;
  }

  /**
   * No description
   * @tags diary
   * @name RemoveEntryDiaryEntriesEntryIdDelete
   * @summary Remove Entry
   * @request DELETE:/diary/entries/{entry_id}
   * @secure
   */
  export namespace RemoveEntryDiaryEntriesEntryIdDelete {
    export type RequestParams = {
      /**
       * Entry Id
       * @format uuid
       */
      entryId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = void;
  }
}

export namespace Foods {
  /**
   * No description
   * @tags foods
   * @name AddFoodFoodsPost
   * @summary Add Food
   * @request POST:/foods
   * @secure
   */
  export namespace AddFoodFoodsPost {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = {
      /** Vitamin B12 Mcg */
      vitamin_b12_mcg?: number | null;
      /** Added Sugar G */
      added_sugar_g?: number | null;
      /** Analytical Traits */
      analytical_traits?: string[];
      baked_good_type?: BakedGoodType | null;
      /** Brand */
      brand?: string | null;
      /** Calcium Mg */
      calcium_mg?: number | null;
      /**
       * Calories
       * @min 0
       * @max 3000
       */
      calories: number;
      /**
       * Carb G
       * @min 0
       * @max 500
       */
      carb_g: number;
      /** Cholesterol Mg */
      cholesterol_mg?: number | null;
      /** Data Source */
      data_source?: string | null;
      default_unit_type: DefaultUnitType;
      /**
       * Fat G
       * @min 0
       * @max 300
       */
      fat_g: number;
      /** Fiber G */
      fiber_g?: number | null;
      /** Folate Dfe Mcg */
      folate_dfe_mcg?: number | null;
      /** Folate Mcg */
      folate_mcg?: number | null;
      /** Food Category Key */
      food_category_key: string;
      /** @default "unknown" */
      food_kind?: FoodKind;
      grain_starch_type?: GrainStarchType | null;
      grain_type?: GrainType | null;
      /** Group Contributions */
      group_contributions?: FoodGroupContributionInput[];
      /** Id */
      id?: string | null;
      ingredients?: IngredientsInput;
      /** Iodine Mcg */
      iodine_mcg?: number | null;
      /** Iron Mg */
      iron_mg?: number | null;
      /** Magnesium Mg */
      magnesium_mg?: number | null;
      /** Name */
      name: string;
      /** Notes */
      notes?: string | null;
      nova?: NovaInput | null;
      nutrition_basis: NutritionBasis;
      nutrition_source?: NutritionSourceInput;
      /** Potassium Mg */
      potassium_mg?: number | null;
      /**
       * Protein G
       * @min 0
       * @max 300
       */
      protein_g: number;
      /** Saturated Fat G */
      saturated_fat_g?: number | null;
      /** Selenium Mcg */
      selenium_mcg?: number | null;
      /** Sodium Mg */
      sodium_mg?: number | null;
      /** Sugar G */
      sugar_g?: number | null;
      /** Trans Fat G */
      trans_fat_g?: number | null;
      /**
       * Unit Amount
       * @exclusiveMin 0
       * @max 2000
       */
      unit_amount: number;
      unit_basis: UnitBasis;
      /** Vitamin A Mcg */
      vitamin_a_mcg?: number | null;
      /** Vitamin A Rae Mcg */
      vitamin_a_rae_mcg?: number | null;
      /** Vitamin C Mg */
      vitamin_c_mg?: number | null;
      /** Vitamin D Mcg */
      vitamin_d_mcg?: number | null;
      /** Vitamin K Mcg */
      vitamin_k_mcg?: number | null;
      /** Zinc Mg */
      zinc_mg?: number | null;
    };
    export type RequestHeaders = {};
    export type ResponseBody = FoodResponse;
  }

  /**
   * No description
   * @tags foods
   * @name EditFoodFoodsFoodIdPut
   * @summary Edit Food
   * @request PUT:/foods/{food_id}
   * @secure
   */
  export namespace EditFoodFoodsFoodIdPut {
    export type RequestParams = {
      /**
       * Food Id
       * @format uuid
       */
      foodId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = {
      /** Vitamin B12 Mcg */
      vitamin_b12_mcg?: number | null;
      /** Added Sugar G */
      added_sugar_g?: number | null;
      /** Analytical Traits */
      analytical_traits?: string[] | null;
      baked_good_type?: BakedGoodType | null;
      /** Brand */
      brand?: string | null;
      /** Calcium Mg */
      calcium_mg?: number | null;
      /** Calories */
      calories?: number | null;
      /** Carb G */
      carb_g?: number | null;
      /** Cholesterol Mg */
      cholesterol_mg?: number | null;
      /** Data Source */
      data_source?: string | null;
      default_unit_type?: DefaultUnitType | null;
      /** Fat G */
      fat_g?: number | null;
      /** Fiber G */
      fiber_g?: number | null;
      /** Folate Dfe Mcg */
      folate_dfe_mcg?: number | null;
      /** Folate Mcg */
      folate_mcg?: number | null;
      /** Food Category Key */
      food_category_key?: string | null;
      food_kind?: FoodKind | null;
      grain_starch_type?: GrainStarchType | null;
      grain_type?: GrainType | null;
      /** Group Contributions */
      group_contributions?: FoodGroupContributionInput[] | null;
      ingredients?: IngredientsInput | null;
      /** Iodine Mcg */
      iodine_mcg?: number | null;
      /** Iron Mg */
      iron_mg?: number | null;
      /** Magnesium Mg */
      magnesium_mg?: number | null;
      /** Name */
      name?: string | null;
      /** Notes */
      notes?: string | null;
      nova?: NovaInput | null;
      nutrition_basis?: NutritionBasis | null;
      nutrition_source?: NutritionSourceInput | null;
      /** Potassium Mg */
      potassium_mg?: number | null;
      /** Protein G */
      protein_g?: number | null;
      /** Saturated Fat G */
      saturated_fat_g?: number | null;
      /** Selenium Mcg */
      selenium_mcg?: number | null;
      /** Sodium Mg */
      sodium_mg?: number | null;
      /** Sugar G */
      sugar_g?: number | null;
      /** Trans Fat G */
      trans_fat_g?: number | null;
      /** Unit Amount */
      unit_amount?: number | null;
      unit_basis?: UnitBasis | null;
      /** Vitamin A Mcg */
      vitamin_a_mcg?: number | null;
      /** Vitamin A Rae Mcg */
      vitamin_a_rae_mcg?: number | null;
      /** Vitamin C Mg */
      vitamin_c_mg?: number | null;
      /** Vitamin D Mcg */
      vitamin_d_mcg?: number | null;
      /** Vitamin K Mcg */
      vitamin_k_mcg?: number | null;
      /** Zinc Mg */
      zinc_mg?: number | null;
    };
    export type RequestHeaders = {};
    export type ResponseBody = FoodResponse;
  }

  /**
   * No description
   * @tags foods
   * @name ReadFoodFoodsFoodIdGet
   * @summary Read Food
   * @request GET:/foods/{food_id}
   * @secure
   */
  export namespace ReadFoodFoodsFoodIdGet {
    export type RequestParams = {
      /**
       * Food Id
       * @format uuid
       */
      foodId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodResponse;
  }

  /**
   * No description
   * @tags foods
   * @name ReadFoodPickerFoodsPickerGet
   * @summary Read Food Picker
   * @request GET:/foods/picker
   * @secure
   */
  export namespace ReadFoodPickerFoodsPickerGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /** Cursor */
      cursor?: string | null;
      /**
       * Limit
       * @min 1
       * @max 30
       * @default 30
       */
      limit?: number;
      /**
       * Search
       * @default ""
       */
      search?: string;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodPickerResponse;
  }

  /**
   * No description
   * @tags foods
   * @name ReadFoodsFoodsGet
   * @summary Read Foods
   * @request GET:/foods
   * @secure
   */
  export namespace ReadFoodsFoodsGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /** Category */
      category?: string | null;
      /** Page */
      page?: number | null;
      /**
       * Page Size
       * @min 1
       * @max 100
       * @default 20
       */
      page_size?: number;
      /** Q */
      q?: string | null;
      /** Search */
      search?: string | null;
      /**
       * Sort
       * @default "name"
       */
      sort?: "name" | "recent" | "calories" | "protein";
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = FoodResponse[] | FoodListResponse;
  }

  /**
   * No description
   * @tags foods
   * @name RemoveFoodFoodsFoodIdDelete
   * @summary Remove Food
   * @request DELETE:/foods/{food_id}
   * @secure
   */
  export namespace RemoveFoodFoodsFoodIdDelete {
    export type RequestParams = {
      /**
       * Food Id
       * @format uuid
       */
      foodId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = void;
  }
}

export namespace Health {
  /**
   * No description
   * @tags health
   * @name HealthHealthGet
   * @summary Health
   * @request GET:/health
   */
  export namespace HealthHealthGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = Record<string, string>;
  }
}

export namespace Nutrition {
  /**
   * No description
   * @tags nutrition
   * @name ReadRegistryNutritionRegistryGet
   * @summary Read Registry
   * @request GET:/nutrition/registry
   * @secure
   */
  export namespace ReadRegistryNutritionRegistryGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {
      /** If-None-Match */
      "if-none-match"?: string | null;
    };
    export type ResponseBody = NutritionRegistryResponse;
  }
}

export namespace Profile {
  /**
   * No description
   * @tags profile
   * @name PreviewProfileProfilePreviewPost
   * @summary Preview Profile
   * @request POST:/profile/preview
   * @secure
   */
  export namespace PreviewProfileProfilePreviewPost {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = ProfilePreview;
    export type RequestHeaders = {};
    export type ResponseBody = TargetResponse;
  }

  /**
   * No description
   * @tags profile
   * @name ReadProfileProfileGet
   * @summary Read Profile
   * @request GET:/profile
   * @secure
   */
  export namespace ReadProfileProfileGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = ProfileResponse;
  }

  /**
   * No description
   * @tags profile
   * @name SaveProfileProfilePut
   * @summary Save Profile
   * @request PUT:/profile
   * @secure
   */
  export namespace SaveProfileProfilePut {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = ProfileUpsert;
    export type RequestHeaders = {};
    export type ResponseBody = ProfileResponse;
  }
}

export namespace TargetPlans {
  /**
   * No description
   * @tags target-plans
   * @name ActivateTargetPlansActivatePost
   * @summary Activate
   * @request POST:/target-plans/activate
   * @secure
   */
  export namespace ActivateTargetPlansActivatePost {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = TargetPlanActivationRequest;
    export type RequestHeaders = {
      /** Idempotency-Key */
      "Idempotency-Key": string;
    };
    export type ResponseBody = TargetPlanActivationResponse;
  }

  /**
   * No description
   * @tags target-plans
   * @name CurrentTargetPlansCurrentGet
   * @summary Current
   * @request GET:/target-plans/current
   * @secure
   */
  export namespace CurrentTargetPlansCurrentGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /** Date */
      date?: string | null;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = TargetSourceResponse;
  }

  /**
   * No description
   * @tags target-plans
   * @name HistoryTargetPlansGet
   * @summary History
   * @request GET:/target-plans
   * @secure
   */
  export namespace HistoryTargetPlansGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /** Cursor */
      cursor?: string | null;
      /**
       * Limit
       * @min 1
       * @max 100
       * @default 20
       */
      limit?: number;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = TargetPlanHistoryResponse;
  }

  /**
   * No description
   * @tags target-plans
   * @name PendingTargetPlansPendingGet
   * @summary Pending
   * @request GET:/target-plans/pending
   * @secure
   */
  export namespace PendingTargetPlansPendingGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = TargetPlanSummary | null;
  }

  /**
   * No description
   * @tags target-plans
   * @name ReplaceTargetPlansPendingReplacePost
   * @summary Replace
   * @request POST:/target-plans/pending/replace
   * @secure
   */
  export namespace ReplaceTargetPlansPendingReplacePost {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = TargetPlanReplacementRequest;
    export type RequestHeaders = {
      /** Idempotency-Key */
      "Idempotency-Key": string;
    };
    export type ResponseBody = TargetPlanActivationResponse;
  }
}
