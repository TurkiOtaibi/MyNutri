import { AlertTriangle, Check, Info } from "lucide-react";
import type { RefObject } from "react";
import { definitionsFromRegistry, formatNutrientValue, targetTypeLabels } from "@/lib/nutrients";
import type { Goal, NutritionRegistryResponse, ProfileResponse, TargetPlanSummary, TargetResponse } from "@/lib/types";
import { blockingSafetyMessage, formatTargetNumber, isPreviewActivatable, type BlockingSafetyOutcome } from "./profile-model";

export function TargetsCard({ title, badge, targets }: { title: string; badge: string; targets: TargetResponse | null }) {
  return (
    <section className="profile-targets-card" aria-label={title}>
      <header><div><h2>{title}</h2><p>تتحدث بعد حفظ بياناتك.</p></div><span>{badge}</span></header>
      {targets ? (
        <><div className="profile-calorie-target"><strong><bdi>{targets.target_calories}</bdi></strong><span>سعرة حرارية يوميًا</span></div><div className="profile-macro-targets"><TargetValue label="البروتين" value={targets.protein_g} /><TargetValue label="الكارب" value={targets.carb_g} /><TargetValue label="الدهون" value={targets.fat_g} /></div></>
      ) : <div className="profile-incomplete"><strong>أكمل بياناتك لحساب أهدافك اليومية</strong><span>أدخل تاريخ الميلاد والطول والوزن.</span></div>}
    </section>
  );
}

export function TargetValue({ label, value }: { label: string; value: number }) {
  return <div><span>{label}</span><strong><bdi dir="ltr">{formatTargetNumber(value)}</bdi> جم</strong></div>;
}

export function AdditionalTargetsCard({ targets, registry }: { targets: TargetResponse | null; registry: NutritionRegistryResponse }) {
  if (!targets) return null;
  const resolvedTargets = new Map((targets.additional_targets ?? []).map((target) => [target.key, target]));
  const definitions = definitionsFromRegistry(registry)
    .filter((definition) => resolvedTargets.has(definition.key))
    .map((definition) => ({ ...definition, targetValue: resolvedTargets.get(definition.key)?.target_value ?? null }));
  return (
    <section className="profile-additional-targets" aria-labelledby="additional-targets-title">
      <h2 id="additional-targets-title">أهداف غذائية إضافية</h2>
      <div>
        {definitions.map((item) => (
          <div className="profile-additional-target-row" key={item.key}>
            <strong>{item.label}</strong>
            <span>{item.targetValue == null ? (item.targetType === "monitor_only" ? "متابعة فقط" : "لم يُحدد هدف افتراضي بعد") : <><bdi dir="ltr">{formatNutrientValue(item.targetValue, item.precision)} {item.unit}</bdi> يوميًا</>}</span>
            {item.targetValue != null ? <small>{targetTypeLabels[item.targetType]}</small> : null}
          </div>
        ))}
      </div>
    </section>
  );
}

export function RegistryState({ kind, onRetry }: { kind: "loading" | "unavailable" | "incompatible"; onRetry?: () => void }) {
  const copy = kind === "loading"
    ? "جارٍ تحميل البيانات الغذائية"
    : kind === "unavailable"
      ? "تعذر تحميل البيانات الغذائية"
      : "إصدار سجل التغذية غير متوافق. يلزم تحديث التطبيق أو التواصل مع الدعم.";
  return (
    <section className="profile-registry-state" role={kind === "loading" ? "status" : "alert"} aria-live="polite">
      <strong>{copy}</strong>
      {kind !== "loading" ? <button className="btn" type="button" onClick={onRetry}>إعادة المحاولة</button> : null}
    </section>
  );
}

const planStatusLabels: Record<TargetPlanSummary["status"], string> = {
  active: "حالية",
  scheduled: "مجدولة",
  closed: "سابقة",
  superseded_before_effective: "استُبدلت قبل أن تبدأ"
};

