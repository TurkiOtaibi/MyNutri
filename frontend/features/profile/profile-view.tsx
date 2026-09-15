import { Activity, CalendarDays, Check, ChevronDown, ChevronLeft, Info, LoaderCircle, RotateCcw, Ruler, Scale, SlidersHorizontal, Target, UserRound } from "lucide-react";
import type { Dispatch, FormEvent, RefObject, SetStateAction } from "react";
import { activityLabels, goalLabels, sexLabels } from "@/lib/labels";
import type { ActivityLevel, Goal, NutritionRegistryResponse, ProfileInput, ProfileResponse, Sex, TargetPlanHistoryResponse, TargetPlanWriteResponse, TargetResponse } from "@/lib/types";
import { NumericSettingsRow, OptionList, SelectionCard, SettingsButton, CutIntensitySelector } from "./profile-controls";
import { AdditionalTargetsCard, ExpectedTargetsCard, RegistryState, TargetPlanHistory, TargetsCard } from "./profile-targets";
import { ProfileConfirm, ProfileSheet } from "./profile-dialogs";
import { FAT_DEFAULTS, PROFILE_LIMITS, PROTEIN_DEFAULT, activityDescriptions, activityDisplayLabels, blankDraft, goalDescriptions, goalDisplayLabels, normalizeNumber, toDraft, type BlockingSafetyOutcome, type DraftProfile, type FieldErrors, type SheetKind, type TargetPlanSubmission, type TargetPlanWritePhase } from "./profile-model";
import "./profile.module.css";

const PROFILE_WRITE_ERROR = "تعذر حفظ التغييرات";

type ProfileViewProps = {
  dirty: boolean;
  pendingServerProfile: ProfileResponse | null | undefined;
  setPendingServerProfile: Dispatch<SetStateAction<ProfileResponse | null | undefined>>;
  requestDiscard: (continueAction: () => void) => void;
  setDraft: Dispatch<SetStateAction<DraftProfile>>;
  setSavedDraft: Dispatch<SetStateAction<DraftProfile | null>>;
  setSavedTargets: Dispatch<SetStateAction<TargetResponse | null>>;
  setPreview: Dispatch<SetStateAction<TargetResponse | null>>;
  setPreviewDraftHash: Dispatch<SetStateAction<string | null>>;
  setErrors: Dispatch<SetStateAction<FieldErrors>>;
  draft: DraftProfile;
  effectiveFrom: string;
  setEffectiveFrom: (value: string) => void;
  effectiveFromRef: RefObject<HTMLInputElement | null>;
  activeSheet: SheetKind;
  updateSex: (sex: Sex) => void;
  setActiveSheet: Dispatch<SetStateAction<SheetKind>>;
  errors: FieldErrors;
  birthRef: RefObject<HTMLInputElement | null>;
  authoritativeDate: string | null;
  displayBirthDate: string;
  heightRef: RefObject<HTMLInputElement | null>;
  weightRef: RefObject<HTMLInputElement | null>;
  update: <K extends keyof DraftProfile>(key: K, value: DraftProfile[K]) => void;
  advancedOpen: boolean;
  setAdvancedOpen: Dispatch<SetStateAction<boolean>>;
  proteinRef: RefObject<HTMLInputElement | null>;
  fatRef: RefObject<HTMLInputElement | null>;
  savedTargets: TargetResponse | null;
  registryQuery: { isPending: boolean; isError: boolean; data: NutritionRegistryResponse | undefined; refetch: () => unknown };
  registryReady: boolean;
  planHistoryQuery: { data: { pages: TargetPlanHistoryResponse[] } | undefined; isPending: boolean; isError: boolean; hasNextPage: boolean; isFetchingNextPage: boolean; refetch: () => unknown; fetchNextPage: () => unknown };
  currentPreview: TargetResponse | null;
  previewPending: boolean;
  previewFailed: boolean;
  writeSafetyOutcome: BlockingSafetyOutcome | null;
  safetyAttemptSequence: number;
  safetyRef: RefObject<HTMLDivElement | null>;
  requestPreview: () => void;
  validation: { payload: ProfileInput | null };
  writeErrorCode: string | null;
  writePhase: TargetPlanWritePhase;
  submit: (event?: FormEvent) => void;
  reconcileAcceptedPlan: (submission: TargetPlanSubmission, accepted: TargetPlanWriteResponse) => Promise<void>;
  restoreOpen: boolean;
  setRestoreOpen: Dispatch<SetStateAction<boolean>>;
  transitionWrite: (next: TargetPlanWritePhase) => void;
  writePhaseRef: RefObject<TargetPlanWritePhase>;
  restoreWriteFocusRef: RefObject<boolean>;
  writeConfirmedPlan: () => Promise<void>;
};

