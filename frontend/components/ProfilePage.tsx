"use client";

import {
  Activity,
  CalendarDays,
  Check,
  ChevronDown,
  ChevronLeft,
  Info,
  LoaderCircle,
  RotateCcw,
  Ruler,
  Scale,
  SlidersHorizontal,
  Target,
  UserRound,
  X
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  type FormEvent,
  type ReactNode,
  type RefObject,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import { ApiError, getProfile, previewProfile, saveProfile } from "@/lib/api";
import { activityLabels, goalLabels, sexLabels } from "@/lib/labels";
import { definitionsForTargets, formatNutrientValue, targetTypeLabels } from "@/lib/nutrients";
import type { ActivityLevel, Goal, ProfileInput, ProfileResponse, Sex, TargetResponse } from "@/lib/types";

const PROFILE_READ_ERROR = "تعذر تحميل بياناتك";
const PROFILE_READ_HELP = "تحقق من الاتصال ثم أعد المحاولة";
const PROFILE_WRITE_ERROR = "تعذر حفظ التغييرات";

const PROTEIN_DEFAULT = 1.2;
const FAT_DEFAULTS: Record<Sex, number> = { male: 0.25, female: 0.3 };
const PROFILE_LIMITS = {
  proteinMin: 1,
  proteinMax: 3,
  fatMinPercent: 20,
  fatMaxPercent: 30
} as const;

const activityDescriptions: Record<ActivityLevel, string> = {
  sedentary: "حركة يومية محدودة ولا توجد تمارين منتظمة",
  light: "تمارين خفيفة أو حركة بسيطة خلال الأسبوع",
  moderate: "تمارين منتظمة عدة أيام أسبوعيًا",
  active: "تمارين قوية أو عمل كثير الحركة",
  very_active: "نشاط بدني مكثف أو تدريب شبه يومي"
};

const activityDisplayLabels: Record<ActivityLevel, string> = {
  sedentary: "خامل · مستوى منخفض",
  light: "نشاط خفيف",
  moderate: "نشاط متوسط",
  active: "نشاط مرتفع",
  very_active: "نشاط مرتفع جدًا"
};

const goalDescriptions: Record<Goal, string> = {
  cut: "خفض الدهون تدريجيًا",
  maintain: "الحفاظ على الوزن الحالي",
  bulk: "رفع الوزن والسعرات تدريجيًا"
};

const goalDisplayLabels: Record<Goal, string> = {
  cut: "تنشيف",
  maintain: "المحافظة",
  bulk: "زيادة الوزن"
};

type DraftProfile = {
  sex: Sex;
  birth_date: string;
  height_cm: string;
  weight_kg: string;
  activity_level: ActivityLevel;
  goal: Goal;
  protein_per_kg: string;
  fat_percent: string;
};

type ProfileField = keyof DraftProfile;
type FieldErrors = Partial<Record<ProfileField, string>>;
type SheetKind = "sex" | "activity" | "goal" | "calculation" | null;

function toDraft(profile: ProfileInput): DraftProfile {
  return {
    sex: profile.sex,
    birth_date: profile.birth_date,
    height_cm: formatEditableNumber(profile.height_cm),
    weight_kg: formatEditableNumber(profile.weight_kg),
    activity_level: profile.activity_level,
    goal: profile.goal,
    protein_per_kg: formatEditableNumber(profile.protein_per_kg),
    fat_percent: formatEditableNumber(profile.fat_pct * 100)
  };
}

function blankDraft(): DraftProfile {
  return {
    sex: "male",
    birth_date: "",
    height_cm: "",
    weight_kg: "",
    activity_level: "moderate",
    goal: "cut",
    protein_per_kg: String(PROTEIN_DEFAULT),
    fat_percent: String(FAT_DEFAULTS.male * 100)
  };
}

function formatEditableNumber(value: number): string {
  return Number.isFinite(value) ? String(Number(value.toFixed(2))) : "";
}

function normalizeNumber(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed || !/^(?:\d+\.?\d*|\.\d+)$/.test(trimmed)) return null;
  const number = Number(trimmed);
  return Number.isFinite(number) ? number : null;
}

function normalizeDraft(draft: DraftProfile): string {
  const normalized = {
    ...draft,
    height_cm: normalizeNumber(draft.height_cm),
    weight_kg: normalizeNumber(draft.weight_kg),
    protein_per_kg: normalizeNumber(draft.protein_per_kg),
    fat_percent: normalizeNumber(draft.fat_percent)
  };
  return JSON.stringify(normalized);
}