export function TargetPlanHistory({ plans, pending, failed, hasMore, loadingMore, onRetry, onLoadMore }: { plans: TargetPlanSummary[]; pending: boolean; failed: boolean; hasMore: boolean; loadingMore: boolean; onRetry: () => void; onLoadMore: () => void }) {
  return (
    <section className="profile-plan-history" aria-labelledby="target-plan-history-title">
      <h2 id="target-plan-history-title">سجل الخطط</h2>
      {pending ? <div className="profile-history-loading" role="status">جارٍ تحميل سجل الخطط</div> : null}
      {failed ? <div className="profile-history-error" role="alert">تعذر تحميل سجل الخطط<button className="btn" type="button" onClick={onRetry}>إعادة المحاولة</button></div> : null}
      {!pending && !failed && plans.length === 0 ? <p>لا توجد خطط محفوظة بعد.</p> : null}
      {!failed && plans.length > 0 ? <ol>{plans.map((plan) => <li key={plan.id}><div><strong>{planStatusLabels[plan.status]}</strong><span>تبدأ <bdi dir="ltr">{plan.effective_from}</bdi>{plan.effective_to ? <> وتنتهي قبل <bdi dir="ltr">{plan.effective_to}</bdi></> : null}</span></div><bdi dir="ltr">{plan.targets.target_calories} kcal</bdi></li>)}</ol> : null}
      {hasMore ? <button className="profile-text-action" type="button" disabled={loadingMore} onClick={onLoadMore}>{loadingMore ? "جارٍ التحميل…" : "عرض خطط أقدم"}</button> : null}
    </section>
  );
}

export function ScheduledPlanCard({ plan }: { plan: NonNullable<ProfileResponse["pending_plan"]> }) {
  return (
    <section className="profile-preview-card" aria-label="الأهداف المجدولة">
      <header><span>الخطة المجدولة</span><strong>تبدأ في <bdi dir="ltr">{plan.effective_from}</bdi></strong></header>
      <div className="profile-preview-values">
        <strong><bdi>{plan.targets.target_calories}</bdi> سعرة</strong>
        <span>بروتين <bdi dir="ltr">{formatTargetNumber(plan.targets.protein_g)}</bdi> جم</span>
        <span>كارب <bdi dir="ltr">{formatTargetNumber(plan.targets.carb_g)}</bdi> جم</span>
        <span>دهون <bdi dir="ltr">{formatTargetNumber(plan.targets.fat_g)}</bdi> جم</span>
      </div>
    </section>
  );
}

