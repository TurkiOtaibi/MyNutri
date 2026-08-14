import { ApiError } from "@/lib/api";
import type { ActivityLevel, CutIntensity, Goal, ProfileInput, ProfileResponse, Sex, TargetPlanActivationResponse, TargetResponse } from "@/lib/types";

const SPECIALIST_REVIEW_MESSAGE = "لا يمكن تفعيل هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.";
const VERY_LOW_ENERGY_MESSAGE = "لا يمكن تفعيل هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.";

export const PROTEIN_DEFAULT = 1.2;
export const FAT_DEFAULTS: Record<Sex, number> = { male: 0.25, female: 0.3 };
export const PROFILE_LIMITS = {
  heightMin: 100,
  heightMax: 250,
  weightMin: 20,
  weightMax: 300,
  proteinMin: 1,
  proteinMax: 3,
  fatMinPercent: 15,
  fatMaxPercent: 40
} as const;

export const activityDescriptions: Record<ActivityLevel, string> = {
  sedentary: "حركة يومية محدودة ولا توجد تمارين منتظمة",
  light: "تمارين خفيفة أو حركة بسيطة خلال الأسبوع",
  moderate: "تمارين منتظمة عدة أيام أسبوعيًا",
  active: "تمارين قوية أو عمل كثير الحركة",
  very_active: "نشاط بدني مكثف أو تدريب شبه يومي"
};

export const activityDisplayLabels: Record<ActivityLevel, string> = {
  sedentary: "خامل · مستوى منخفض",
  light: "نشاط خفيف",
  moderate: "نشاط متوسط",
  active: "نشاط مرتفع",
  very_active: "نشاط مرتفع جدًا"
};

export const goalDescriptions: Record<Goal, string> = {
  cut: "خفض الدهون تدريجيًا",
  maintain: "الحفاظ على الوزن الحالي",
  bulk: "رفع الوزن والسعرات تدريجيًا"
};

export const goalDisplayLabels: Record<Goal, string> = {
  cut: "تنشيف",
  maintain: "المحافظة",
  bulk: "زيادة الوزن"
};

export type DraftProfile = {
  sex: Sex;
  birth_date: string;
  height_cm: string;
  weight_kg: string;
  activity_level: ActivityLevel;
  goal: Goal;
  selected_cut_intensity: CutIntensity;
  protein_per_kg: string;
  fat_percent: string;
};

export type ProfileField = keyof DraftProfile;
export type FieldErrors = Partial<Record<ProfileField, string>>;
export type SheetKind = "sex" | "activity" | "goal" | "calculation" | null;
export type ActivationSubmission = {
  payload: ProfileInput;
  preview: TargetResponse & { preview_hash: string };
  idempotencyKey: string;
  replacesPendingPlan: boolean;
};
export type ActivationPhase =
  | { kind: "idle" }
  | { kind: "confirming"; submission: ActivationSubmission }
  | { kind: "submitting"; submission: ActivationSubmission }
  | { kind: "reconciling"; submission: ActivationSubmission; accepted: TargetPlanActivationResponse }
  | { kind: "committed"; accepted: TargetPlanActivationResponse }
  | { kind: "recovery"; submission: ActivationSubmission; accepted: TargetPlanActivationResponse }
  | { kind: "failed"; submission: ActivationSubmission };

export function toDraft(profile: ProfileInput): DraftProfile {
  return {
    sex: profile.sex,
    birth_date: profile.birth_date,
    height_cm: formatEditableNumber(profile.height_cm),
    weight_kg: formatEditableNumber(profile.weight_kg),
    activity_level: profile.activity_level,
    goal: profile.goal,
    selected_cut_intensity: profile.selected_cut_intensity,
    protein_per_kg: formatEditableNumber(profile.protein_per_kg),
    fat_percent: formatEditableNumber(profile.fat_pct * 100)
  };
}

export function blankDraft(): DraftProfile {
  return {
    sex: "male",
    birth_date: "",
    height_cm: "",
    weight_kg: "",
    activity_level: "moderate",
    goal: "cut",
    selected_cut_intensity: 0.2,
    protein_per_kg: String(PROTEIN_DEFAULT),
    fat_percent: String(FAT_DEFAULTS.male * 100)
  };
}

export function formatEditableNumber(value: number): string {
  return Number.isFinite(value) ? String(Number(value.toFixed(2))) : "";
}

export function normalizeNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed || !/^(?:\d+\.?\d*|\.\d+)$/.test(trimmed)) return null;
  const number = Number(trimmed);
  return Number.isFinite(number) ? number : null;
}

export function normalizeDraft(draft: DraftProfile): string {
  const normalized = {
    ...draft,
    height_cm: normalizeNumber(draft.height_cm),
    weight_kg: normalizeNumber(draft.weight_kg),
    protein_per_kg: normalizeNumber(draft.protein_per_kg),
    fat_percent: normalizeNumber(draft.fat_percent)
  };
  return JSON.stringify(normalized);
}