function validateDraft(draft: DraftProfile): { errors: FieldErrors; payload: ProfileInput | null } {
  const errors: FieldErrors = {};
  const height = normalizeNumber(draft.height_cm);
  const weight = normalizeNumber(draft.weight_kg);
  const protein = normalizeNumber(draft.protein_per_kg);
  const fatPercent = normalizeNumber(draft.fat_percent);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const birth = draft.birth_date ? new Date(`${draft.birth_date}T00:00:00`) : null;

  if (!birth || Number.isNaN(birth.getTime()) || birth > today) errors.birth_date = "اختر تاريخ ميلاد صحيحًا";
  if (height == null || height <= 0) errors.height_cm = "أدخل طولًا صحيحًا";
  if (weight == null || weight <= 0) errors.weight_kg = "أدخل وزنًا صحيحًا";
  if (protein == null || protein < PROFILE_LIMITS.proteinMin || protein > PROFILE_LIMITS.proteinMax) {
    errors.protein_per_kg = "أدخل قيمة صحيحة للبروتين لكل كجم";
  }
  if (fatPercent == null || fatPercent < PROFILE_LIMITS.fatMinPercent || fatPercent > PROFILE_LIMITS.fatMaxPercent) {
    errors.fat_percent = "أدخل نسبة دهون صحيحة";
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
      protein_per_kg: protein,
      fat_pct: fatPercent / 100
    }
  };
}

