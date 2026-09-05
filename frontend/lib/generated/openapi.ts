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

/** AnalysisComparisonV2 */
export interface AnalysisComparisonV2 {
  /** Difference */
  difference: number | null;
  /** Normalized Adverse Delta */
  normalized_adverse_delta: number | null;
  /** Reason */
  reason:
    | "comparable"
    | "insufficient_complete_days"
    | "insufficient_coverage"
    | "limited_coverage"
    | "coverage_mismatch"
    | "target_incompatible"
    | "version_incompatible"
    | "invalid_target"
    | "stale_evidence"
    | "unavailable_value";
  /** Status */
  status:
    | "improved"
    | "worsened"
    | "no_material_change"
    | "descriptive_increase"
    | "descriptive_decrease"
    | "descriptive_change"
    | "not_comparable";
}

/** AnalysisCompleteDayBandCountsV1 */
export interface AnalysisCompleteDayBandCountsV1 {
  /**
   * 0-3
   * @min 0
   */
  "0-3": number;
  /**
   * 4-5
   * @min 0
   */
  "4-5": number;
  /**
   * 6-7
   * @min 0
   */
  "6-7": number;
}

/** AnalysisContributorV2 */
export interface AnalysisContributorV2 {
  /**
   * Contribution Value
   * @min 0
   */
  contribution_value: number;
  /**
   * Diary Date
   * @format date
   */
  diary_date: string;
  /**
   * Relation
   * @default "supports_observed_value"
   */
  relation?: "supports_observed_value";
  /**
   * Source Ref
   * @format uuid
   */
  source_ref: string;
  /**
   * Source Version
   * @minLength 1
   */
  source_version: string;
  /**
   * Unit
   * @minLength 1
   */
  unit: string;
}

/** AnalysisContributorsV2 */
export interface AnalysisContributorsV2 {
  /**
   * Current
   * @maxItems 5
   */
  current: AnalysisContributorV2[];
  /**
   * Previous
   * @maxItems 5
   */
  previous: AnalysisContributorV2[];
}

/** AnalysisCoverageBandCountsV1 */
export interface AnalysisCoverageBandCountsV1 {
  /**
   * 0 To Lt 50
   * @min 0
   */
  "0_to_lt_50": number;
  /**
   * 50 To Lt 75
   * @min 0
   */
  "50_to_lt_75": number;
  /**
   * 75 To 100
   * @min 0
   */
  "75_to_100": number;
  /**
   * Unknown
   * @min 0
   */
  unknown: number;
}

/** AnalysisDayFactV2 */
export interface AnalysisDayFactV2 {
  /** Analysis Eligible */
  analysis_eligible: boolean;
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
  /** Logging Status */
  logging_status: "unregistered" | "partial" | "complete";
  /**
   * Logging Status Version
   * @min 0
   */
  logging_status_version: number;
  /** Metric Values */
  metric_values: AnalysisDayMetricValueV2[];
  /** Snapshot Schema Versions */
  snapshot_schema_versions: number[];
}

/** AnalysisDayMetricValueV2 */
export interface AnalysisDayMetricValueV2 {
  /** Amount Qualifier */
  amount_qualifier: "exact" | "at_least" | "unavailable";
  /**
   * Known Entry Count
   * @min 0
   */
  known_entry_count: number;
  /**
   * Metric Key
   * @minLength 1
   */
  metric_key: string;
  /**
   * Total Entry Count
   * @min 0
   */
  total_entry_count: number;
  /**
   * Unit
   * @minLength 1
   */
  unit: string;
  /** Value */
  value: number | null;
  /** Value State */
  value_state: "known" | "explicit_zero" | "unknown";
}

/** AnalysisEvaluateCommandV2 */
export interface AnalysisEvaluateCommandV2 {
  /** Expected Current Revision */
  expected_current_revision?: number | null;
}

/** AnalysisLatencyBandCountsV1 */
export interface AnalysisLatencyBandCountsV1 {
  /**
   * 250 To Lt 500 Ms
   * @min 0
   */
  "250_to_lt_500_ms": number;
  /**
   * 500 To Lt 1000 Ms
   * @min 0
   */
  "500_to_lt_1000_ms": number;
  /**
   * Gte 1000 Ms
   * @min 0
   */
  gte_1000_ms: number;
  /**
   * Lt 250 Ms
   * @min 0
   */
  lt_250_ms: number;
  /**
   * Unknown
   * @min 0
   */
  unknown: number;
}

/** AnalysisMetricEnergyCaloriesKcalPerDayV2 */
export interface AnalysisMetricEnergyCaloriesKcalPerDayV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "maximum"
   */
  direction?: "maximum";
  /**
   * Metric Key
   * @default "energy:calories_kcal_per_day"
   */
  metric_key?: "energy:calories_kcal_per_day";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "kcal/day"
   */
  unit?: "kcal/day";
}

/** AnalysisMetricGroupDairyFortifiedServingsPerDayV2 */
export interface AnalysisMetricGroupDairyFortifiedServingsPerDayV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "group:dairy_fortified_servings_per_day"
   */
  metric_key?: "group:dairy_fortified_servings_per_day";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "servings/day"
   */
  unit?: "servings/day";
}

/** AnalysisMetricGroupFruitVegetableGPerDayV2 */
export interface AnalysisMetricGroupFruitVegetableGPerDayV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "group:fruit_vegetable_g_per_day"
   */
  metric_key?: "group:fruit_vegetable_g_per_day";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricGroupLegumesServingsPerPeriodV2 */
export interface AnalysisMetricGroupLegumesServingsPerPeriodV2 {
  /**
   * Aggregation
   * @default "sum_period"
   */
  aggregation?: "sum_period";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "group:legumes_servings_per_period"
   */
  metric_key?: "group:legumes_servings_per_period";
  /**
   * Metric Kind
   * @default "period_total"
   */
  metric_kind?: "period_total";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "servings/7d"
   */
  unit?: "servings/7d";
}

/** AnalysisMetricGroupNutsSeedsServingsPerPeriodV2 */
export interface AnalysisMetricGroupNutsSeedsServingsPerPeriodV2 {
  /**
   * Aggregation
   * @default "sum_period"
   */
  aggregation?: "sum_period";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "group:nuts_seeds_servings_per_period"
   */
  metric_key?: "group:nuts_seeds_servings_per_period";
  /**
   * Metric Kind
   * @default "period_total"
   */
  metric_kind?: "period_total";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "servings/7d"
   */
  unit?: "servings/7d";
}

/** AnalysisMetricGroupOmega3SeafoodServingsPerPeriodV2 */
export interface AnalysisMetricGroupOmega3SeafoodServingsPerPeriodV2 {
  /**
   * Aggregation
   * @default "sum_period"
   */
  aggregation?: "sum_period";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "group:omega3_seafood_servings_per_period"
   */
  metric_key?: "group:omega3_seafood_servings_per_period";
  /**
   * Metric Kind
   * @default "period_total"
   */
  metric_kind?: "period_total";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "servings/7d"
   */
  unit?: "servings/7d";
}

/** AnalysisMetricGroupProcessedMeatOccurrenceDaysV2 */
export interface AnalysisMetricGroupProcessedMeatOccurrenceDaysV2 {
  /**
   * Aggregation
   * @default "distinct_positive_dates"
   */
  aggregation?: "distinct_positive_dates";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimize"
   */
  direction?: "minimize";
  /**
   * Metric Key
   * @default "group:processed_meat_occurrence_days"
   */
  metric_key?: "group:processed_meat_occurrence_days";
  /**
   * Metric Kind
   * @default "occurrence_days"
   */
  metric_kind?: "occurrence_days";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "days/7d"
   */
  unit?: "days/7d";
}

