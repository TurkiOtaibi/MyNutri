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
  protein_g: number;
  fat_g: number;
  carb_g: number;
  carb_clamped: boolean;
  additional_targets?: AdditionalNutrientTarget[];
}

export interface AdditionalNutrientTarget {
  key: string;
  label_ar: string;
  unit: string;
  precision: number;
  order: number;
  target_type: "minimum" | "maximum" | "range" | "monitor_only";
  target_source: "fixed" | "calculated" | "reference" | "manual" | "clinical";
  target_value: number | null;
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