export function ProfilePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<DraftProfile>(blankDraft);
  const [savedDraft, setSavedDraft] = useState<DraftProfile | null>(null);
  const [savedTargets, setSavedTargets] = useState<TargetResponse | null>(null);
  const [preview, setPreview] = useState<TargetResponse | null>(null);
  const [previewPending, setPreviewPending] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [activeSheet, setActiveSheet] = useState<SheetKind>(null);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [discardHref, setDiscardHref] = useState<string | null>(null);
  const [saveError, setSaveError] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);
  const previewSequence = useRef(0);
  const heightRef = useRef<HTMLInputElement>(null);
  const weightRef = useRef<HTMLInputElement>(null);
  const birthRef = useRef<HTMLInputElement>(null);
  const proteinRef = useRef<HTMLInputElement>(null);
  const fatRef = useRef<HTMLInputElement>(null);

  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: getProfile });

  useEffect(() => {
    if (profileQuery.data === undefined) return;
    const nextDraft = profileQuery.data ? toDraft(profileQuery.data) : blankDraft();
    setDraft(nextDraft);
    setSavedDraft(nextDraft);
    setSavedTargets(profileQuery.data?.targets ?? null);
    setPreview(null);
    setErrors({});
  }, [profileQuery.data]);

  const dirty = savedDraft != null && normalizeDraft(draft) !== normalizeDraft(savedDraft);
  const validation = useMemo(() => validateDraft(draft), [draft]);

  const requestPreview = () => {
    if (!dirty || !validation.payload) {
      setPreview(null);
      setPreviewPending(false);
      setPreviewFailed(false);
      return;
    }
    const sequence = ++previewSequence.current;
    setPreviewPending(true);
    setPreviewFailed(false);
    previewProfile(validation.payload)
      .then((result) => {
        if (sequence !== previewSequence.current) return;
        setPreview(result);
        setPreviewFailed(false);
      })
      .catch(() => {
        if (sequence !== previewSequence.current) return;
        setPreview(null);
        setPreviewFailed(true);
      })
      .finally(() => {
        if (sequence === previewSequence.current) setPreviewPending(false);
      });
  };

  useEffect(() => {
    const timer = window.setTimeout(requestPreview, 400);
    return () => window.clearTimeout(timer);
    // requestPreview intentionally follows the normalized draft and saved baseline.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirty, normalizeDraft(draft)]);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    const interceptNavigation = (event: MouseEvent) => {
      if (!dirty || event.defaultPrevented || event.button !== 0) return;
      const anchor = (event.target as Element | null)?.closest("a[href]") as HTMLAnchorElement | null;
      if (!anchor || anchor.target || anchor.origin !== window.location.origin || anchor.pathname === window.location.pathname) return;
      event.preventDefault();
      event.stopPropagation();
      setDiscardHref(`${anchor.pathname}${anchor.search}${anchor.hash}`);
    };
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", interceptNavigation, true);
    return () => {
      window.removeEventListener("beforeunload", beforeUnload);
      document.removeEventListener("click", interceptNavigation, true);
    };
  }, [dirty]);

  const mutation = useMutation({
    mutationFn: saveProfile,
    onSuccess: (profile: ProfileResponse) => {
      const confirmed = toDraft(profile);
      queryClient.setQueryData(["profile"], profile);
      setDraft(confirmed);
      setSavedDraft(confirmed);
      setSavedTargets(profile.targets);
      setPreview(null);
      setPreviewFailed(false);
      setErrors({});
      setSaveError(false);
      setSavedNotice(true);
      window.setTimeout(() => setSavedNotice(false), 2800);
    },
    onError: (error) => {
      const mapped = mapProfileApiErrors(error);
      if (Object.keys(mapped).length > 0) setErrors(mapped);
      else setSaveError(true);
    }
  });

  function update<K extends keyof DraftProfile>(key: K, value: DraftProfile[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
    setSaveError(false);
    setSavedNotice(false);
  }

  function updateSex(nextSex: Sex) {
    setDraft((current) => {
      const currentFat = normalizeNumber(current.fat_percent);
      const previousDefault = FAT_DEFAULTS[current.sex] * 100;
      return {
        ...current,
        sex: nextSex,
        fat_percent: currentFat === previousDefault ? String(FAT_DEFAULTS[nextSex] * 100) : current.fat_percent
      };
    });
    setErrors((current) => { const next = { ...current }; delete next.sex; delete next.fat_percent; return next; });
    setSaveError(false);
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const result = validateDraft(draft);
    setErrors(result.errors);
    setSaveError(false);
    if (!result.payload) {
      const order: Array<[ProfileField, RefObject<HTMLInputElement | null>]> = [
        ["birth_date", birthRef], ["height_cm", heightRef], ["weight_kg", weightRef],
        ["protein_per_kg", proteinRef], ["fat_percent", fatRef]
      ];
      const invalid = order.find(([field]) => result.errors[field]);
      if (invalid?.[0] === "protein_per_kg" || invalid?.[0] === "fat_percent") setAdvancedOpen(true);
      window.setTimeout(() => invalid?.[1].current?.focus(), 0);
      return;
    }
    if (!mutation.isPending) mutation.mutate(result.payload);
  }

  if (profileQuery.isPending) return <ProfileSkeleton />;
  if (profileQuery.isError) return <ProfileLoadError onRetry={() => profileQuery.refetch()} />;

  const displayBirthDate = draft.birth_date ? formatArabicGregorianDate(draft.birth_date) : "غير محدد";

  return (
    <main className={`profile-page ${dirty ? "is-dirty" : ""}`}>
      <header className="profile-page-head">
        <h1>بياناتك وأهدافك</h1>
        <p>حدّث بياناتك لنحسب احتياجك اليومي.</p>
      </header>

      <form className="profile-form" onSubmit={submit} noValidate>
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
              max={todayIsoDate()}
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

        <TargetsCard title="الأهداف اليومية" badge="محسوبة تلقائيًا" targets={savedTargets} />
        <AdditionalTargetsCard targets={savedTargets} />
        <button className="profile-explain-action" type="button" onClick={() => setActiveSheet("calculation")}><Info size={17} /> كيف حُسبت أهدافي؟</button>

        {dirty && validation.payload ? (
          <ExpectedTargetsCard targets={preview} pending={previewPending} failed={previewFailed} onRetry={requestPreview} />
        ) : null}

      </form>

      {dirty ? (
        <div className="profile-save-bar" role="region" aria-label="حفظ تغييرات الملف الشخصي">
          <span>{Object.keys(errors).length > 0 ? "صحح الحقول المعلّمة للمتابعة" : saveError ? PROFILE_WRITE_ERROR : "تغييرات غير محفوظة"}</span>
          {saveError ? <small>تحقق من الاتصال ثم أعد المحاولة</small> : null}
          <button className="btn primary" type="button" onClick={() => submit()} disabled={mutation.isPending}>
            {mutation.isPending ? <><LoaderCircle className="spin" size={17} /> جارٍ حفظ التغييرات…</> : saveError ? <><RotateCcw size={17} /> إعادة المحاولة</> : "حفظ التغييرات"}
          </button>
        </div>
      ) : null}

      {savedNotice ? <div className="profile-save-status" role="status"><Check size={17} /> تم حفظ التغييرات</div> : null}

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

      {discardHref ? (
        <ProfileConfirm
          title="تجاهل التغييرات؟"
          description="لم يتم حفظ تعديلاتك الحالية."
          safeLabel="متابعة التعديل"
          confirmLabel="تجاهل التغييرات"
          destructive
          onClose={() => setDiscardHref(null)}
          onConfirm={() => { const href = discardHref; setDiscardHref(null); router.push(href); }}
        />
      ) : null}
    </main>
  );
}