/** AnalysisMetricGroupRedMeatGPerPeriodV2 */
export interface AnalysisMetricGroupRedMeatGPerPeriodV2 {
  /**
   * Aggregation
   * @default "sum_period"
   */
  aggregation?: "sum_period";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "maximum"
   */
  direction?: "maximum";
  /**
   * Metric Key
   * @default "group:red_meat_g_per_period"
   */
  metric_key?: "group:red_meat_g_per_period";
  /**
   * Metric Kind
   * @default "period_total"
   */
  metric_kind?: "period_total";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/7d"
   */
  unit?: "g/7d";
}

/** AnalysisMetricGroupSeafoodServingsPerPeriodV2 */
export interface AnalysisMetricGroupSeafoodServingsPerPeriodV2 {
  /**
   * Aggregation
   * @default "sum_period"
   */
  aggregation?: "sum_period";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "group:seafood_servings_per_period"
   */
  metric_key?: "group:seafood_servings_per_period";
  /**
   * Metric Kind
   * @default "period_total"
   */
  metric_kind?: "period_total";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "servings/7d"
   */
  unit?: "servings/7d";
}

/** AnalysisMetricGroupSugarSweetenedBeverageOccurrenceDaysV2 */
export interface AnalysisMetricGroupSugarSweetenedBeverageOccurrenceDaysV2 {
  /**
   * Aggregation
   * @default "distinct_positive_dates"
   */
  aggregation?: "distinct_positive_dates";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimize"
   */
  direction?: "minimize";
  /**
   * Metric Key
   * @default "group:sugar_sweetened_beverage_occurrence_days"
   */
  metric_key?: "group:sugar_sweetened_beverage_occurrence_days";
  /**
   * Metric Kind
   * @default "occurrence_days"
   */
  metric_kind?: "occurrence_days";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "days/7d"
   */
  unit?: "days/7d";
}

/** AnalysisMetricGroupSweetsOccurrenceDaysV2 */
export interface AnalysisMetricGroupSweetsOccurrenceDaysV2 {
  /**
   * Aggregation
   * @default "distinct_positive_dates"
   */
  aggregation?: "distinct_positive_dates";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimize"
   */
  direction?: "minimize";
  /**
   * Metric Key
   * @default "group:sweets_occurrence_days"
   */
  metric_key?: "group:sweets_occurrence_days";
  /**
   * Metric Kind
   * @default "occurrence_days"
   */
  metric_kind?: "occurrence_days";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "days/7d"
   */
  unit?: "days/7d";
}

/** AnalysisMetricGroupWholeGrainSharePercentV2 */
export interface AnalysisMetricGroupWholeGrainSharePercentV2 {
  /**
   * Aggregation
   * @default "ratio_percent"
   */
  aggregation?: "ratio_percent";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "group:whole_grain_share_percent"
   */
  metric_key?: "group:whole_grain_share_percent";
  /**
   * Metric Kind
   * @default "share_percent"
   */
  metric_kind?: "share_percent";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "percent"
   */
  unit?: "percent";
}

/** AnalysisMetricMacroCarbGPerDayV2 */
export interface AnalysisMetricMacroCarbGPerDayV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "range"
   */
  direction?: "range";
  /**
   * Metric Key
   * @default "macro:carb_g_per_day"
   */
  metric_key?: "macro:carb_g_per_day";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricMacroFatGPerDayV2 */
export interface AnalysisMetricMacroFatGPerDayV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "range"
   */
  direction?: "range";
  /**
   * Metric Key
   * @default "macro:fat_g_per_day"
   */
  metric_key?: "macro:fat_g_per_day";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricMacroProteinGPerDayV2 */
export interface AnalysisMetricMacroProteinGPerDayV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "macro:protein_g_per_day"
   */
  metric_key?: "macro:protein_g_per_day";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricNutrientAddedSugarGV2 */
export interface AnalysisMetricNutrientAddedSugarGV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "maximum"
   */
  direction?: "maximum";
  /**
   * Metric Key
   * @default "nutrient:added_sugar_g"
   */
  metric_key?: "nutrient:added_sugar_g";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricNutrientCalciumMgV2 */
export interface AnalysisMetricNutrientCalciumMgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:calcium_mg"
   */
  metric_key?: "nutrient:calcium_mg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mg/day"
   */
  unit?: "mg/day";
}

/** AnalysisMetricNutrientCholesterolMgV2 */
export interface AnalysisMetricNutrientCholesterolMgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "monitor_only"
   */
  direction?: "monitor_only";
  /**
   * Metric Key
   * @default "nutrient:cholesterol_mg"
   */
  metric_key?: "nutrient:cholesterol_mg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mg/day"
   */
  unit?: "mg/day";
}

/** AnalysisMetricNutrientFiberGV2 */
export interface AnalysisMetricNutrientFiberGV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:fiber_g"
   */
  metric_key?: "nutrient:fiber_g";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricNutrientFolateDfeMcgV2 */
export interface AnalysisMetricNutrientFolateDfeMcgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:folate_dfe_mcg"
   */
  metric_key?: "nutrient:folate_dfe_mcg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mcg/day"
   */
  unit?: "mcg/day";
}

/** AnalysisMetricNutrientIodineMcgV2 */
export interface AnalysisMetricNutrientIodineMcgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:iodine_mcg"
   */
  metric_key?: "nutrient:iodine_mcg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mcg/day"
   */
  unit?: "mcg/day";
}

/** AnalysisMetricNutrientIronMgV2 */
export interface AnalysisMetricNutrientIronMgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:iron_mg"
   */
  metric_key?: "nutrient:iron_mg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mg/day"
   */
  unit?: "mg/day";
}

/** AnalysisMetricNutrientMagnesiumMgV2 */
export interface AnalysisMetricNutrientMagnesiumMgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:magnesium_mg"
   */
  metric_key?: "nutrient:magnesium_mg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mg/day"
   */
  unit?: "mg/day";
}

/** AnalysisMetricNutrientPotassiumMgV2 */
export interface AnalysisMetricNutrientPotassiumMgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:potassium_mg"
   */
  metric_key?: "nutrient:potassium_mg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mg/day"
   */
  unit?: "mg/day";
}

/** AnalysisMetricNutrientSaturatedFatGV2 */
export interface AnalysisMetricNutrientSaturatedFatGV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "maximum"
   */
  direction?: "maximum";
  /**
   * Metric Key
   * @default "nutrient:saturated_fat_g"
   */
  metric_key?: "nutrient:saturated_fat_g";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricNutrientSeleniumMcgV2 */
export interface AnalysisMetricNutrientSeleniumMcgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:selenium_mcg"
   */
  metric_key?: "nutrient:selenium_mcg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mcg/day"
   */
  unit?: "mcg/day";
}

/** AnalysisMetricNutrientSodiumMgV2 */
export interface AnalysisMetricNutrientSodiumMgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "maximum"
   */
  direction?: "maximum";
  /**
   * Metric Key
   * @default "nutrient:sodium_mg"
   */
  metric_key?: "nutrient:sodium_mg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mg/day"
   */
  unit?: "mg/day";
}

/** AnalysisMetricNutrientTransFatGV2 */
export interface AnalysisMetricNutrientTransFatGV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "maximum"
   */
  direction?: "maximum";
  /**
   * Metric Key
   * @default "nutrient:trans_fat_g"
   */
  metric_key?: "nutrient:trans_fat_g";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "g/day"
   */
  unit?: "g/day";
}

