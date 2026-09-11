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

/** AdminDiaryDayStatusPage */
export interface AdminDiaryDayStatusPage {
  /** Items */
  items: DiaryDayStatusResponse[];
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

/** DaySummary */
export interface DaySummary {
  /** Completed At */
  completed_at: string | null;
  /**
   * Date
   * @format date
   */
  date: string;
  /**
   * Entry Count
   * @min 0
   */
  entry_count: number;
  logging_status: DiaryLoggingStatus;
  /**
   * Logging Status Version
   * @min 0
   */
  logging_status_version: number;
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

/** DiaryDayStatusCommand */
export interface DiaryDayStatusCommand {
  /**
   * Expected Version
   * @min 0
   */
  expected_version: number;
}

/** DiaryDayStatusResponse */
export interface DiaryDayStatusResponse {
  calendar: CalendarAuthorityResponse;
  /** Completed At */
  completed_at: string | null;
  /**
   * Date
   * @format date
   */
  date: string;
  /**
   * Entry Count
   * @min 0
   */
  entry_count: number;
  logging_status: DiaryLoggingStatus;
  /**
   * Logging Status Version
   * @min 0
   */
  logging_status_version: number;
}

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
  food: DiaryFoodReference;
  /**
   * Food Id
   * @format uuid
   */
  food_id: string;
  /**
   * Id
   * @format uuid
   */
  id: string;
  meal_type: MealType;
  /** Quantity */
  quantity: number;
  /** Recorded Unit Amount */
  recorded_unit_amount: number;
  recorded_unit_basis: UnitBasis;
  /** Recorded Unit Label */
  recorded_unit_label: string | null;
  recorded_unit_type: DefaultUnitType;
  /** Target Plan Id */
  target_plan_id: string | null;
  /** Target Provenance */
  target_provenance:
    | "versioned_plan"
    | "legacy_unversioned"
    | "no_target_source";
  totals: NutritionTotals;
}

/** DiaryFoodReference */
export interface DiaryFoodReference {
  /** Brand */
  brand?: string | null;
  /**
   * Id
   * @format uuid
   */
  id: string;
  /** Name */
  name: string;
}

/** DiaryLoggingStatus */
export type DiaryLoggingStatus = "unregistered" | "partial" | "complete";

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

/** FoodListResponse */
export interface FoodListResponse {
  /** Categories */
  categories: string[];
  /** Items */
  items: FoodResponseV3[];
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

/**
 * FoodResponseV3
 * Active Food response contract.
 */
export interface FoodResponseV3 {
  /** Vitamin B12 Mcg */
  vitamin_b12_mcg?: number | null;
  /** Added Sugar G */
  added_sugar_g?: number | null;
  /** Archived At */
  archived_at: string | null;
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
  /**
   * Id
   * @format uuid
   */
  id: string;
  /** Ingredients */
  ingredients?: string | null;
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
  net_carbs_g: number | null;
  /** Notes */
  notes?: string | null;
  nutrition_basis: NutritionBasis;
  nutrition_data_source: NutritionDataSource;
  /** Potassium Mg */
  potassium_mg?: number | null;
  /** Primary Category */
  primary_category: string;
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
  /** Subcategory */
  subcategory: string;
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

/** Goal */
export type Goal = "cut" | "maintain" | "bulk";

/** HTTPValidationError */
export interface HTTPValidationError {
  /** Detail */
  detail?: ValidationError[];
}

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

/** NutritionBasis */
export type NutritionBasis = "per_100g" | "per_100ml";

/** NutritionDataSource */
export type NutritionDataSource = "official" | "estimated";

/** NutritionRegistryResponse */
export interface NutritionRegistryResponse {
  /** Calculation Engine Version */
  calculation_engine_version: "2.0.0";
  /** Calculation Policy */
  calculation_policy: Record<string, any>;
  /** Food Taxonomy */
  food_taxonomy: RegistryPrimaryCategoryDefinition[];
  /** Nutrients */
  nutrients: RegistryNutrientDefinition[];
  /** Nutrition Data Sources */
  nutrition_data_sources: RegistryLabelDefinition[];
  /** Nutrition Registry Version */
  nutrition_registry_version: "4.0.0";
  /** Primary Categories */
  primary_categories: string[];
  /** Registry Schema Version */
  registry_schema_version: 4;
  /** Rules Manifest Hash */
  rules_manifest_hash: string;
  /** Target Types */
  target_types: string[];
}

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
  net_carbs_g?: number | null;
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

/** RegistryLabelDefinition */
export interface RegistryLabelDefinition {
  /** Key */
  key: string;
  /** Label Ar */
  label_ar: string;
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

/** RegistryPrimaryCategoryDefinition */
export interface RegistryPrimaryCategoryDefinition {
  /** Key */
  key: string;
  /** Label Ar */
  label_ar: string;
  /** Subcategories */
  subcategories: RegistryLabelDefinition[];
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
    export type ResponseBody = FoodResponseV3;
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
    export type ResponseBody = FoodResponseV3;
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
      /**
       * Archived
       * @default false
       */
      archived?: boolean | null;
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
    export type ResponseBody = FoodResponseV3;
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
   * @name UserDiaryDaysAdminUsersPrincipalIdDiaryDaysGet
   * @summary User Diary Days
   * @request GET:/admin/users/{principal_id}/diary-days
   * @secure
   */
  export namespace UserDiaryDaysAdminUsersPrincipalIdDiaryDaysGet {
    export type RequestParams = {
      /**
       * Principal Id
       * @format uuid
       */
      principalId: string;
    };
    export type RequestQuery = {
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
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = AdminDiaryDayStatusPage;
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
    export type RequestHeaders = {
      /** If-Match */
      "If-Match": string;
    };
    export type ResponseBody = DiaryEntryResponse;
  }