function SettingsButton({ icon, label, value, onClick, ariaLabel }: { icon: ReactNode; label: string; value: string; onClick: () => void; ariaLabel: string }) {
  return <button className="profile-setting-row" type="button" onClick={onClick} aria-label={ariaLabel}>{icon}<span className="profile-setting-copy"><strong>{label}</strong><bdi>{value}</bdi></span><ChevronLeft size={18} aria-hidden="true" /></button>;
}

function NumericSettingsRow({ ref, icon, label, value, unit, step, error, help, onChange }: { ref: RefObject<HTMLInputElement | null>; icon?: ReactNode; label: string; value: string; unit: string; step: string; error?: string; help?: string; onChange: (value: string) => void }) {
  const id = `profile-${label.replaceAll(" ", "-")}`;
  return (
    <label className={`profile-setting-row profile-number-row ${error ? "has-error" : ""}`}>
      {icon ?? <span className="profile-row-spacer" />}
      <span className="profile-setting-copy"><strong>{label}</strong>{help ? <small>{help}</small> : null}</span>
      <span className="profile-number-control" dir="ltr"><input ref={ref} id={id} type="text" inputMode="decimal" value={value} onChange={(event) => onChange(event.target.value)} aria-label={label} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : help ? `${id}-help` : undefined} /><bdi>{unit}</bdi></span>
      {error ? <small id={`${id}-error`} className="profile-field-error">{error}</small> : null}
      {help ? <span id={`${id}-help`} className="sr-only">{help}</span> : null}
    </label>
  );
}

function SelectionCard({ icon, title, value, description, onClick, ariaLabel }: { icon: ReactNode; title: string; value: string; description: string; onClick: () => void; ariaLabel: string }) {
  return (
    <section className="profile-selection-card">
      <h2>{title}</h2>
      <button type="button" onClick={onClick} aria-label={ariaLabel}>{icon}<span><strong>{value}</strong><small>{description}</small></span><ChevronLeft size={19} aria-hidden="true" /></button>
    </section>
  );
}

function TargetsCard({ title, badge, targets }: { title: string; badge: string; targets: TargetResponse | null }) {
  return (
    <section className="profile-targets-card" aria-label={title}>
      <header><div><h2>{title}</h2><p>تتحدث بعد حفظ بياناتك.</p></div><span>{badge}</span></header>
      {targets ? (
        <><div className="profile-calorie-target"><strong><bdi>{targets.target_calories}</bdi></strong><span>سعرة حرارية يوميًا</span></div><div className="profile-macro-targets"><TargetValue label="البروتين" value={targets.protein_g} /><TargetValue label="الكارب" value={targets.carb_g} /><TargetValue label="الدهون" value={targets.fat_g} /></div></>
      ) : <div className="profile-incomplete"><strong>أكمل بياناتك لحساب أهدافك اليومية</strong><span>أدخل تاريخ الميلاد والطول والوزن.</span></div>}
    </section>
  );
}

function TargetValue({ label, value }: { label: string; value: number }) {
  return <div><span>{label}</span><strong><bdi dir="ltr">{formatTargetNumber(value)}</bdi> جم</strong></div>;
}