/** AnalysisMetricNutrientVitaminARaeMcgV2 */
export interface AnalysisMetricNutrientVitaminARaeMcgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:vitamin_a_rae_mcg"
   */
  metric_key?: "nutrient:vitamin_a_rae_mcg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mcg/day"
   */
  unit?: "mcg/day";
}

/** AnalysisMetricNutrientVitaminB12McgV2 */
export interface AnalysisMetricNutrientVitaminB12McgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:vitamin_b12_mcg"
   */
  metric_key?: "nutrient:vitamin_b12_mcg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mcg/day"
   */
  unit?: "mcg/day";
}

/** AnalysisMetricNutrientZincMgV2 */
export interface AnalysisMetricNutrientZincMgV2 {
  /**
   * Aggregation
   * @default "average_numeric_days"
   */
  aggregation?: "average_numeric_days";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "minimum"
   */
  direction?: "minimum";
  /**
   * Metric Key
   * @default "nutrient:zinc_mg"
   */
  metric_key?: "nutrient:zinc_mg";
  /**
   * Metric Kind
   * @default "daily_average"
   */
  metric_kind?: "daily_average";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "mg/day"
   */
  unit?: "mg/day";
}

/** AnalysisMetricProteinSourceDiversityCountV2 */
export interface AnalysisMetricProteinSourceDiversityCountV2 {
  /**
   * Aggregation
   * @default "distinct_source_count"
   */
  aggregation?: "distinct_source_count";
  comparison: AnalysisComparisonV2;
  contributors: AnalysisContributorsV2;
  current: PeriodMetricEvidenceV2;
  /**
   * Direction
   * @default "monitor_only"
   */
  direction?: "monitor_only";
  /**
   * Metric Key
   * @default "protein:source_diversity_count"
   */
  metric_key?: "protein:source_diversity_count";
  /**
   * Metric Kind
   * @default "diversity_count"
   */
  metric_kind?: "diversity_count";
  persistence: AnalysisPersistenceV2;
  previous: PeriodMetricEvidenceV2;
  target: AnalysisMetricTargetV2 | null;
  /**
   * Unit
   * @default "sources/7d"
   */
  unit?: "sources/7d";
}

/** AnalysisMetricTargetV1 */
export interface AnalysisMetricTargetV1 {
  /** Lower */
  lower?: number | null;
  /** Source Plan Ids */
  source_plan_ids: string[];
  /** Type */
  type: "minimum" | "maximum" | "range";
  /** Upper */
  upper?: number | null;
  /** Value */
  value?: number | null;
}

/** AnalysisMetricTargetV2 */
export interface AnalysisMetricTargetV2 {
  /** Lower */
  lower?: number | null;
  /** Source Plan Ids */
  source_plan_ids: string[];
  /** Type */
  type: "minimum" | "maximum" | "range";
  /** Upper */
  upper?: number | null;
  /** Value */
  value?: number | null;
}

/** AnalysisPersistenceV2 */
export interface AnalysisPersistenceV2 {
  /**
   * Kind
   * @default "same_direction_two_period"
   */
  kind?: "same_direction_two_period";
  /** Qualifies */
  qualifies: boolean;
  /** Reason */
  reason:
    | "qualified"
    | "current_not_qualifying"
    | "previous_not_qualifying"
    | "insufficient_complete_days"
    | "insufficient_coverage"
    | "target_changed"
    | "version_incompatible"
    | "stale_evidence"
    | "missing_previous";
}

/** AnalysisSourceVersionBundleV2 */
export interface AnalysisSourceVersionBundleV2 {
  /** Analysis Rules Version */
  analysis_rules_version: "w3-analysis-2.0.0";
  /** Calculation Engine Version */
  calculation_engine_version: "2.0.0";
  /**
   * Content Hash
   * @pattern ^[0-9a-f]{64}$
   */
  content_hash: string;
  /** Food Group Rules Version */
  food_group_rules_version: "1.0.0";
  /** Nutrition Registry Version */
  nutrition_registry_version: "3.0.0";
  /**
   * Rules Manifest Hash
   * @pattern ^[0-9a-f]{64}$
   */
  rules_manifest_hash: string;
  /** Snapshot Schema Versions */
  snapshot_schema_versions: any;
  /**
   * Source Input Hash
   * @pattern ^[0-9a-f]{64}$
   */
  source_input_hash: string;
  /** Source Reliability Rules Version */
  source_reliability_rules_version: "1.0.0";
  /** Status Evidence Version */
  status_evidence_version: 1;
}