export function ProfileView({
  dirty,
  pendingServerProfile,
  setPendingServerProfile,
  requestDiscard,
  setDraft,
  setSavedDraft,
  setSavedTargets,
  setPreview,
  setPreviewDraftHash,
  setErrors,
  draft,
  effectiveFrom,
  setEffectiveFrom,
  effectiveFromRef,
  activeSheet,
  updateSex,
  setActiveSheet,
  errors,
  birthRef,
  authoritativeDate,
  displayBirthDate,
  heightRef,
  weightRef,
  update,
  advancedOpen,
  setAdvancedOpen,
  proteinRef,
  fatRef,
  savedTargets,
  registryQuery,
  registryReady,
  planHistoryQuery,
  currentPreview,
  previewPending,
  previewFailed,
  writeSafetyOutcome,
  safetyAttemptSequence,
  safetyRef,
  requestPreview,
  validation,
  writeErrorCode,
  writePhase,
  submit,
  reconcileAcceptedPlan,
  restoreOpen,
  setRestoreOpen,
  transitionWrite,
  writePhaseRef,
  restoreWriteFocusRef,
  writeConfirmedPlan,
}: ProfileViewProps) {
  return (
    <main className={`profile-page ${dirty ? "is-dirty" : ""}`}>
      <header className="profile-page-head">
        <h1>بياناتك وأهدافك</h1>
        <p>حدّث بياناتك لنحسب احتياجك اليومي.</p>
      </header>

      <form className="profile-form" onSubmit={submit} noValidate>
        {pendingServerProfile !== undefined ? (
          <div className="unsaved-conflict" role="status">
            <p>توجد نسخة أحدث من بيانات الملف على الخادم. احتفظنا بتعديلاتك الحالية.</p>
            <div className="actions">
              <button className="btn" type="button" onClick={() => setPendingServerProfile(undefined)}>الاحتفاظ بتعديلاتي</button>
              <button className="btn danger" type="button" onClick={() => requestDiscard(() => {
                const nextDraft = pendingServerProfile ? toDraft(pendingServerProfile) : blankDraft();
                setDraft(nextDraft);
                setSavedDraft(nextDraft);
                setSavedTargets(pendingServerProfile?.targets ?? null);
                setPreview(null);
                setPreviewDraftHash(null);
                setErrors({});
                setPendingServerProfile(undefined);
              })}>تحميل نسخة الخادم</button>
            </div>
          </div>
        ) : null}
        <section className="profile-settings-card body-data-card" aria-labelledby="body-data-title">
          <h2 id="body-data-title">بيانات الجسم</h2>
          <SettingsButton
            icon={<UserRound size={19} />}
            label="الجنس"
            value={sexLabels[draft.sex]}
            onClick={() => setActiveSheet("sex")}
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
              onChange={(event) => update("birth_date", event.target.value)}
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
            onChange={(value) => update("height_cm", value)}
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
            onChange={(value) => update("weight_kg", value)}
          />
        </section>

        <SelectionCard
          icon={<Activity size={20} />}
          title="مستوى النشاط"
          value={activityDisplayLabels[draft.activity_level]}
          description={activityDescriptions[draft.activity_level]}
          onClick={() => setActiveSheet("activity")}
          ariaLabel={`تغيير مستوى النشاط، القيمة الحالية ${activityLabels[draft.activity_level]}`}
        />

        <SelectionCard
          icon={<Target size={20} />}
          title="الهدف"
          value={goalDisplayLabels[draft.goal]}
          description={goalDescriptions[draft.goal]}
          onClick={() => setActiveSheet("goal")}
          ariaLabel={`تغيير الهدف، القيمة الحالية ${goalLabels[draft.goal]}`}
        />

        {draft.goal === "cut" ? (
          <CutIntensitySelector
            value={draft.selected_cut_intensity}
            onChange={(value) => update("selected_cut_intensity", value)}
          />
        ) : null}

        <section className={`profile-advanced ${advancedOpen ? "open" : ""}`}>
          <button
            className="profile-advanced-toggle"
            type="button"
            aria-expanded={advancedOpen}
            aria-controls="advanced-profile-fields"
            aria-label={`${advancedOpen ? "إغلاق" : "فتح"} الخيارات المتقدمة`}
            onClick={() => setAdvancedOpen((current) => !current)}
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
              onChange={(value) => update("protein_per_kg", value)}
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
              onChange={(value) => update("fat_percent", value)}
            />
            <p className="profile-advanced-notice">تغيير هذه القيم سيؤثر في أهداف البروتين والدهون اليومية.</p>
            <button
              className="profile-text-action"
              type="button"
              onClick={() => {
                const defaultsAlreadySet = normalizeNumber(draft.protein_per_kg) === PROTEIN_DEFAULT && normalizeNumber(draft.fat_percent) === FAT_DEFAULTS[draft.sex] * 100;
                if (defaultsAlreadySet) return;
                setRestoreOpen(true);
              }}
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
              onChange={(event) => setEffectiveFrom(event.target.value)}
              aria-label="تاريخ سريان الأهداف"
              aria-invalid={Boolean(errors.effective_from)}
              aria-describedby={errors.effective_from ? "effective-from-error" : undefined}
            />
            {errors.effective_from ? <small id="effective-from-error" className="profile-field-error">{errors.effective_from}</small> : null}
          </label>
        </section>

        <TargetsCard title="الأهداف اليومية" badge="محسوبة تلقائيًا" targets={savedTargets} />
        {registryQuery.isPending ? <RegistryState kind="loading" /> : registryQuery.isError ? <RegistryState kind="unavailable" onRetry={() => registryQuery.refetch()} /> : !registryReady ? <RegistryState kind="incompatible" onRetry={() => registryQuery.refetch()} /> : <AdditionalTargetsCard targets={savedTargets} registry={registryQuery.data!} />}
        <TargetPlanHistory
          plans={planHistoryQuery.data?.pages.flatMap((page) => page.items) ?? []}
          pending={planHistoryQuery.isPending}
          failed={planHistoryQuery.isError}
          hasMore={planHistoryQuery.hasNextPage}
          loadingMore={planHistoryQuery.isFetchingNextPage}
          onRetry={() => planHistoryQuery.refetch()}
          onLoadMore={() => planHistoryQuery.fetchNextPage()}
        />
        <button className="profile-explain-action" type="button" onClick={() => setActiveSheet("calculation")}><Info size={17} /> كيف حُسبت أهدافي؟</button>

        {dirty && validation.payload ? (
          <ExpectedTargetsCard
            targets={currentPreview}
            goal={draft.goal}
            pending={previewPending}
            failed={previewFailed}
            recoveryOutcome={writeSafetyOutcome}
            safetyAttemptSequence={safetyAttemptSequence}
            safetyRef={safetyRef}
            onRetry={requestPreview}
          />
        ) : null}

      </form>

      {dirty ? (
        <div className="profile-save-bar" role="region" aria-label="حفظ تغييرات الملف الشخصي">
          <span>{Object.keys(errors).length > 0 ? "صحح الحقول المعلّمة للمتابعة" : writeSafetyOutcome ? "راجع قرار السلامة وحدّث المعاينة قبل المتابعة" : writeErrorCode ? "تغيّرت المعاينة. راجع الأهداف المحدثة ثم أكد مجددًا" : writePhase.kind === "failed" ? PROFILE_WRITE_ERROR : !registryReady ? "سجل التغذية غير جاهز" : "تغييرات غير محفوظة"}</span>
          {writePhase.kind === "failed" ? <small>تحقق من الاتصال ثم أعد المحاولة</small> : null}
          <button className="btn primary" type="button" onClick={() => submit()} disabled={!registryReady || writePhase.kind === "submitting" || previewPending || (Boolean(validation.payload) && !currentPreview?.preview_hash && !writeSafetyOutcome)}>
            {writePhase.kind === "submitting" ? <><LoaderCircle className="spin" size={17} /> جارٍ حفظ الخطة…</> : writeSafetyOutcome ? "تحديث المعاينة" : writeErrorCode ? "مراجعة المعاينة" : writePhase.kind === "failed" ? <><RotateCcw size={17} /> إعادة المحاولة</> : "مراجعة وتأكيد"}
          </button>
        </div>
      ) : null}

      {["reconciling", "committed"].includes(writePhase.kind) ? <div className="profile-save-status" role="status"><Check size={17} /> تم حفظ التغييرات</div> : null}
      {writePhase.kind === "recovery" ? (
        <div className="profile-reconciliation-status" role="status">
          <div><Check size={17} /><span><strong>تم حفظ التغييرات</strong><small>تعذر تحديث البيانات المعروضة. الأهداف المحفوظة أدناه ما زالت معتمدة.</small></span></div>
          <button className="btn" type="button" onClick={() => void reconcileAcceptedPlan(writePhase.submission, writePhase.accepted)}>
            <RotateCcw size={17} /> إعادة تحديث البيانات
          </button>
        </div>
      ) : null}

      {activeSheet === "sex" ? (
        <ProfileSheet title="اختر الجنس" onClose={() => setActiveSheet(null)}>
          <OptionList
            value={draft.sex}
            options={(Object.keys(sexLabels) as Sex[]).map((value) => ({ value, label: sexLabels[value] }))}
            onChoose={(value) => { updateSex(value as Sex); setActiveSheet(null); }}
          />
        </ProfileSheet>
      ) : null}
      {activeSheet === "activity" ? (
        <ProfileSheet title="اختر مستوى النشاط" onClose={() => setActiveSheet(null)}>
          <OptionList
            value={draft.activity_level}
            options={(Object.keys(activityLabels) as ActivityLevel[]).map((value) => ({ value, label: activityDisplayLabels[value], description: activityDescriptions[value] }))}
            onChoose={(value) => { update("activity_level", value as ActivityLevel); setActiveSheet(null); }}
          />
        </ProfileSheet>
      ) : null}
      {activeSheet === "goal" ? (
        <ProfileSheet title="اختر هدفك" onClose={() => setActiveSheet(null)}>
          <OptionList
            value={draft.goal}
            options={(Object.keys(goalLabels) as Goal[]).map((value) => ({ value, label: goalDisplayLabels[value], description: goalDescriptions[value] }))}
            onChoose={(value) => { update("goal", value as Goal); setActiveSheet(null); }}
          />
        </ProfileSheet>
      ) : null}
      {activeSheet === "calculation" ? (
        <ProfileSheet title="طريقة حساب أهدافك" onClose={() => setActiveSheet(null)}>
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
          onClose={() => setRestoreOpen(false)}
          onConfirm={() => {
            update("protein_per_kg", String(PROTEIN_DEFAULT));
            update("fat_percent", String(FAT_DEFAULTS[draft.sex] * 100));
            setRestoreOpen(false);
          }}
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
          onClose={() => {
            if (writePhaseRef.current.kind === "confirming") transitionWrite({ kind: "idle" });
          }}
          onConfirm={() => void writeConfirmedPlan()}
        />
      ) : null}

    </main>

  );
}