function AdditionalTargetsCard({ targets }: { targets: TargetResponse | null }) {
  if (!targets) return null;
  const definitions = definitionsForTargets(targets);
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

function ExpectedTargetsCard({ targets, pending, failed, onRetry }: { targets: TargetResponse | null; pending: boolean; failed: boolean; onRetry: () => void }) {
  return (
    <section className="profile-preview-card" aria-label="الأهداف المتوقعة بعد الحفظ">
      <header><div><h2>الأهداف المتوقعة بعد الحفظ</h2><p>ستُطبق هذه الأهداف بعد حفظ التغييرات.</p></div><span>معاينة</span></header>
      {pending ? <div className="profile-preview-skeleton" aria-label="جارٍ تحديث معاينة الأهداف" role="status" /> : null}
      {failed ? <div className="profile-preview-error"><strong>تعذر تحديث معاينة الأهداف</strong><button type="button" onClick={onRetry}>إعادة المحاولة</button></div> : null}
      {!pending && !failed && targets ? <div className="profile-preview-values"><strong><bdi>{targets.target_calories}</bdi> سعرة</strong><span>بروتين <bdi dir="ltr">{formatTargetNumber(targets.protein_g)}</bdi> جم</span><span>كارب <bdi dir="ltr">{formatTargetNumber(targets.carb_g)}</bdi> جم</span><span>دهون <bdi dir="ltr">{formatTargetNumber(targets.fat_g)}</bdi> جم</span></div> : null}
    </section>
  );
}

function OptionList({ value, options, onChoose }: { value: string; options: Array<{ value: string; label: string; description?: string }>; onChoose: (value: string) => void }) {
  return <div className="profile-option-list" role="radiogroup">{options.map((option) => <button key={option.value} type="button" role="radio" aria-checked={value === option.value} onClick={() => onChoose(option.value)}><span><strong>{option.label}</strong>{option.description ? <small>{option.description}</small> : null}</span>{value === option.value ? <Check size={19} aria-label="محدد" /> : <span className="profile-radio-dot" />}</button>)}</div>;
}

function ProfileSheet({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    triggerRef.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    closeRef.current?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !panel) return;
      const focusable = [...panel.querySelectorAll<HTMLElement>("button:not(:disabled), input:not(:disabled), [tabindex]:not([tabindex='-1'])")];
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", keydown);
    document.body.classList.add("modal-open");
    return () => { document.removeEventListener("keydown", keydown); document.body.classList.remove("modal-open"); triggerRef.current?.focus(); };
  }, [onClose]);
  return <div className="profile-sheet-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section ref={panelRef} className="profile-sheet" role="dialog" aria-modal="true" aria-labelledby="profile-sheet-title"><div className="profile-sheet-handle" /><header><h2 id="profile-sheet-title">{title}</h2><button ref={closeRef} type="button" onClick={onClose} aria-label={`إغلاق ${title}`}><X size={19} /></button></header><div className="profile-sheet-content">{children}</div></section></div>;
}

function ProfileConfirm({ title, description, safeLabel, confirmLabel, destructive = false, onClose, onConfirm }: { title: string; description: string; safeLabel: string; confirmLabel: string; destructive?: boolean; onClose: () => void; onConfirm: () => void }) {
  return <ProfileSheet title={title} onClose={onClose}><div className="profile-confirm"><p>{description}</p><button className="btn primary" type="button" onClick={onClose}>{safeLabel}</button><button className={destructive ? "btn danger" : "btn"} type="button" onClick={onConfirm}>{confirmLabel}</button></div></ProfileSheet>;
}

function ProfileSkeleton() {
  return <main className="profile-page profile-loading" aria-label="جارٍ تحميل بياناتك"><header className="profile-page-head"><span /><span /></header><div className="profile-card-skeleton tall" /><div className="profile-card-skeleton" /><div className="profile-card-skeleton" /><div className="profile-card-skeleton targets" /></main>;
}

function ProfileLoadError({ onRetry }: { onRetry: () => void }) {
  return <main className="profile-page"><header className="profile-page-head"><h1>بياناتك وأهدافك</h1><p>حدّث بياناتك لنحسب احتياجك اليومي.</p></header><section className="profile-load-error" role="alert"><strong>{PROFILE_READ_ERROR}</strong><span>{PROFILE_READ_HELP}</span><button className="btn" type="button" onClick={onRetry}><RotateCcw size={17} /> إعادة المحاولة</button></section></main>;
}

function formatArabicGregorianDate(input: string): string {
  const [year, month, day] = input.split("-").map(Number);
  if (!year || !month || !day) return "غير محدد";
  return new Intl.DateTimeFormat("ar-SA-u-ca-gregory-nu-latn", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(year, month - 1, day)));
}

function todayIsoDate(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function formatTargetNumber(value: number): string {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, useGrouping: false }).format(value);
}

function mapProfileApiErrors(error: unknown): FieldErrors {
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
