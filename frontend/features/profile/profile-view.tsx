import { Activity, CalendarDays, Check, ChevronDown, ChevronLeft, Info, LoaderCircle, RotateCcw, Ruler, Scale, SlidersHorizontal, Target, UserRound } from "lucide-react";
import type { FormEvent, RefObject } from "react";
import type { ActivityLevel, Goal, NutritionRegistryResponse, Sex, TargetPlanHistoryResponse, TargetResponse } from "@/lib/types";
import { NumericSettingsRow, OptionList, SelectionCard, SettingsButton, CutIntensitySelector } from "./profile-controls";
import { AdditionalTargetsCard, ExpectedTargetsCard, RegistryState, TargetPlanHistory, TargetsCard } from "./profile-targets";
import { ProfileConfirm, ProfileSheet } from "./profile-dialogs";
import { PROFILE_LIMITS, activityDescriptions, activityDisplayLabels, activityLabels, goalDescriptions, goalDisplayLabels, goalLabels, sexLabels, type BlockingSafetyOutcome, type DraftProfile, type FieldErrors, type SheetKind, type TargetPlanWritePhase } from "./profile-model";
import "./profile.module.css";

const PROFILE_WRITE_ERROR = "تعذر حفظ التغييرات";

type ProfileViewState = {
  dirty: boolean;
  hasPendingServerProfile: boolean;
  draft: DraftProfile;
  errors: FieldErrors;
  effectiveFrom: string;
  authoritativeDate: string | null;
  displayBirthDate: string;
  activeSheet: SheetKind;
  advancedOpen: boolean;
  restoreOpen: boolean;
  effectiveFromRef: RefObject<HTMLInputElement | null>;
  birthRef: RefObject<HTMLInputElement | null>;
  heightRef: RefObject<HTMLInputElement | null>;
  weightRef: RefObject<HTMLInputElement | null>;
  proteinRef: RefObject<HTMLInputElement | null>;
  fatRef: RefObject<HTMLInputElement | null>;
};

type ProfileTargetsViewState = {
  savedTargets: TargetResponse | null;
  registry: {
    pending: boolean;
    failed: boolean;
    data: NutritionRegistryResponse | undefined;
  };
  history: {
    plans: TargetPlanHistoryResponse["items"];
    pending: boolean;
    failed: boolean;
    hasMore: boolean;
    loadingMore: boolean;
  };
  preview: {
    visible: boolean;
    current: TargetResponse | null;
    pending: boolean;
    failed: boolean;
    safetyOutcome: BlockingSafetyOutcome | null;
    safetyAttemptSequence: number;
    safetyRef: RefObject<HTMLDivElement | null>;
  };
};

type ProfileWriteViewState = {
  registryReady: boolean;
  validationHasPayload: boolean;
  writeErrorCode: string | null;
  writePhase: TargetPlanWritePhase;
  restoreWriteFocusRef: RefObject<boolean>;
};

type ProfileViewIntents = {
  keepLocalProfile: () => void;
  acceptServerProfile: () => void;
  updateField: <K extends keyof DraftProfile>(key: K, value: DraftProfile[K]) => void;
  changeEffectiveFrom: (value: string) => void;
  openSheet: (sheet: Exclude<SheetKind, null>) => void;
  closeSheet: () => void;
  selectSex: (sex: Sex) => void;
  selectActivity: (activity: ActivityLevel) => void;
  selectGoal: (goal: Goal) => void;
  toggleAdvanced: () => void;
  requestRestoreDefaults: () => void;
  cancelRestoreDefaults: () => void;
  confirmRestoreDefaults: () => void;
  retryRegistry: () => void;
  retryHistory: () => void;
  loadMoreHistory: () => void;
  retryPreview: () => void;
  submit: (event?: FormEvent) => void;
  retryReconciliation: () => void;
  cancelWriteConfirmation: () => void;
  confirmWrite: () => void;
};

type ProfileViewProps = {
  profile: ProfileViewState;
  targets: ProfileTargetsViewState;
  write: ProfileWriteViewState;
  intents: ProfileViewIntents;
};

