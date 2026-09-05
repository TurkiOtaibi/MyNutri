import type {
  BehaviorGoal,
  BehaviorGoalCommand,
  PatternAnalysisMetric,
  PatternAnalysisResponse,
  WeeklyPriorityResult
} from "@/lib/types";

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

export const PRIORITY_COPY = {
  heading: "أولوية هذا الأسبوع",
  loading: "جارٍ تحميل أولوية الأسبوع",
  unavailable: "لا تتوفر أولوية أسبوعية موثوقة الآن.",
  stale: "تغيّرت بيانات اليوميات. حدّث التحليل قبل عرض أولوية.",
  safety: "لا يمكن اقتراح أولوية آمنة من هذه البيانات. راجع إعدادات أهدافك أو مختصًا مؤهلًا عند الحاجة.",
  evidence: "بُني هذا الاقتراح على الأيام المكتملة والتغطية المتاحة، وليس على الأيام غير المكتملة.",
  offer: "هل ترغب في تحويل الأولوية إلى هدف أسبوعي؟",
  failure: "تعذر تحميل أولوية الأسبوع. حاول مرة أخرى.",
  commandFailure: "تعذر حفظ الهدف. لم تُفقد بياناتك؛ حاول مجددًا.",
  repeatSuccess: "بدأ أسبوع جديد للهدف مع الاحتفاظ بنتيجة الأسبوع السابق.",
  informationalOnly: "هذه الأولوية إرشادية حاليًا؛ لا يمكن تتبع تنفيذ هذه الخطوة تلقائيًا من بيانات اليوميات."
} as const;

export const goalStateCopy: Record<BehaviorGoal["state"], string> = {
  offered: "هل ترغب في تحويل الأولوية إلى هدف أسبوعي؟",
  deferred: "تم تأجيل الخطوة ويمكنك العودة إليها لاحقًا.",
  active: "هدفك الأسبوعي نشط",
  paused: "الهدف متوقف مؤقتًا",
  incomplete: "راجع هدف الأسبوع وفق الأيام المكتملة.",
  rejected: "تم حفظ اختيارك دون حكم على النتيجة.",
  completed: "اكتملت الخطوة وفق الأيام المسجلة.",
  ended: "تم إنهاء الهدف دون حكم على النتيجة.",
  archived: "هدف محفوظ في السجل."
};

export const goalActionCopy: Record<string, string> = {
  accept: "بدء الهدف",
  edit: "تعديل الخطوة",
  defer: "ذكّرني لاحقًا داخل التطبيق",
  reject: "ليس مناسبًا الآن",
  change: "تغيير الهدف",
  pause: "إيقاف مؤقت",
  resume: "استئناف الهدف",
  end: "إنهاء الهدف",
  repeat: "تكرار الهدف لأسبوع جديد",
  reduce: "تخفيف الخطوة للأسبوع الجديد"
};

export type GoalCommandAttempt = {
  goalId: string;
  key: string;
  command: BehaviorGoalCommand;
};

export type GoalEditTerms = {
  weeklyTargetCount: number;
  scheduledDayMask: number[];
  reminderPreference: "enabled" | "disabled";
  note: string;
};

export function stableGoalCommandAttempt(
  existing: GoalCommandAttempt | null,
  goal: BehaviorGoal,
  action: BehaviorGoal["allowed_actions"][number],
  terms?: GoalEditTerms
): GoalCommandAttempt {
  const event: BehaviorGoalCommand["event"] = action === "reduce" ? "repeat" : action;
  if (existing?.goalId === goal.goal_id && existing.command.event === event) return existing;
  let command: BehaviorGoalCommand;
  if (event === "repeat") {
    command = action === "reduce"
      ? {
          event: "repeat",
          expected_version: goal.version,
          repeat_mode: "reduce",
          weekly_target_count: terms?.weeklyTargetCount
        }
      : { event: "repeat", expected_version: goal.version, repeat_mode: "same" };
  } else if (event === "accept" || event === "edit" || event === "change") {
    command = {
      event,
      expected_version: goal.version,
      weekly_target_count: terms?.weeklyTargetCount,
      scheduled_day_mask: terms?.scheduledDayMask,
      reminder_preference: terms?.reminderPreference,
      note: terms?.note || null
    } as BehaviorGoalCommand;
  } else {
    command = { event, expected_version: goal.version } as BehaviorGoalCommand;
  }
  return {
    goalId: goal.goal_id,
    key: crypto.randomUUID(),
    command
  };
}

export function priorityMessage(priority: WeeklyPriorityResult | null): string {
  if (!priority) return PRIORITY_COPY.unavailable;
  if (priority.status === "stale" || priority.status === "superseded") return PRIORITY_COPY.stale;
  if (priority.status === "safety_suppressed") return PRIORITY_COPY.safety;
  if (priority.status === "none") {
    return priority.none_reason === "insufficient_complete_days" || priority.none_reason === "insufficient_coverage"
      ? "أكمل تسجيل أربعة أيام على الأقل مع بيانات كافية لاقتراح أولوية أسبوعية."
      : "لا توجد أولوية واضحة هذا الأسبوع بناءً على البيانات المكتملة.";
  }
  return "";
}

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
  "group:processed_meat_occurrence_days": "أيام تناول اللحوم المصنعة"
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