  /**
   * No description
   * @tags diary
   * @name CompleteDayDiaryDaysDiaryDateCompletePut
   * @summary Complete Day
   * @request PUT:/diary/days/{diary_date}/complete
   * @secure
   */
  export namespace CompleteDayDiaryDaysDiaryDateCompletePut {
    export type RequestParams = {
      /**
       * Diary Date
       * @format date
       */
      diaryDate: string;
    };
    export type RequestQuery = {};
    export type RequestBody = DiaryDayStatusCommand;
    export type RequestHeaders = {
      /** Idempotency-Key */
      "Idempotency-Key": string;
      /** If-Match */
      "If-Match"?: string | null;
    };
    export type ResponseBody = DiaryDayStatusResponse;
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
    export type RequestHeaders = {
      /** If-Match */
      "If-Match": string;
    };
    export type ResponseBody = DiaryEntryResponse;
  }

  /**
   * No description
   * @tags diary
   * @name ReadDayStatusDiaryDaysDiaryDateStatusGet
   * @summary Read Day Status
   * @request GET:/diary/days/{diary_date}/status
   * @secure
   */
  export namespace ReadDayStatusDiaryDaysDiaryDateStatusGet {
    export type RequestParams = {
      /**
       * Diary Date
       * @format date
       */
      diaryDate: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = DiaryDayStatusResponse;
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
   * @name RemoveEntryDocumentedDiaryEntriesEntryIdDelete
   * @summary Remove Entry Documented
   * @request DELETE:/diary/entries/{entry_id}
   * @secure
   */
  export namespace RemoveEntryDocumentedDiaryEntriesEntryIdDelete {
    export type RequestParams = {
      /**
       * Entry Id
       * @format uuid
       */
      entryId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {
      /** If-Match */
      "If-Match": string;
    };
    export type ResponseBody = void;
  }

  /**
   * No description
   * @tags diary
   * @name ReopenDayDiaryDaysDiaryDateReopenPut
   * @summary Reopen Day
   * @request PUT:/diary/days/{diary_date}/reopen
   * @secure
   */
  export namespace ReopenDayDiaryDaysDiaryDateReopenPut {
    export type RequestParams = {
      /**
       * Diary Date
       * @format date
       */
      diaryDate: string;
    };
    export type RequestQuery = {};
    export type RequestBody = DiaryDayStatusCommand;
    export type RequestHeaders = {
      /** Idempotency-Key */
      "Idempotency-Key": string;
      /** If-Match */
      "If-Match"?: string | null;
    };
    export type ResponseBody = DiaryDayStatusResponse;
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
      /** Id */
      id?: string | null;
      /** Ingredients */
      ingredients?: string | null;
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
      nutrition_basis: NutritionBasis;
      nutrition_data_source: NutritionDataSource;
      /** Potassium Mg */
      potassium_mg?: number | null;
      /** Primary Category */
      primary_category: string;
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
      /** Subcategory */
      subcategory: string;
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
    export type ResponseBody = FoodResponseV3;
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
      default_unit_type?: DefaultUnitType | null;
      /** Fat G */
      fat_g?: number | null;
      /** Fiber G */
      fiber_g?: number | null;
      /** Folate Dfe Mcg */
      folate_dfe_mcg?: number | null;
      /** Folate Mcg */
      folate_mcg?: number | null;
      /** Ingredients */
      ingredients?: string | null;
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
      nutrition_basis?: NutritionBasis | null;
      nutrition_data_source?: NutritionDataSource | null;
      /** Potassium Mg */
      potassium_mg?: number | null;
      /** Primary Category */
      primary_category?: string | null;
      /** Protein G */
      protein_g?: number | null;
      /** Saturated Fat G */
      saturated_fat_g?: number | null;
      /** Selenium Mcg */
      selenium_mcg?: number | null;
      /** Sodium Mg */
      sodium_mg?: number | null;
      /** Subcategory */
      subcategory?: string | null;
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
    export type ResponseBody = FoodResponseV3;
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
    export type ResponseBody = FoodResponseV3;
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
    export type ResponseBody = FoodResponseV3[] | FoodListResponse;
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