export function ProfileView({
  profile,
  targets,
  write,
  intents,
}: ProfileViewProps) {
  const {
    dirty, hasPendingServerProfile, draft, errors, effectiveFrom, authoritativeDate,
    displayBirthDate, activeSheet, advancedOpen, restoreOpen, effectiveFromRef,
    birthRef, heightRef, weightRef, proteinRef, fatRef,
  } = profile;
  const { savedTargets, registry, history, preview } = targets;
  const { registryReady, validationHasPayload, writeErrorCode, writePhase, restoreWriteFocusRef } = write;
  return (
    <main className={`profile-page ${dirty ? "is-dirty" : ""}`}>
      <header className="profile-page-head">
        <h1>بياناتك وأهدافك</h1>
        <p>حدّث بياناتك لنحسب احتياجك اليومي.</p>
      </header>

      <form className="profile-form" onSubmit={intents.submit} noValidate>
        {hasPendingServerProfile ? (
          <div className="unsaved-conflict" role="status">
            <p>توجد نسخة أحدث من بيانات الملف على الخادم. احتفظنا بتعديلاتك الحالية.</p>
            <div className="actions">
              <button className="btn" type="button" onClick={intents.keepLocalProfile}>الاحتفاظ بتعديلاتي</button>
              <button className="btn danger" type="button" onClick={intents.acceptServerProfile}>تحميل نسخة الخادم</button>
            </div>
          </div>
        ) : null}
        <section className="profile-settings-card body-data-card" aria-labelledby="body-data-title">
          <h2 id="body-data-title">بيانات الجسم</h2>
          <SettingsButton
            icon={<UserRound size={19} />}
            label="الجنس"
            value={sexLabels[draft.sex]}
            onClick={() => intents.openSheet("sex")}
            ariaLabel={`تغيير الجنس، القيمة الحالية ${sexLabels[draft.sex]}`}
          />
          <label className={`profile-setting-row profile-date-row ${errors.birth_date ? "has-error" : ""}`}>
            <CalendarDays size={19} aria-hidden="true" />
            <span className="profile-setting-copy"><strong>تاريخ الميلاد</strong><bdi>{displayBirthDate}</bdi></span>
            <ChevronLeft size={18} aria-hidden="true" />
            <input
              ref={birthRef}
              type="date"
              value={draft.birth_date}
              max={authoritativeDate ?? undefined}
              onChange={(event) => intents.updateField("birth_date", event.target.value)}
              aria-label="تاريخ الميلاد"
              aria-invalid={Boolean(errors.birth_date)}
              aria-describedby={errors.birth_date ? "birth-date-error" : undefined}
            />
            {errors.birth_date ? <small id="birth-date-error" className="profile-field-error">{errors.birth_date}</small> : null}
          </label>
          <NumericSettingsRow
            ref={heightRef}
            icon={<Ruler size={19} />}
            label="الطول"
            value={draft.height_cm}
            unit="سم"
            step="0.1"
            min={PROFILE_LIMITS.heightMin}
            max={PROFILE_LIMITS.heightMax}
            error={errors.height_cm}
            onChange={(value) => intents.updateField("height_cm", value)}
          />
          <NumericSettingsRow
            ref={weightRef}
            icon={<Scale size={19} />}
            label="الوزن"
            value={draft.weight_kg}
            unit="كجم"
            step="0.1"
            min={PROFILE_LIMITS.weightMin}
            max={PROFILE_LIMITS.weightMax}
            error={errors.weight_kg}
            onChange={(value) => intents.updateField("weight_kg", value)}
          />
        </section>

        <SelectionCard
          icon={<Activity size={20} />}
          title="مستوى النشاط"
          value={activityDisplayLabels[draft.activity_level]}
          description={activityDescriptions[draft.activity_level]}
          onClick={() => intents.openSheet("activity")}
          ariaLabel={`تغيير مستوى النشاط، القيمة الحالية ${activityLabels[draft.activity_level]}`}
        />

        <SelectionCard
          icon={<Target size={20} />}
          title="الهدف"
          value={goalDisplayLabels[draft.goal]}
          description={goalDescriptions[draft.goal]}
          onClick={() => intents.openSheet("goal")}
          ariaLabel={`تغيير الهدف، القيمة الحالية ${goalLabels[draft.goal]}`}
        />

        {draft.goal === "cut" ? (
          <CutIntensitySelector
            value={draft.selected_cut_intensity}
            onChange={(value) => intents.updateField("selected_cut_intensity", value)}
          />
        ) : null}

        <section className={`profile-advanced ${advancedOpen ? "open" : ""}`}>
          <button
            className="profile-advanced-toggle"
            type="button"
            aria-expanded={advancedOpen}
            aria-controls="advanced-profile-fields"
            aria-label={`${advancedOpen ? "إغلاق" : "فتح"} الخيارات المتقدمة`}
            onClick={intents.toggleAdvanced}
          >
            <SlidersHorizontal size={20} aria-hidden="true" />
            <span><strong>الخيارات المتقدمة</strong><small>لمن يرغب بتخصيص توزيع البروتين والدهون</small></span>
            <ChevronDown className="profile-advanced-chevron" size={19} aria-hidden="true" />
          </button>
          <div id="advanced-profile-fields" className="profile-advanced-content" hidden={!advancedOpen}>
            <NumericSettingsRow
              ref={proteinRef}
              label="البروتين لكل كجم"
              value={draft.protein_per_kg}
              unit="جم/كجم"
              step="0.1"
              min={PROFILE_LIMITS.proteinMin}
              max={PROFILE_LIMITS.proteinMax}
              error={errors.protein_per_kg}
              help="يحدد هدف البروتين حسب وزنك."
              onChange={(value) => intents.updateField("protein_per_kg", value)}
            />
            <NumericSettingsRow
              ref={fatRef}
              label="نسبة الدهون"
              value={draft.fat_percent}
              unit="%"
              step="1"
              min={PROFILE_LIMITS.fatMinPercent}
              max={PROFILE_LIMITS.fatMaxPercent}
              error={errors.fat_percent}
              help="تحدد نسبة السعرات اليومية القادمة من الدهون."
              onChange={(value) => intents.updateField("fat_percent", value)}
            />
            <p className="profile-advanced-notice">تغيير هذه القيم سيؤثر في أهداف البروتين والدهون اليومية.</p>
            <button
              className="profile-text-action"
              type="button"
              onClick={intents.requestRestoreDefaults}
            >استعادة القيم الافتراضية</button>
          </div>
        </section>

        <section className="profile-settings-card" aria-labelledby="target-effective-date-title">
          <h2 id="target-effective-date-title">تاريخ سريان الأهداف</h2>
          <label className={`profile-setting-row profile-date-row ${errors.effective_from ? "has-error" : ""}`}>
            <CalendarDays size={19} aria-hidden="true" />
            <span className="profile-setting-copy"><strong>تاريخ السريان</strong><bdi dir="ltr">{effectiveFrom || "غير محدد"}</bdi></span>
            <ChevronLeft size={18} aria-hidden="true" />
            <input
              ref={effectiveFromRef}
              type="date"
              value={effectiveFrom}
              min={authoritativeDate ?? undefined}
              onChange={(event) => intents.changeEffectiveFrom(event.target.value)}
              aria-label="تاريخ سريان الأهداف"
              aria-invalid={Boolean(errors.effective_from)}
              aria-describedby={errors.effective_from ? "effective-from-error" : undefined}
            />
            {errors.effective_from ? <small id="effective-from-error" className="profile-field-error">{errors.effective_from}</small> : null}
          </label>
        </section>

        <TargetsCard title="الأهداف اليومية" badge="محسوبة تلقائيًا" targets={savedTargets} />
        {registry.pending ? <RegistryState kind="loading" /> : registry.failed ? <RegistryState kind="unavailable" onRetry={intents.retryRegistry} /> : registryReady ? <AdditionalTargetsCard targets={savedTargets} registry={registry.data!} /> : null}
        <TargetPlanHistory
          plans={history.plans}
          pending={history.pending}
          failed={history.failed}
          hasMore={history.hasMore}
          loadingMore={history.loadingMore}
          onRetry={intents.retryHistory}
          onLoadMore={intents.loadMoreHistory}
        />
        <button className="profile-explain-action" type="button" onClick={() => intents.openSheet("calculation")}><Info size={17} /> كيف حُسبت أهدافي؟</button>

        {preview.visible ? (
          <ExpectedTargetsCard
            targets={preview.current}
            goal={draft.goal}
            pending={preview.pending}
            failed={preview.failed}
            recoveryOutcome={preview.safetyOutcome}
            safetyAttemptSequence={preview.safetyAttemptSequence}
            safetyRef={preview.safetyRef}
            onRetry={intents.retryPreview}
          />
        ) : null}

      </form>

      {dirty ? (
        <div className="profile-save-bar" role="region" aria-label="حفظ تغييرات الملف الشخصي">
          <span>{Object.keys(errors).length > 0 ? "صحح الحقول المعلّمة للمتابعة" : preview.safetyOutcome ? "راجع قرار السلامة وحدّث المعاينة قبل المتابعة" : writeErrorCode ? "تغيّرت المعاينة. راجع الأهداف المحدثة ثم أكد مجددًا" : writePhase.kind === "failed" ? PROFILE_WRITE_ERROR : !registryReady ? "سجل التغذية غير جاهز" : "تغييرات غير محفوظة"}</span>
          {writePhase.kind === "failed" ? <small>تحقق من الاتصال ثم أعد المحاولة</small> : null}
          <button className="btn primary" type="button" onClick={() => intents.submit()} disabled={!registryReady || writePhase.kind === "submitting" || preview.pending || (validationHasPayload && !preview.current?.preview_hash && !preview.safetyOutcome)}>
            {writePhase.kind === "submitting" ? <><LoaderCircle className="spin" size={17} /> جارٍ حفظ الخطة…</> : preview.safetyOutcome ? "تحديث المعاينة" : writeErrorCode ? "مراجعة المعاينة" : writePhase.kind === "failed" ? <><RotateCcw size={17} /> إعادة المحاولة</> : "مراجعة وتأكيد"}
          </button>
        </div>
      ) : null}

      {["reconciling", "committed"].includes(writePhase.kind) ? <div className="profile-save-status" role="status"><Check size={17} /> تم حفظ التغييرات</div> : null}
      {writePhase.kind === "recovery" ? (
        <div className="profile-reconciliation-status" role="status">
          <div><Check size={17} /><span><strong>تم حفظ التغييرات</strong><small>تعذر تحديث البيانات المعروضة. الأهداف المحفوظة أدناه ما زالت معتمدة.</small></span></div>
          <button className="btn" type="button" onClick={intents.retryReconciliation}>
            <RotateCcw size={17} /> إعادة تحديث البيانات
          </button>
        </div>
      ) : null}

      {activeSheet === "sex" ? (
        <ProfileSheet title="اختر الجنس" onClose={intents.closeSheet}>
          <OptionList
            value={draft.sex}
            options={(Object.keys(sexLabels) as Sex[]).map((value) => ({ value, label: sexLabels[value] }))}
            onChoose={(value) => intents.selectSex(value as Sex)}
          />
        </ProfileSheet>
      ) : null}
      {activeSheet === "activity" ? (
        <ProfileSheet title="اختر مستوى النشاط" onClose={intents.closeSheet}>
          <OptionList
            value={draft.activity_level}
            options={(Object.keys(activityLabels) as ActivityLevel[]).map((value) => ({ value, label: activityDisplayLabels[value], description: activityDescriptions[value] }))}
            onChoose={(value) => intents.selectActivity(value as ActivityLevel)}
          />
        </ProfileSheet>
      ) : null}
      {activeSheet === "goal" ? (
        <ProfileSheet title="اختر هدفك" onClose={intents.closeSheet}>
          <OptionList
            value={draft.goal}
            options={(Object.keys(goalLabels) as Goal[]).map((value) => ({ value, label: goalDisplayLabels[value], description: goalDescriptions[value] }))}
            onChoose={(value) => intents.selectGoal(value as Goal)}
          />
        </ProfileSheet>
      ) : null}
      {activeSheet === "calculation" ? (
        <ProfileSheet title="طريقة حساب أهدافك" onClose={intents.closeSheet}>
          <div className="profile-calculation-copy">
            <p>نحسب معدل الأيض الأساسي باستخدام معادلة <bdi dir="ltr">Mifflin–St Jeor</bdi>، ثم نعدله وفق مستوى النشاط والهدف، وبعدها نوزع البروتين والدهون والكربوهيدرات حسب إعداداتك.</p>
            <ul>
              <li>العمر والجنس</li><li>الطول والوزن</li><li>مستوى النشاط</li><li>الهدف</li><li>البروتين لكل كجم</li><li>نسبة الدهون</li>
            </ul>
          </div>
        </ProfileSheet>
      ) : null}

      {restoreOpen ? (
        <ProfileConfirm
          title="استعادة القيم الافتراضية؟"
          description="سيتم استبدال إعدادات البروتين والدهون الحالية."
          safeLabel="إبقاء القيم الحالية"
          confirmLabel="استعادة القيم"
          onClose={intents.cancelRestoreDefaults}
          onConfirm={intents.confirmRestoreDefaults}
        />
      ) : null}

      {(writePhase.kind === "confirming" || writePhase.kind === "submitting") ? (
        <ProfileConfirm
          title="تأكيد الأهداف الجديدة؟"
          description={`المعاينة وحدها لا تحفظ الأهداف. تاريخ السريان ${writePhase.submission.effectiveFrom}.`}
          safeLabel="متابعة المراجعة"
          confirmLabel="حفظ الخطة"
          restoreFocusRef={restoreWriteFocusRef}
          pending={writePhase.kind === "submitting"}
          onClose={intents.cancelWriteConfirmation}
          onConfirm={intents.confirmWrite}
        />
      ) : null}

    </main>

  );
}