/** AnalysisStaleReasonCountsV1 */
export interface AnalysisStaleReasonCountsV1 {
  /**
   * Day Reopened
   * @min 0
   */
  day_reopened: number;
  /**
   * Day Version Changed
   * @min 0
   */
  day_version_changed: number;
  /**
   * Source Snapshot Corrected
   * @min 0
   */
  source_snapshot_corrected: number;
  /**
   * Source Version Unsupported
   * @min 0
   */
  source_version_unsupported: number;
  /**
   * Target Source Changed
   * @min 0
   */
  target_source_changed: number;
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

/** BehaviorGoalAcceptCommandV1 */
export interface BehaviorGoalAcceptCommandV1 {
  /** Event */
  event: "accept";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
  /** Note */
  note?: string | null;
  /** Reminder Preference */
  reminder_preference?: "enabled" | "disabled" | null;
  /** Scheduled Day Mask */
  scheduled_day_mask?: number[] | null;
  /** Weekly Target Count */
  weekly_target_count?: number | null;
}

/** BehaviorGoalChangeCommandV1 */
export interface BehaviorGoalChangeCommandV1 {
  /** Change Reason */
  change_reason?: "owner_requested" | "evidence_superseded" | null;
  /** Event */
  event: "change";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
  /** Note */
  note?: string | null;
  /** Reminder Preference */
  reminder_preference?: "enabled" | "disabled" | null;
  /** Scheduled Day Mask */
  scheduled_day_mask?: number[] | null;
  /** Weekly Target Count */
  weekly_target_count?: number | null;
}

/** BehaviorGoalCommandResponseV1 */
export interface BehaviorGoalCommandResponseV1 {
  goal: BehaviorGoalResponseV1;
  previous_goal?: BehaviorGoalResponseV1 | null;
  recommendation: WeeklyPriorityResultV1 | null;
  /** Result */
  result:
    | "accepted"
    | "edited"
    | "deferred"
    | "rejected"
    | "changed"
    | "change_available"
    | "paused"
    | "resumed"
    | "ended"
    | "repeated"
    | "reduced_and_repeated";
}

/** BehaviorGoalCommandV1 */
export type BehaviorGoalCommandV1 =
  | ({
      event: "accept";
    } & BehaviorGoalAcceptCommandV1)
  | ({
      event: "change";
    } & BehaviorGoalChangeCommandV1)
  | ({
      event: "defer";
    } & BehaviorGoalDeferCommandV1)
  | ({
      event: "edit";
    } & BehaviorGoalEditCommandV1)
  | ({
      event: "end";
    } & BehaviorGoalEndCommandV1)
  | ({
      event: "pause";
    } & BehaviorGoalPauseCommandV1)
  | ({
      event: "reject";
    } & BehaviorGoalRejectCommandV1)
  | ({
      event: "repeat";
    } & BehaviorGoalRepeatCommandV1)
  | ({
      event: "resume";
    } & BehaviorGoalResumeCommandV1);

/** BehaviorGoalCurrentResponseV1 */
export interface BehaviorGoalCurrentResponseV1 {
  goal: BehaviorGoalResponseV1 | null;
  /** Goal Unavailable Reason */
  goal_unavailable_reason?: "action_not_observable" | null;
  recommendation: WeeklyPriorityResultV1 | null;
}

/** BehaviorGoalDeferCommandV1 */
export interface BehaviorGoalDeferCommandV1 {
  /** Event */
  event: "defer";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
}

/** BehaviorGoalEditCommandV1 */
export interface BehaviorGoalEditCommandV1 {
  /** Event */
  event: "edit";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
  /** Note */
  note?: string | null;
  /** Reminder Preference */
  reminder_preference?: "enabled" | "disabled" | null;
  /** Scheduled Day Mask */
  scheduled_day_mask?: number[] | null;
  /** Weekly Target Count */
  weekly_target_count?: number | null;
}

/** BehaviorGoalEndCommandV1 */
export interface BehaviorGoalEndCommandV1 {
  /** Event */
  event: "end";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
  /** Note */
  note?: string | null;
  /** Reason */
  reason?:
    | "not_relevant"
    | "too_difficult"
    | "prefer_other"
    | "pause_tracking"
    | "other"
    | null;
}

/** BehaviorGoalHistoryItemV1 */
export interface BehaviorGoalHistoryItemV1 {
  /** Event Type */
  event_type:
    | "offered"
    | "accept"
    | "edit"
    | "defer"
    | "reject"
    | "change"
    | "changed"
    | "pause"
    | "resume"
    | "end"
    | "completed"
    | "archive"
    | "evidence_reopened"
    | "progress_updated"
    | "historical_evidence_changed"
    | "finalized_completed"
    | "finalized_incomplete"
    | "repeated_from_previous_window";
  /** From State */
  from_state:
    | "offered"
    | "deferred"
    | "active"
    | "paused"
    | "completed"
    | "incomplete"
    | "rejected"
    | "ended"
    | "archived"
    | null;
  /**
   * Goal Id
   * @format uuid
   */
  goal_id: string;
  /**
   * Goal Version
   * @min 1
   */
  goal_version: number;
  /**
   * History Id
   * @format uuid
   */
  history_id: string;
  /**
   * Occurred At
   * @format date-time
   */
  occurred_at: string;
  /** Previous Goal Id */
  previous_goal_id: string | null;
  /** Reason */
  reason: string | null;
  /**
   * Root Goal Id
   * @format uuid
   */
  root_goal_id: string;
  /**
   * Schema Version
   * @default 1
   */
  schema_version?: 1;
  /**
   * Sequence Number
   * @min 1
   */
  sequence_number: number;
  snapshot: BehaviorGoalHistorySnapshotV1;
  /** To State */
  to_state:
    | "offered"
    | "deferred"
    | "active"
    | "paused"
    | "completed"
    | "incomplete"
    | "rejected"
    | "ended"
    | "archived";
}

/** BehaviorGoalHistoryPageV1 */
export interface BehaviorGoalHistoryPageV1 {
  /** Items */
  items: BehaviorGoalHistoryItemV1[];
  /** Next Cursor */
  next_cursor: string | null;
}

/** BehaviorGoalHistorySnapshotV1 */
export interface BehaviorGoalHistorySnapshotV1 {
  /** Accepted At */
  accepted_at: string | null;
  /** Action Copy Ar */
  action_copy_ar: string;
  /** Action Key */
  action_key: string;
  /** Analysis Rules Version */
  analysis_rules_version: string;
  /** Archived At */
  archived_at: string | null;
  /** Changed At */
  changed_at: string | null;
  /** Completed At */
  completed_at: string | null;
  /** Copy Version */
  copy_version: string;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /** Deferred At */
  deferred_at: string | null;
  /** Deferred Until */
  deferred_until: string | null;
  /** Ended At */
  ended_at: string | null;
  /**
   * Goal Id
   * @format uuid
   */
  goal_id: string;
  /** Goal Trackability */
  goal_trackability: "trackable";
  /** Goal Unavailable Reason */
  goal_unavailable_reason?: null;
  /** Informational Copy Ar */
  informational_copy_ar?: string | null;
  /** Last Progress Analysis Id */
  last_progress_analysis_id: string | null;
  /** Last Progress Analysis Revision */
  last_progress_analysis_revision?: number | null;
  /** Last Progress Analysis Revision Id */
  last_progress_analysis_revision_id: string | null;
  /**
   * Offered At
   * @format date-time
   */
  offered_at: string;
  /** Owner Note */
  owner_note?: string | null;
  /** Paused At */
  paused_at: string | null;
  /** Previous Goal Id */
  previous_goal_id: string | null;
  progress: BehaviorGoalProgressV1;
  /**
   * Progress Revision
   * @min 1
   */
  progress_revision: number;
  /**
   * Recommendation Id
   * @format uuid
   */
  recommendation_id: string;
  /** Rejected At */
  rejected_at: string | null;
  /** Reminder Preference */
  reminder_preference: "enabled" | "disabled";
  /** Resumed At */
  resumed_at: string | null;
  /** Reviewed At */
  reviewed_at: string | null;
  /**
   * Root Goal Id
   * @format uuid
   */
  root_goal_id: string;
  /** Rule Key */
  rule_key: string;
  /** Rules Version */
  rules_version: string;
  /** Scheduled Day Mask */
  scheduled_day_mask: number[];
  /**
   * Sequence Number
   * @min 1
   */
  sequence_number: number;
  /**
   * Source Analysis Id
   * @format uuid
   */
  source_analysis_id: string;
  /**
   * Source Analysis Revision
   * @min 1
   */
  source_analysis_revision: number;
  /**
   * Source Analysis Revision Id
   * @format uuid
   */
  source_analysis_revision_id: string;
  /** Source Versions */
  source_versions: Record<string, any>;
  /** State */
  state:
    | "offered"
    | "deferred"
    | "active"
    | "paused"
    | "completed"
    | "incomplete"
    | "rejected"
    | "ended"
    | "archived";
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /**
   * Version
   * @min 1
   */
  version: number;
  /**
   * Weekly Target Count
   * @min 1
   * @max 7
   */
  weekly_target_count: number;
  /**
   * Window End
   * @format date
   */
  window_end: string;
  /**
   * Window Start
   * @format date
   */
  window_start: string;
}

/** BehaviorGoalPauseCommandV1 */
export interface BehaviorGoalPauseCommandV1 {
  /** Event */
  event: "pause";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
  /** Note */
  note?: string | null;
  /** Reason */
  reason?:
    | "not_relevant"
    | "too_difficult"
    | "prefer_other"
    | "pause_tracking"
    | "other"
    | null;
}

/** BehaviorGoalProgressV1 */
export interface BehaviorGoalProgressV1 {
  /**
   * As Of Diary Date
   * @format date
   */
  as_of_diary_date: string;
  /** Calculation Rules Version */
  calculation_rules_version: string;
  /**
   * Complete Day Count
   * @min 0
   * @max 7
   */
  complete_day_count: number;
  /**
   * Last Recomputed At
   * @format date-time
   */
  last_recomputed_at: string;
  /**
   * Partial Day Count
   * @min 0
   * @max 7
   */
  partial_day_count: number;
  /**
   * Progress Count
   * @min 0
   * @max 7
   */
  progress_count: number;
  /** Progress Percent */
  progress_percent?: number | null;
  /** Source Day Versions */
  source_day_versions: Record<string, number>;
  /** Status */
  status:
    | "unknown"
    | "in_progress"
    | "achieved"
    | "not_yet_reached"
    | "insufficient_evidence";
  /**
   * Target Count
   * @min 1
   * @max 7
   */
  target_count: number;
  /**
   * Unregistered Day Count
   * @min 0
   * @max 7
   */
  unregistered_day_count: number;
  /**
   * Window End
   * @format date
   */
  window_end: string;
  /**
   * Window Start
   * @format date
   */
  window_start: string;
}

/** BehaviorGoalRejectCommandV1 */
export interface BehaviorGoalRejectCommandV1 {
  /** Event */
  event: "reject";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
  /** Note */
  note?: string | null;
  /** Reason */
  reason?:
    | "not_relevant"
    | "too_difficult"
    | "prefer_other"
    | "pause_tracking"
    | "other"
    | null;
}

/** BehaviorGoalRepeatCommandV1 */
export interface BehaviorGoalRepeatCommandV1 {
  /** Event */
  event: "repeat";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
  /** Repeat Mode */
  repeat_mode: "same" | "reduce";
  /** Weekly Target Count */
  weekly_target_count?: number | null;
}

/** BehaviorGoalResponseV1 */
export interface BehaviorGoalResponseV1 {
  /** Accepted At */
  accepted_at: string | null;
  /** Action Key */
  action_key: string;
  /** Allowed Actions */
  allowed_actions: (
    | "accept"
    | "edit"
    | "defer"
    | "reject"
    | "change"
    | "pause"
    | "resume"
    | "end"
    | "repeat"
    | "reduce"
  )[];
  /** Archived At */
  archived_at: string | null;
  calendar: CalendarAuthorityResponse;
  /** Changed At */
  changed_at: string | null;
  /** Completed At */
  completed_at: string | null;
  /**
   * Created At
   * @format date-time
   */
  created_at: string;
  /** Deferred At */
  deferred_at: string | null;
  /** Deferred Until */
  deferred_until: string | null;
  /** Ended At */
  ended_at: string | null;
  /** Etag */
  etag: string;
  /**
   * Goal Id
   * @format uuid
   */
  goal_id: string;
  /**
   * Offered At
   * @format date-time
   */
  offered_at: string;
  /** Owner Note */
  owner_note?: string | null;
  /** Paused At */
  paused_at: string | null;
  /** Previous Goal Id */
  previous_goal_id: string | null;
  progress: BehaviorGoalProgressV1;
  /** Rejected At */
  rejected_at: string | null;
  /** Reminder Preference */
  reminder_preference: "enabled" | "disabled";
  /** Resumed At */
  resumed_at: string | null;
  /** Reviewed At */
  reviewed_at: string | null;
  /**
   * Root Goal Id
   * @format uuid
   */
  root_goal_id: string;
  /** Rule Key */
  rule_key: string;
  /** Scheduled Day Mask */
  scheduled_day_mask: number[];
  /**
   * Schema Version
   * @default 1
   */
  schema_version?: 1;
  /**
   * Sequence Number
   * @min 1
   */
  sequence_number: number;
  /** Source Copy Version */
  source_copy_version: string;
  /**
   * Source Recommendation Id
   * @format uuid
   */
  source_recommendation_id: string;
  /** Source Rules Version */
  source_rules_version: string;
  /** State */
  state:
    | "offered"
    | "deferred"
    | "active"
    | "paused"
    | "completed"
    | "incomplete"
    | "rejected"
    | "ended"
    | "archived";
  /**
   * Updated At
   * @format date-time
   */
  updated_at: string;
  /**
   * Version
   * @min 1
   */
  version: number;
  /**
   * Weekly Target Count
   * @min 1
   * @max 7
   */
  weekly_target_count: number;
  /**
   * Window End
   * @format date
   */
  window_end: string;
  /**
   * Window Start
   * @format date
   */
  window_start: string;
}

/** BehaviorGoalResumeCommandV1 */
export interface BehaviorGoalResumeCommandV1 {
  /** Event */
  event: "resume";
  /**
   * Expected Version
   * @min 1
   */
  expected_version: number;
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

/** ContributionDataStatus */
export type ContributionDataStatus = "known" | "estimated";

/** DaySummary */
export interface DaySummary {
  /** Analysis Eligible */
  analysis_eligible: boolean;
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
  /** Analysis Eligible */
  analysis_eligible: boolean;
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
 * Active NOVA-free Food response contract.
 */
export interface FoodResponseV3 {
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

/** NutritionAnalysisMonitoringResponseV1 */
export interface NutritionAnalysisMonitoringResponseV1 {
  complete_day_band_counts: AnalysisCompleteDayBandCountsV1;
  coverage_band_counts: AnalysisCoverageBandCountsV1;
  /** Iso Week */
  iso_week: string;
  latency_band_counts: AnalysisLatencyBandCountsV1;
  stale_reason_counts: AnalysisStaleReasonCountsV1;
  /** Status Counts */
  status_counts: Record<string, number>;
  /**
   * Total Count
   * @min 0
   */
  total_count: number;
  /** Version Counts */
  version_counts: Record<string, number>;
}

/** NutritionBasis */
export type NutritionBasis = "per_100g" | "per_100ml";

/** NutritionPatternAnalysisHistoryItemV2 */
export interface NutritionPatternAnalysisHistoryItemV2 {
  /** Analysis Rules Version */
  analysis_rules_version: "w3-analysis-2.0.0";
  /**
   * As Of Diary Date
   * @format date
   */
  as_of_diary_date: string;
  /**
   * Complete Day Count
   * @min 0
   * @max 7
   */
  complete_day_count: number;
  /**
   * Etag
   * @pattern ^"analysis-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}-r[1-9][0-9]*"$
   */
  etag: string;
  /**
   * Finalized At
   * @format date-time
   */
  finalized_at: string;
  /**
   * Generated At
   * @format date-time
   */
  generated_at: string;
  /** Lifecycle Status */
  lifecycle_status: "current" | "stale" | "superseded";
  /**
   * Period End
   * @format date
   */
  period_end: string;
  /**
   * Period Start
   * @format date
   */
  period_start: string;
  /**
   * Previous Complete Day Count
   * @min 0
   * @max 7
   */
  previous_complete_day_count: number;
  /**
   * Previous Period End
   * @format date
   */
  previous_period_end: string;
  /**
   * Previous Period Start
   * @format date
   */
  previous_period_start: string;
  /**
   * Source Analysis Id
   * @format uuid
   */
  source_analysis_id: string;
  /**
   * Source Analysis Revision
   * @min 1
   */
  source_analysis_revision: number;
}

/** NutritionPatternAnalysisHistoryPageV2 */
export interface NutritionPatternAnalysisHistoryPageV2 {
  /** Items */
  items: NutritionPatternAnalysisHistoryItemV2[];
  /** Next Cursor */
  next_cursor: string | null;
}

/** NutritionPatternAnalysisResponseV2 */
export interface NutritionPatternAnalysisResponseV2 {
  /**
   * As Of Diary Date
   * @format date
   */
  as_of_diary_date: string;
  /**
   * Complete Day Count
   * @min 0
   * @max 7
   */
  complete_day_count: number;
  /**
   * Etag
   * @pattern ^"analysis-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}-r[1-9][0-9]*"$
   */
  etag: string;
  /**
   * Finalized At
   * @format date-time
   */
  finalized_at: string;
  /**
   * Generated At
   * @format date-time
   */
  generated_at: string;
  /** Lifecycle Status */
  lifecycle_status: "current" | "stale" | "superseded";
  /**
   * Metric Summaries
   * @maxItems 32
   * @minItems 32
   */
  metric_summaries: [
    AnalysisMetricEnergyCaloriesKcalPerDayV2,
    AnalysisMetricGroupDairyFortifiedServingsPerDayV2,
    AnalysisMetricGroupFruitVegetableGPerDayV2,
    AnalysisMetricGroupLegumesServingsPerPeriodV2,
    AnalysisMetricGroupNutsSeedsServingsPerPeriodV2,
    AnalysisMetricGroupOmega3SeafoodServingsPerPeriodV2,
    AnalysisMetricGroupProcessedMeatOccurrenceDaysV2,
    AnalysisMetricGroupRedMeatGPerPeriodV2,
    AnalysisMetricGroupSeafoodServingsPerPeriodV2,
    AnalysisMetricGroupSugarSweetenedBeverageOccurrenceDaysV2,
    AnalysisMetricGroupSweetsOccurrenceDaysV2,
    AnalysisMetricGroupWholeGrainSharePercentV2,
    AnalysisMetricMacroCarbGPerDayV2,
    AnalysisMetricMacroFatGPerDayV2,
    AnalysisMetricMacroProteinGPerDayV2,
    AnalysisMetricNutrientAddedSugarGV2,
    AnalysisMetricNutrientCalciumMgV2,
    AnalysisMetricNutrientCholesterolMgV2,
    AnalysisMetricNutrientFiberGV2,
    AnalysisMetricNutrientFolateDfeMcgV2,
    AnalysisMetricNutrientIodineMcgV2,
    AnalysisMetricNutrientIronMgV2,
    AnalysisMetricNutrientMagnesiumMgV2,
    AnalysisMetricNutrientPotassiumMgV2,
    AnalysisMetricNutrientSaturatedFatGV2,
    AnalysisMetricNutrientSeleniumMcgV2,
    AnalysisMetricNutrientSodiumMgV2,
    AnalysisMetricNutrientTransFatGV2,
    AnalysisMetricNutrientVitaminARaeMcgV2,
    AnalysisMetricNutrientVitaminB12McgV2,
    AnalysisMetricNutrientZincMgV2,
    AnalysisMetricProteinSourceDiversityCountV2,
  ];
  /**
   * Period End
   * @format date
   */
  period_end: string;
  /**
   * Period Start
   * @format date
   */
  period_start: string;
  /**
   * Previous Complete Day Count
   * @min 0
   * @max 7
   */
  previous_complete_day_count: number;
  /**
   * Previous Period End
   * @format date
   */
  previous_period_end: string;
  /**
   * Previous Period Start
   * @format date
   */
  previous_period_start: string;
  priority_input: WeeklyPriorityAnalysisInputV2;
  /**
   * Source Analysis Id
   * @format uuid
   */
  source_analysis_id: string;
  /**
   * Source Analysis Revision
   * @min 1
   */
  source_analysis_revision: number;
  source_versions: AnalysisSourceVersionBundleV2;
  /** Stale Reasons */
  stale_reasons: (
    | "day_reopened"
    | "day_version_changed"
    | "target_source_changed"
    | "source_snapshot_corrected"
    | "source_version_unsupported"
  )[];
}

/** NutritionRegistryResponse */
export interface NutritionRegistryResponse {
  /** Analysis Metrics */
  analysis_metrics: Record<string, string>[];
  /** Analysis Rules Status */
  analysis_rules_status: "active";
  /** Analysis Rules Version */
  analysis_rules_version: "w3-analysis-2.0.0";
  /** Baked Good Type Definitions */
  baked_good_type_definitions: RegistryLabelDefinition[];
  /** Calculation Engine Version */
  calculation_engine_version: "2.0.0";
  /** Calculation Policy */
  calculation_policy: Record<string, any>;
  /** Food Categories */
  food_categories: string[];
  /** Food Category Definitions */
  food_category_definitions: RegistryLabelDefinition[];
  /** Food Group Definitions */
  food_group_definitions: RegistryFoodGroupDefinition[];
  /** Food Group Rules Version */
  food_group_rules_version: "1.0.0";
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
  /** Nutrients */
  nutrients: RegistryNutrientDefinition[];
  /** Nutrition Registry Version */
  nutrition_registry_version: "3.0.0";
  /** Registry Schema Version */
  registry_schema_version: 3;
  /** Reliability Levels */
  reliability_levels: RegistryLabelDefinition[];
  /** Rules Manifest Hash */
  rules_manifest_hash: string;
  /** Snapshot Schema Version */
  snapshot_schema_version: 4;
  /** Source Reliability Rules Version */
  source_reliability_rules_version: "1.0.0";
  /** Source Types */
  source_types: RegistrySourceTypeDefinition[];
  /** Target Types */
  target_types: string[];
  /** Traits */
  traits: RegistryLabelDefinition[];
  /** Weekly Priority Copy Version */
  weekly_priority_copy_version: "w3-priority-ar-1.1.0";
  /** Weekly Priority Rules */
  weekly_priority_rules: Record<string, any>[];
  /** Weekly Priority Rules Version */
  weekly_priority_rules_version: "w3-priority-1.1.0";
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

/** OpaqueEvidenceRefV1 */
export interface OpaqueEvidenceRefV1 {
  /**
   * Diary Date
   * @format date
   */
  diary_date: string;
  /**
   * Source Ref
   * @format uuid
   */
  source_ref: string;
  /**
   * Source Version
   * @minLength 1
   */
  source_version: string;
}

/** OpaqueEvidenceRefV2 */
export interface OpaqueEvidenceRefV2 {
  /**
   * Diary Date
   * @format date
   */
  diary_date: string;
  /**
   * Source Ref
   * @format uuid
   */
  source_ref: string;
  /**
   * Source Version
   * @minLength 1
   */
  source_version: string;
}

/** PeriodMetricEvidenceV2 */
export interface PeriodMetricEvidenceV2 {
  /** Amount Qualifier */
  amount_qualifier: "exact" | "at_least" | "unavailable";
  /**
   * Complete Day Count
   * @min 0
   * @max 7
   */
  complete_day_count: number;
  /** Confidence */
  confidence: "strong" | "limited" | "unavailable";
  /** Coverage Percent */
  coverage_percent?: number | null;
  /** Evidence Refs */
  evidence_refs: OpaqueEvidenceRefV2[];
  /**
   * Known Entry Count
   * @min 0
   */
  known_entry_count: number;
  /**
   * Numeric Day Count
   * @min 0
   * @max 7
   */
  numeric_day_count: number;
  /** Status */
  status:
    | "below_target"
    | "at_target"
    | "within_target"
    | "above_target"
    | "observed"
    | "target_incompatible"
    | "unavailable";
  /**
   * Total Entry Count
   * @min 0
   */
  total_entry_count: number;
  /** Value */
  value: number | null;
  /** Value State */
  value_state: "known" | "explicit_zero" | "unknown";
}

/** Plan033ErrorDetailV1 */
export interface Plan033ErrorDetailV1 {
  /** Code */
  code:
    | "VALIDATION_ERROR"
    | "INVALID_IDEMPOTENCY_KEY"
    | "RESOURCE_NOT_FOUND"
    | "GOAL_STATE_CONFLICT"
    | "GOAL_VERSION_CONFLICT"
    | "IDEMPOTENCY_KEY_REUSED"
    | "PRIMARY_GOAL_EXISTS"
    | "GOAL_REPEAT_PRIORITY_CONFLICT"
    | "PRIORITY_SOURCE_STALE"
    | "PRIORITY_SOURCE_SUPERSEDED"
    | "UNSUPPORTED_PRIORITY_VERSION"
    | "FEATURE_DISABLED"
    | "PRIORITY_EVIDENCE_UNAVAILABLE"
    | "GOAL_WRITE_FAILED";
  /** Details */
  details: Record<string, any>;
  /** Message Ar */
  message_ar: string;
  /**
   * Request Id
   * @format uuid
   */
  request_id: string;
}

/** Plan033ErrorResponseV1 */
export interface Plan033ErrorResponseV1 {
  error: Plan033ErrorDetailV1;
}

/** PrincipalRole */
export type PrincipalRole = "user" | "admin";

/** PrincipalStatus */
export type PrincipalStatus = "active" | "disabled";

/** PriorityV1 */
export interface PriorityV1 {
  /**
   * Action Ar
   * @minLength 1
   */
  action_ar: string;
  /**
   * Action Key
   * @minLength 1
   */
  action_key: string;
  /** Action Mode */
  action_mode: "add" | "replace" | "review";
  /** Category */
  category: "limit" | "positive" | "micronutrient";
  /**
   * Complete Day Count
   * @min 4
   * @max 7
   */
  complete_day_count: number;
  /**
   * Confidence
   * @default "strong"
   */
  confidence?: "strong";
  /** Conflict Decisions */
  conflict_decisions: string[];
  /** Copy Version */
  copy_version: "w3-priority-ar-1.1.0";
  /**
   * Coverage Percent
   * @min 75
   * @max 100
   */
  coverage_percent: number;
  /** Evidence Refs */
  evidence_refs: OpaqueEvidenceRefV1[];
  /** Facts Used */
  facts_used: WeeklyPriorityFactV1[];
  /** Goal Trackability */
  goal_trackability: "trackable" | "informational_only";
  /** Goal Unavailable Copy Ar */
  goal_unavailable_copy_ar: string | null;
  /** Goal Unavailable Reason */
  goal_unavailable_reason: "action_not_observable" | null;
  /** Rank */
  rank: "main" | "secondary";
  /**
   * Reason Ar
   * @minLength 1
   */
  reason_ar: string;
  /**
   * Rule Key
   * @minLength 1
   */
  rule_key: string;
  /** Rules Version */
  rules_version: "w3-priority-1.1.0";
  /**
   * Title Ar
   * @minLength 1
   */
  title_ar: string;
}

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

/** TargetPlanAnalysisRefV1 */
export interface TargetPlanAnalysisRefV1 {
  /**
   * Calculation Document Schema Version
   * @min 1
   */
  calculation_document_schema_version: number;
  /**
   * Calculation Engine Version
   * @minLength 1
   */
  calculation_engine_version: string;
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
  /**
   * Nutrition Registry Version
   * @minLength 1
   */
  nutrition_registry_version: string;
  /** Safety Outcome */
  safety_outcome:
    | "normal"
    | "specialist_review_required"
    | "very_low_energy_blocked";
  /**
   * Target Document Hash
   * @pattern ^[0-9a-f]{64}$
   */
  target_document_hash: string;
}

/**
 * TargetPlanAnalysisRefV2
 * Pinned Target Plan provenance; compatibility is evaluated, not rewritten.
 */
export interface TargetPlanAnalysisRefV2 {
  /**
   * Calculation Document Schema Version
   * @min 1
   */
  calculation_document_schema_version: number;
  /**
   * Calculation Engine Version
   * @minLength 1
   */
  calculation_engine_version: string;
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
  /**
   * Nutrition Registry Version
   * @minLength 1
   */
  nutrition_registry_version: string;
  /** Safety Outcome */
  safety_outcome:
    | "normal"
    | "specialist_review_required"
    | "very_low_energy_blocked";
  /**
   * Target Document Hash
   * @pattern ^[0-9a-f]{64}$
   */
  target_document_hash: string;
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

/** WeeklyPriorityAnalysisInputV2 */
export interface WeeklyPriorityAnalysisInputV2 {
  /** Analysis Rules Version */
  analysis_rules_version: "w3-analysis-2.0.0";
  /**
   * As Of Diary Date
   * @format date
   */
  as_of_diary_date: string;
  /** Calendar Timezone */
  calendar_timezone: "Asia/Riyadh";
  /**
   * Days
   * @maxItems 7
   * @minItems 7
   */
  days: AnalysisDayFactV2[];
  /** Food Group Rules Version */
  food_group_rules_version: "1.0.0";
  /**
   * Generated At
   * @format date-time
   */
  generated_at: string;
  /**
   * Interface Version
   * @default 2
   */
  interface_version?: 2;
  /**
   * Metric Facts
   * @maxItems 32
   * @minItems 32
   */
  metric_facts: [
    AnalysisMetricEnergyCaloriesKcalPerDayV2,
    AnalysisMetricGroupDairyFortifiedServingsPerDayV2,
    AnalysisMetricGroupFruitVegetableGPerDayV2,
    AnalysisMetricGroupLegumesServingsPerPeriodV2,
    AnalysisMetricGroupNutsSeedsServingsPerPeriodV2,
    AnalysisMetricGroupOmega3SeafoodServingsPerPeriodV2,
    AnalysisMetricGroupProcessedMeatOccurrenceDaysV2,
    AnalysisMetricGroupRedMeatGPerPeriodV2,
    AnalysisMetricGroupSeafoodServingsPerPeriodV2,
    AnalysisMetricGroupSugarSweetenedBeverageOccurrenceDaysV2,
    AnalysisMetricGroupSweetsOccurrenceDaysV2,
    AnalysisMetricGroupWholeGrainSharePercentV2,
    AnalysisMetricMacroCarbGPerDayV2,
    AnalysisMetricMacroFatGPerDayV2,
    AnalysisMetricMacroProteinGPerDayV2,
    AnalysisMetricNutrientAddedSugarGV2,
    AnalysisMetricNutrientCalciumMgV2,
    AnalysisMetricNutrientCholesterolMgV2,
    AnalysisMetricNutrientFiberGV2,
    AnalysisMetricNutrientFolateDfeMcgV2,
    AnalysisMetricNutrientIodineMcgV2,
    AnalysisMetricNutrientIronMgV2,
    AnalysisMetricNutrientMagnesiumMgV2,
    AnalysisMetricNutrientPotassiumMgV2,
    AnalysisMetricNutrientSaturatedFatGV2,
    AnalysisMetricNutrientSeleniumMcgV2,
    AnalysisMetricNutrientSodiumMgV2,
    AnalysisMetricNutrientTransFatGV2,
    AnalysisMetricNutrientVitaminARaeMcgV2,
    AnalysisMetricNutrientVitaminB12McgV2,
    AnalysisMetricNutrientZincMgV2,
    AnalysisMetricProteinSourceDiversityCountV2,
  ];
  /** Nutrition Registry Version */
  nutrition_registry_version: "3.0.0";
  /**
   * Period End
   * @format date
   */
  period_end: string;
  /**
   * Period Start
   * @format date
   */
  period_start: string;
  /**
   * Previous Period
   * @maxItems 7
   * @minItems 7
   */
  previous_period: AnalysisDayFactV2[];
  /**
   * Previous Period End
   * @format date
   */
  previous_period_end: string;
  /**
   * Previous Period Start
   * @format date
   */
  previous_period_start: string;
  /**
   * Principal Ref
   * @format uuid
   */
  principal_ref: string;
  /** Safety Flags */
  safety_flags: (
    | "incompatible_target"
    | "incompatible_source_versions"
    | "invalid_day_evidence"
    | "missing_target"
    | "non_finite_source_fact"
    | "profile_specialist_review_required"
    | "stale_evidence"
    | "unsupported_analysis_rules"
    | "unsupported_food_group_rules"
    | "unsupported_registry"
    | "unsupported_snapshot_schema"
    | "very_low_energy_blocked"
  )[];
  /** Snapshot Schema Versions */
  snapshot_schema_versions: any;
  /**
   * Source Analysis Id
   * @format uuid
   */
  source_analysis_id: string;
  /**
   * Source Analysis Revision
   * @min 1
   */
  source_analysis_revision: number;
  /** Target Plan Refs */
  target_plan_refs: TargetPlanAnalysisRefV2[];
}

/** WeeklyPriorityExcludedV1 */
export interface WeeklyPriorityExcludedV1 {
  /** Reason Code */
  reason_code:
    | "lower_rank"
    | "duplicate_evidence"
    | "action_conflict"
    | "addition_replaced"
    | "insufficient_coverage"
    | "insufficient_persistence"
    | "safety_exclusion";
  /** Rule Key */
  rule_key: string;
}

/** WeeklyPriorityFactV1 */
export interface WeeklyPriorityFactV1 {
  /**
   * Comparison
   * @minLength 1
   */
  comparison: string;
  /**
   * Metric Key
   * @minLength 1
   */
  metric_key: string;
  /** Period */
  period: "current" | "previous";
  target: AnalysisMetricTargetV1 | null;
  /**
   * Unit
   * @minLength 1
   */
  unit: string;
  /** Value */
  value: number | null;
}

/** WeeklyPriorityResultV1 */
export interface WeeklyPriorityResultV1 {
  /** Analysis Rules Version */
  analysis_rules_version: string;
  /** Copy Version */
  copy_version: "w3-priority-ar-1.1.0";
  /** Etag */
  etag: string;
  /** Excluded Alternatives */
  excluded_alternatives: WeeklyPriorityExcludedV1[];
  /**
   * Expires At
   * @format date-time
   */
  expires_at: string;
  /** Food Group Rules Version */
  food_group_rules_version: string;
  /**
   * Generated At
   * @format date-time
   */
  generated_at: string;
  main: PriorityV1 | null;
  /** None Reason */
  none_reason:
    | "invalid_analysis_input"
    | "insufficient_complete_days"
    | "insufficient_coverage"
    | "no_eligible_priority"
    | "stale_analysis"
    | "superseded_analysis"
    | "safety_exclusion"
    | "unsupported_version"
    | "rejected_goal_suppression"
    | null;
  /** Nova Rules Version */
  nova_rules_version: string;
  /** Nutrition Registry Version */
  nutrition_registry_version: string;
  /**
   * Period End
   * @format date
   */
  period_end: string;
  /**
   * Period Start
   * @format date
   */
  period_start: string;
  /**
   * Recommendation Id
   * @format uuid
   */
  recommendation_id: string;
  /** Rules Version */
  rules_version: "w3-priority-1.1.0";
  /**
   * Schema Version
   * @default 1
   */
  schema_version?: 1;
  secondary: PriorityV1 | null;
  /** Snapshot Schema Versions */
  snapshot_schema_versions: number[];
  /**
   * Source Analysis Id
   * @format uuid
   */
  source_analysis_id: string;
  /**
   * Source Analysis Revision
   * @min 1
   */
  source_analysis_revision: number;
  /** Status */
  status: "selected" | "none" | "stale" | "superseded" | "safety_suppressed";
  /** Target Plan Refs */
  target_plan_refs: TargetPlanAnalysisRefV1[];
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
   * @tags admin
   * @name MonitoringAdminNutritionAnalysisMonitoringGet
   * @summary Monitoring
   * @request GET:/admin/nutrition-analysis/monitoring
   * @secure
   */
  export namespace MonitoringAdminNutritionAnalysisMonitoringGet {
    export type RequestParams = {};
    export type RequestQuery = {
      /**
       * Iso Week
       * @pattern ^\d{4}-W\d{2}$
       */
      iso_week: string;
    };
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = NutritionAnalysisMonitoringResponseV1;
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

export namespace Progress {
  /**
   * No description
   * @tags nutrition-analysis
   * @name CurrentV2ProgressNutritionAnalysisV2CurrentGet
   * @summary Current V2
   * @request GET:/progress/nutrition-analysis/v2/current
   * @secure
   */
  export namespace CurrentV2ProgressNutritionAnalysisV2CurrentGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = NutritionPatternAnalysisResponseV2;
  }

