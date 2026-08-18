import type { PatternAnalysisMetric, PatternAnalysisResponse } from "@/lib/types";

export const ANALYSIS_COPY = {
  heading: "تحليل نمط التغذية",
  loading: "جارٍ تحليل نمط التغذية",
  insufficient: "التحليل غير متاح لعدم كفاية الأيام المكتملة",
  limited: "البيانات محدودة لهذا العنصر",
  stale: "تغيرت بعض البيانات منذ هذه النسخة",
  unsupported: "تعذر فتح هذه النسخة بإصدارها الأصلي",
  failure: "تعذر تحديث التحليل. حاول مرة أخرى",
  evaluate: "تحديث التحليل",
  history: "سجل تحليلات نمط التغذية"
} as const;

export const metricLabels: Record<string, string> = {
  "energy:calories_kcal_per_day": "متوسط الطاقة اليومي",
  "macro:protein_g_per_day": "متوسط البروتين اليومي",
  "macro:carb_g_per_day": "متوسط الكربوهيدرات اليومي",
  "macro:fat_g_per_day": "متوسط الدهون اليومي",
  "nutrient:fiber_g": "الألياف",
  "group:fruit_vegetable_g_per_day": "الفواكه والخضروات",
  "group:legumes_servings_per_period": "البقوليات",
  "group:whole_grain_share_percent": "نسبة الحبوب الكاملة",
  "group:nuts_seeds_servings_per_period": "المكسرات والبذور",
  "group:seafood_servings_per_period": "المأكولات البحرية",
  "group:processed_meat_occurrence_days": "أيام تناول اللحوم المصنعة",
  "nova:nova4_calorie_share_percent": "نسبة طاقة NOVA 4"
};

export type AnalysisDisplayState =
  | "empty"
  | "current"
  | "stale"
  | "limited"
  | "unsafe";

export function displayState(analysis: PatternAnalysisResponse | null): AnalysisDisplayState {
  if (!analysis) return "empty";
  if (analysis.lifecycle_status === "stale") return "stale";
  if (analysis.priority_input.safety_flags.length > 0) return "unsafe";
  if (analysis.metric_summaries.some((metric) => metric.current.confidence === "limited")) {
    return "limited";
  }
  return "current";
}

export function visibleMetrics(analysis: PatternAnalysisResponse): PatternAnalysisMetric[] {
  return analysis.metric_summaries
    .filter((metric) => metric.current.value !== null)
    .sort((left, right) => left.metric_key.localeCompare(right.metric_key, "en"));
}

export function metricLabel(metricKey: string): string {
  return metricLabels[metricKey] ?? metricKey;
}

export function metricStatusText(metric: PatternAnalysisMetric): string {
  if (metric.current.confidence === "limited") return ANALYSIS_COPY.limited;
  if (metric.current.confidence === "unavailable") return "الدليل غير كافٍ لهذا العنصر";
  return {
    below_target: "أقل من النطاق المستهدف",
    above_target: "أعلى من النطاق المستهدف",
    at_target: "عند الهدف",
    within_target: "ضمن الهدف",
    observed: "نمط مسجل",
    target_incompatible: "الهدف غير متوافق",
    unavailable: "غير متاح"
  }[metric.current.status];
}

export function formatMetricValue(metric: PatternAnalysisMetric): string {
  if (metric.current.value === null) return "غير متاح";
  return `${new Intl.NumberFormat("ar-SA", { maximumFractionDigits: 2 }).format(metric.current.value)} ${metric.unit}`;
}

export type AnalysisAttempt = {
  key: string;
  expectedRevision: number | null;
  etag: string | null;
};

export function stableAnalysisAttempt(
  existing: AnalysisAttempt | null,
  analysis: PatternAnalysisResponse | null
): AnalysisAttempt {
  return existing ?? {
    key: crypto.randomUUID(),
    expectedRevision: analysis?.source_analysis_revision ?? null,
    etag: analysis?.etag ?? null
  };
}