export function ExpectedTargetsCard({
  targets,
  goal,
  pending,
  failed,
  recoveryOutcome,
  safetyAttemptSequence,
  safetyRef,
  onRetry
}: {
  targets: TargetResponse | null;
  goal: Goal;
  pending: boolean;
  failed: boolean;
  recoveryOutcome: BlockingSafetyOutcome | null;
  safetyAttemptSequence: number;
  safetyRef: RefObject<HTMLDivElement | null>;
  onRetry: () => void;
}) {
  const outcome = recoveryOutcome ?? targets?.safety_outcome ?? null;
  const safetyMessage = outcome
    ? blockingSafetyMessage(outcome) ??
      (targets && !isPreviewActivatable(targets)
        ? "تعذر التحقق من إمكانية تفعيل هذا الهدف. حدّث المعاينة قبل المتابعة."
        : null)
    : null;
  const previewDescription = targets && isPreviewActivatable(targets)
    ? "ستُطبق هذه الأهداف بعد حفظ التغييرات."
    : safetyMessage
      ? "هذه معاينة توضيحية فقط، ولا يمكن تفعيل هذا الهدف."
      : "راجع نتيجة المعاينة قبل المتابعة.";
  const announceSafety = safetyAttemptSequence > 0;
  return (
    <section className="profile-preview-card" aria-label="الأهداف المتوقعة بعد الحفظ">
      <header><div><h2>الأهداف المتوقعة بعد الحفظ</h2><p>{previewDescription}</p></div><span>معاينة</span></header>
      {pending ? <div className="profile-preview-skeleton" aria-label="جارٍ تحديث معاينة الأهداف" role="status" /> : null}
      {failed ? <div className="profile-preview-error"><strong>تعذر تحديث معاينة الأهداف</strong><button type="button" onClick={onRetry}>إعادة المحاولة</button></div> : null}
      {!pending && !failed && targets ? (
        <>
          <div className="profile-preview-values">
            <strong><bdi>{targets.final_target_calories}</bdi> سعرة</strong>
            <span>بروتين <bdi dir="ltr">{formatTargetNumber(targets.protein_g)}</bdi> جم</span>
            <span>كارب <bdi dir="ltr">{formatTargetNumber(targets.carb_g)}</bdi> جم</span>
            <span>دهون <bdi dir="ltr">{formatTargetNumber(targets.fat_g)}</bdi> جم</span>
          </div>
          <dl className="profile-preview-summary">
            {goal === "cut" ? <div><dt>شدة الخفض المختارة</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.selected_cut_intensity * 100)}%</bdi></dd></div> : null}
            <div><dt>العجز المطلوب</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.requested_deficit_kcal)}</bdi> سعرة</dd></div>
            <div><dt>العجز المطبق</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.applied_deficit_kcal)}</bdi> سعرة</dd></div>
          </dl>
          {targets.deficit_cap_applied ? (
            <div className="profile-preview-notice">
              <Info size={18} aria-hidden="true" />
              <span>طُبق حد العجز الآمن، وأصبح العجز المطبق <bdi dir="ltr">{formatTargetNumber(targets.applied_deficit_kcal)}</bdi> سعرة.</span>
            </div>
          ) : null}
          {targets.calculation_warnings.length > 0 ? (
            <section className="profile-preview-warnings" aria-label="تنبيهات الحساب">
              <h3><AlertTriangle size={18} aria-hidden="true" /> تنبيهات الحساب</h3>
              <ul>
                {targets.calculation_warnings.map((warning) => (
                  <li key={warning.code}>
                    <span>{warning.message_ar}</span>
                    <small>القيمة <bdi dir="ltr">{formatTargetNumber(warning.value)}</bdi> جم، والمرجع <bdi dir="ltr">{formatTargetNumber(warning.reference_value)}</bdi> جم</small>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
          <section className="profile-protein-calculation" aria-labelledby="profile-protein-calculation-title">
            <h3 id="profile-protein-calculation-title">تفاصيل حساب البروتين</h3>
            <p>{targets.protein_calculation.explanation_ar}</p>
            <dl>
              <div><dt>أساس الحساب</dt><dd>{targets.protein_calculation.basis === "actual_weight" ? "الوزن الفعلي" : "الوزن المعدل"}</dd></div>
              <div><dt>مؤشر كتلة الجسم المستخدم</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.protein_calculation.bmi_used)}</bdi></dd></div>
              <div><dt>الوزن الفعلي</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.protein_calculation.actual_weight_kg)}</bdi> كجم</dd></div>
              <div><dt>{targets.protein_calculation.reference_weight_label_ar}</dt><dd>{targets.protein_calculation.reference_weight_kg == null ? "غير مستخدم" : <><bdi dir="ltr">{formatTargetNumber(targets.protein_calculation.reference_weight_kg)}</bdi> كجم</>}</dd></div>
              <div><dt>وزن الحساب</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.protein_calculation.calculation_weight_kg)}</bdi> كجم</dd></div>
              <div><dt>البروتين لكل كجم</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.protein_calculation.protein_per_kg)}</bdi> جم</dd></div>
              <div><dt>هدف البروتين</dt><dd><bdi dir="ltr">{formatTargetNumber(targets.protein_calculation.target_g)}</bdi> جم</dd></div>
            </dl>
          </section>
        </>
      ) : null}
      {!pending && !failed && safetyMessage ? (
        <div
          key={`safety-${safetyAttemptSequence}`}
          ref={safetyRef}
          className="profile-safety-decision"
          role={announceSafety ? "alert" : undefined}
          aria-live={announceSafety ? "assertive" : undefined}
          tabIndex={-1}
          data-focus-requested={announceSafety ? "true" : "false"}
        >
          <AlertTriangle size={20} aria-hidden="true" />
          <div><strong>لا يمكن تفعيل الهدف</strong><p>{safetyMessage}</p></div>
        </div>
      ) : !pending && !failed && isPreviewActivatable(targets) ? (
        <div className="profile-safety-decision is-available" role="status">
          <Check size={20} aria-hidden="true" />
          <div><strong>الهدف متاح للتفعيل</strong><p>راجِع القيم ثم تابع إلى التأكيد.</p></div>
        </div>
      ) : null}
    </section>
  );
}