  /**
   * No description
   * @tags nutrition-analysis
   * @name EvaluateV2ProgressNutritionAnalysisV2EvaluatePost
   * @summary Evaluate V2
   * @request POST:/progress/nutrition-analysis/v2/evaluate
   * @secure
   */
  export namespace EvaluateV2ProgressNutritionAnalysisV2EvaluatePost {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = AnalysisEvaluateCommandV2;
    export type RequestHeaders = {
      /** Idempotency-Key */
      "Idempotency-Key": string;
      /** If-Match */
      "If-Match": string;
    };
    export type ResponseBody = NutritionPatternAnalysisResponseV2;
  }

  /**
   * No description
   * @tags behavior-goals
   * @name GetGoalHistoryProgressBehaviorGoalsHistoryGet
   * @summary Get Goal History
   * @request GET:/progress/behavior-goals/history
   * @secure
   */
  export namespace GetGoalHistoryProgressBehaviorGoalsHistoryGet {
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
    export type ResponseBody = BehaviorGoalHistoryPageV1;
  }

  /**
   * No description
   * @tags behavior-goals
   * @name GetGoalProgressBehaviorGoalsCurrentGet
   * @summary Get Goal
   * @request GET:/progress/behavior-goals/current
   * @secure
   */
  export namespace GetGoalProgressBehaviorGoalsCurrentGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = BehaviorGoalCurrentResponseV1;
  }

