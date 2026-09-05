import type * as OpenApi from "./generated/openapi";

type DeepRequired<T> = T extends readonly (infer Item)[]
  ? DeepRequired<Item>[]
  : T extends object
    ? { [Key in keyof T]-?: DeepRequired<Exclude<T[Key], undefined>> }
    : T;

export type Sex = OpenApi.Sex;
export type ActivityLevel = OpenApi.ActivityLevel;
export type Goal = OpenApi.Goal;
export type CutIntensity = NonNullable<OpenApi.ProfileUpsert["selected_cut_intensity"]>;
export type NutritionBasis = OpenApi.NutritionBasis;
export type DefaultUnitType = OpenApi.DefaultUnitType;
export type UnitBasis = OpenApi.UnitBasis;
export type FoodKind = OpenApi.FoodKind;
export type GroupDataStatus = OpenApi.GroupDataStatus;
export type GroupDataCompleteness = OpenApi.GroupDataCompleteness;
export type NutritionSourceType = OpenApi.NutritionSourceType;
export type IngredientsSourceType = OpenApi.IngredientsSourceType;
export type SourceReliability = OpenApi.RegistrySourceTypeDefinition["reliability"];
export type FoodStatus = OpenApi.FoodStatus;
export type GrainType = OpenApi.GrainType;
export type BakedGoodType = OpenApi.BakedGoodType;
export type GrainStarchType = OpenApi.GrainStarchType;

export type TargetResponse = Omit<
  DeepRequired<OpenApi.TargetResponse>,
  "additional_targets" | "preview_hash"
> & {
  additional_targets?: AdditionalNutrientTarget[];
  preview_hash?: string | null;
};
export type NutrientTargetType = OpenApi.AdditionalNutrientTarget["target_type"];
export type AdditionalNutrientTarget = DeepRequired<OpenApi.AdditionalNutrientTarget>;
export type CalculationWarning = OpenApi.CalculationWarningResponse;
export type CalendarAuthorityResponse = DeepRequired<OpenApi.CalendarAuthorityResponse>;

/** Editable Profile domain input mapped to the generated transport request. */
export type ProfileInput = Required<
  Pick<OpenApi.ProfileUpsert, "protein_per_kg" | "fat_pct" | "selected_cut_intensity">
> & Omit<OpenApi.ProfileUpsert, "protein_per_kg" | "fat_pct" | "selected_cut_intensity">;

export type NutritionRegistryResponse = DeepRequired<OpenApi.NutritionRegistryResponse>;
export type ProfileResponse = Omit<
  DeepRequired<OpenApi.ProfileResponse>,
  "targets" | "effective_plan" | "pending_plan"
> & {
  targets: TargetResponse;
  effective_plan: TargetPlanSummary | null;
  pending_plan: TargetPlanSummary | null;
};
export type TargetPlanSummary = Omit<DeepRequired<OpenApi.TargetPlanSummary>, "targets"> & {
  targets: TargetResponse;
};
export type TargetPlanActivationResponse = Omit<
  DeepRequired<OpenApi.TargetPlanActivationResponse>,
  "plan" | "replaced_plan"
> & {
  plan: TargetPlanSummary;
  replaced_plan: TargetPlanSummary | null;
};
export type TargetPlanHistoryResponse = Omit<
  DeepRequired<OpenApi.TargetPlanHistoryResponse>,
  "items"
> & { items: TargetPlanSummary[] };

export type FoodInput = Omit<
  DeepRequired<OpenApi.Foods.AddFoodFoodsPost.RequestBody>,
  "id"
>;
export type FoodResponse = DeepRequired<OpenApi.FoodResponseV3>;
export type FoodPickerItem = OpenApi.FoodPickerItem;
export type FoodPickerResponse = OpenApi.FoodPickerResponse;
export type FoodSort = "name" | "recent" | "calories" | "protein";
export type FoodListResponse = Omit<DeepRequired<OpenApi.FoodListResponse>, "items"> & {
  items: FoodResponse[];
};

export type NutritionSnapshot = OpenApi.NutritionSnapshot &
  Required<
    Pick<
      OpenApi.NutritionSnapshot,
      "food_id" | "name" | "calories" | "protein_g" | "carb_g" | "fat_g"
    >
  >;
export type NutritionTotals = Omit<
  DeepRequired<OpenApi.NutritionTotals>,
  "total_sugars_g"
> & Pick<OpenApi.NutritionTotals, "total_sugars_g">;
export type MealType = OpenApi.MealType;
export type DiaryEntryInput = Omit<
  DeepRequired<OpenApi.Diary.AddEntryDiaryEntriesPost.RequestBody>,
  "id"
> & { id?: string };
export type DiaryEntryResponse = Omit<DeepRequired<OpenApi.DiaryEntryResponse>, "totals" | "nutrition_snapshot"> & {
  totals: NutritionTotals;
  nutrition_snapshot: NutritionSnapshot;
};
export type AdminDiaryPage = DeepRequired<OpenApi.AdminDiaryPage>;
export type AdminDiaryItem = DeepRequired<OpenApi.AdminDiaryItem>;
export type DiaryLoggingStatus = OpenApi.DiaryLoggingStatus;
export type DiaryDayStatusResponse = DeepRequired<OpenApi.DiaryDayStatusResponse>;
export type PatternAnalysisResponse = DeepRequired<OpenApi.NutritionPatternAnalysisResponseV2>;
export type PatternAnalysisHistory = DeepRequired<OpenApi.NutritionPatternAnalysisHistoryPageV2>;
export type PatternAnalysisHistoryItem = DeepRequired<OpenApi.NutritionPatternAnalysisHistoryItemV2>;
export type PatternAnalysisMetric = PatternAnalysisResponse["metric_summaries"][number];
export type WeeklyPriorityResult = DeepRequired<OpenApi.WeeklyPriorityResultV1>;
export type WeeklyPriority = DeepRequired<OpenApi.PriorityV1>;
export type BehaviorGoal = DeepRequired<OpenApi.BehaviorGoalResponseV1>;
export type BehaviorGoalCurrent = DeepRequired<OpenApi.BehaviorGoalCurrentResponseV1>;
export type BehaviorGoalHistory = DeepRequired<OpenApi.BehaviorGoalHistoryPageV1>;
export type BehaviorGoalCommand = OpenApi.BehaviorGoalCommandV1;
export type BehaviorGoalCommandResponse = DeepRequired<OpenApi.BehaviorGoalCommandResponseV1>;
export type DaySummary = Omit<DeepRequired<OpenApi.DaySummary>, "totals" | "targets"> & {
  totals: NutritionTotals;
  targets: TargetResponse | null;
};
export type DiaryNutrientAggregate = DeepRequired<OpenApi.DiaryNutrientAggregate>;
export type WeekSummary = Omit<DeepRequired<OpenApi.WeekSummary>, "weekly_totals" | "targets" | "days"> & {
  weekly_totals: NutritionTotals;
  targets: TargetResponse | null;
  days: DaySummary[];
};
