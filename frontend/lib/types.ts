export type Sex = "male" | "female";
export type ActivityLevel = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type Goal = "cut" | "maintain" | "bulk";

export interface TargetResponse {
  bmr: number;
  tdee: number;
  target_calories: number;
  protein_g: number;
  fat_g: number;
  carb_g: number;
  carb_clamped: boolean;
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
  serving_label: string;
  serving_grams: number | null;
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  saturated_fat_g: number | null;
  trans_fat_g: number | null;
  cholesterol_mg: number | null;
  sodium_mg: number | null;
  fiber_g: number | null;
  total_sugars_g: number | null;
  added_sugar_g: number | null;
}

export interface FoodResponse extends FoodInput {
  id: string;
  net_carbs_g: number;
  created_at: string;
  updated_at: string;
}

export interface NutritionSnapshot extends FoodInput {
  food_id: string;
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
  total_sugars_g: number | null;
  added_sugar_g: number | null;
  net_carbs_g: number;
}

export interface DiaryEntryInput {
  id?: string;
  entry_date: string;
  food_id: string;
  quantity: number;
}

export interface DiaryEntryResponse {
  id: string;
  entry_date: string;
  food_id: string;
  quantity: number;
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

export interface QueuedMutation {
  id?: number;
  method: "POST" | "PUT" | "DELETE";
  path: string;
  body?: unknown;
  created_at: string;
  status: "pending" | "syncing";
}

export interface SyncOperation {
  method: QueuedMutation["method"];
  path: string;
  body?: unknown;
  client_id?: string;
  created_at?: string;
}

export interface SyncPushResponse {
  accepted: number;
  accepted_client_ids: string[];
  rejected: Array<{
    method: string;
    path: string;
    client_id?: string | null;
    error: string;
  }>;
}

export interface SyncPullResponse {
  profile: ProfileResponse | null;
  foods: FoodResponse[];
  diary_entries: DiaryEntryResponse[];
}