  /**
   * No description
   * @tags weekly-priorities
   * @name GetPriorityProgressWeeklyPrioritiesCurrentGet
   * @summary Get Priority
   * @request GET:/progress/weekly-priorities/current
   * @secure
   */
  export namespace GetPriorityProgressWeeklyPrioritiesCurrentGet {
    export type RequestParams = {};
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = WeeklyPriorityResultV1;
  }

  /**
   * No description
   * @tags nutrition-analysis
   * @name HistoryV2ProgressNutritionAnalysisV2HistoryGet
   * @summary History V2
   * @request GET:/progress/nutrition-analysis/v2/history
   * @secure
   */
  export namespace HistoryV2ProgressNutritionAnalysisV2HistoryGet {
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
    export type ResponseBody = NutritionPatternAnalysisHistoryPageV2;
  }

  /**
   * No description
   * @tags behavior-goals
   * @name PostGoalCommandProgressBehaviorGoalsGoalIdCommandsPost
   * @summary Post Goal Command
   * @request POST:/progress/behavior-goals/{goal_id}/commands
   * @secure
   */
  export namespace PostGoalCommandProgressBehaviorGoalsGoalIdCommandsPost {
    export type RequestParams = {
      /**
       * Goal Id
       * @format uuid
       */
      goalId: string;
    };
    export type RequestQuery = {};
    export type RequestBody = BehaviorGoalCommandV1;
    export type RequestHeaders = {
      /** Idempotency-Key */
      "Idempotency-Key": string;
    };
    export type ResponseBody = BehaviorGoalCommandResponseV1;
  }

  /**
   * No description
   * @tags nutrition-analysis
   * @name RevisionV2ProgressNutritionAnalysisV2AnalysisIdRevisionsRevisionGet
   * @summary Revision V2
   * @request GET:/progress/nutrition-analysis/v2/{analysis_id}/revisions/{revision}
   * @secure
   */
  export namespace RevisionV2ProgressNutritionAnalysisV2AnalysisIdRevisionsRevisionGet {
    export type RequestParams = {
      /**
       * Analysis Id
       * @format uuid
       */
      analysisId: string;
      /** Revision */
      revision: number;
    };
    export type RequestQuery = {};
    export type RequestBody = never;
    export type RequestHeaders = {};
    export type ResponseBody = NutritionPatternAnalysisResponseV2;
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