export function validateDraft(draft: DraftProfile, authoritativeDate: string | null): { errors: FieldErrors; payload: ProfileInput | null } {
  const errors: FieldErrors = {};
  const height = normalizeNumber(draft.height_cm);
  const weight = normalizeNumber(draft.weight_kg);
  const protein = normalizeNumber(draft.protein_per_kg);
  const fatPercent = normalizeNumber(draft.fat_percent);
  const validBirthDate = /^\d{4}-\d{2}-\d{2}$/.test(draft.birth_date);

  if (!validBirthDate || !authoritativeDate || draft.birth_date > authoritativeDate) errors.birth_date = "اختر تاريخ ميلاد صحيحًا";
  if (height == null || height < PROFILE_LIMITS.heightMin || height > PROFILE_LIMITS.heightMax) errors.height_cm = "أدخل طولًا صحيحًا";
  if (weight == null || weight < PROFILE_LIMITS.weightMin || weight > PROFILE_LIMITS.weightMax) errors.weight_kg = "أدخل وزنًا صحيحًا";
  if (protein == null || protein < PROFILE_LIMITS.proteinMin || protein > PROFILE_LIMITS.proteinMax) {
    errors.protein_per_kg = "أدخل قيمة صحيحة للبروتين لكل كجم";
  }
  if (fatPercent == null || fatPercent < PROFILE_LIMITS.fatMinPercent || fatPercent > PROFILE_LIMITS.fatMaxPercent) {
    errors.fat_percent = "أدخل نسبة دهون صحيحة";
  }
  if (![0.15, 0.2, 0.25].includes(draft.selected_cut_intensity)) {
    errors.selected_cut_intensity = "اختر شدة خفض صحيحة";
  }

  if (Object.keys(errors).length > 0 || height == null || weight == null || protein == null || fatPercent == null) {
    return { errors, payload: null };
  }
  return {
    errors,
    payload: {
      sex: draft.sex,
      birth_date: draft.birth_date,
      height_cm: height,
      weight_kg: weight,
      activity_level: draft.activity_level,
      goal: draft.goal,
      selected_cut_intensity: draft.selected_cut_intensity,
      protein_per_kg: protein,
      fat_pct: fatPercent / 100
    }
  };
}

export type BlockingSafetyOutcome = "specialist_review_required" | "very_low_energy_blocked";

export function blockingSafetyMessage(outcome: string): string | null {
  if (outcome === "specialist_review_required") return SPECIALIST_REVIEW_MESSAGE;
  if (outcome === "very_low_energy_blocked") return VERY_LOW_ENERGY_MESSAGE;
  if (outcome !== "normal") return "تعذر التحقق من إمكانية تفعيل هذا الهدف. حدّث المعاينة قبل المتابعة.";
  return null;
}

export function isPreviewActivatable(targets: TargetResponse | null): targets is TargetResponse & { preview_hash: string } {
  return Boolean(
    targets?.preview_hash &&
    targets.can_activate === true &&
    targets.safety_outcome === "normal"
  );
}

export function profileMatchesAcceptedActivation(
  profile: ProfileResponse,
  submission: ActivationSubmission,
  activation: TargetPlanActivationResponse
): boolean {
  const containsPlan = profile.effective_plan?.id === activation.plan.id || profile.pending_plan?.id === activation.plan.id;
  return containsPlan && normalizeDraft(toDraft(profile)) === normalizeDraft(toDraft(submission.payload));
}

export function formatArabicGregorianDate(input: string): string {
  const [year, month, day] = input.split("-").map(Number);
  if (!year || !month || !day) return "غير محدد";
  return new Intl.DateTimeFormat("ar-SA-u-ca-gregory-nu-latn", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(year, month - 1, day)));
}

export function formatTargetNumber(value: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, useGrouping: false }).format(value);
}

export function mapProfileApiErrors(error: unknown): FieldErrors {
  if (!(error instanceof ApiError) || !Array.isArray(error.detail)) return {};
  const mapped: FieldErrors = {};
  for (const item of error.detail as Array<{ loc?: unknown[] }>) {
    const field = item.loc?.at(-1);
    if (field === "birth_date") mapped.birth_date = "اختر تاريخ ميلاد صحيحًا";
    if (field === "height_cm") mapped.height_cm = "أدخل طولًا صحيحًا";
    if (field === "weight_kg") mapped.weight_kg = "أدخل وزنًا صحيحًا";
    if (field === "protein_per_kg") mapped.protein_per_kg = "أدخل قيمة صحيحة للبروتين لكل كجم";
    if (field === "fat_pct") mapped.fat_percent = "أدخل نسبة دهون صحيحة";
  }
  return mapped;
}
