"use client";

import {
  Activity,
  AlertTriangle,
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
import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type FormEvent,
  type ReactNode,
  type RefObject,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState
} from "react";

import { ApiError, activateTargetPlan, getCalendarAuthority, getNutritionRegistry, getProfile, listTargetPlanHistory, previewProfile, replacePendingTargetPlan } from "@/lib/api";
import { activityLabels, goalLabels, sexLabels } from "@/lib/labels";
import { definitionsFromRegistry, formatNutrientValue, targetTypeLabels } from "@/lib/nutrients";
import type { ActivityLevel, CutIntensity, Goal, NutritionRegistryResponse, ProfileInput, ProfileResponse, Sex, TargetPlanActivationResponse, TargetPlanSummary, TargetResponse } from "@/lib/types";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";
import { useUnsavedChanges } from "./UnsavedChangesProvider";

const PROFILE_READ_ERROR = "تعذر تحميل بياناتك";
const PROFILE_READ_HELP = "تحقق من الاتصال ثم أعد المحاولة";
const PROFILE_WRITE_ERROR = "تعذر حفظ التغييرات";
const SPECIALIST_REVIEW_MESSAGE = "لا يمكن تفعيل هذا الهدف لأنه غير مناسب لحالتك الحالية. إذا رغبت في اتباع هذا الهدف، فاستشر أخصائي تغذية قبل اعتماده.";
const VERY_LOW_ENERGY_MESSAGE = "لا يمكن تفعيل هذا الهدف لأن السعرات المستهدفة منخفضة جدًا ولا تحقق الحد الأدنى الآمن المعتمد في النظام.";

const PROTEIN_DEFAULT = 1.2;
const FAT_DEFAULTS: Record<Sex, number> = { male: 0.25, female: 0.3 };
const PROFILE_LIMITS = {
  heightMin: 100,
  heightMax: 250,
  weightMin: 20,
  weightMax: 300,
  proteinMin: 1,
  proteinMax: 3,
  fatMinPercent: 15,
  fatMaxPercent: 40
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
  selected_cut_intensity: CutIntensity;
  protein_per_kg: string;
  fat_percent: string;
};

type ProfileField = keyof DraftProfile;
type FieldErrors = Partial<Record<ProfileField, string>>;
type SheetKind = "sex" | "activity" | "goal" | "calculation" | null;
type ActivationSubmission = {
  payload: ProfileInput;
  preview: TargetResponse & { preview_hash: string };
  idempotencyKey: string;
  replacesPendingPlan: boolean;
};
type ActivationPhase =
  | { kind: "idle" }
  | { kind: "confirming"; submission: ActivationSubmission }
  | { kind: "submitting"; submission: ActivationSubmission }
  | { kind: "reconciling"; submission: ActivationSubmission; accepted: TargetPlanActivationResponse }
  | { kind: "committed"; accepted: TargetPlanActivationResponse }
  | { kind: "recovery"; submission: ActivationSubmission; accepted: TargetPlanActivationResponse }
  | { kind: "failed"; submission: ActivationSubmission };

function toDraft(profile: ProfileInput): DraftProfile {
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

function blankDraft(): DraftProfile {
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

function validateDraft(draft: DraftProfile, authoritativeDate: string | null): { errors: FieldErrors; payload: ProfileInput | null } {
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

type BlockingSafetyOutcome = "specialist_review_required" | "very_low_energy_blocked";

function blockingSafetyMessage(outcome: string): string | null {
  if (outcome === "specialist_review_required") return SPECIALIST_REVIEW_MESSAGE;
  if (outcome === "very_low_energy_blocked") return VERY_LOW_ENERGY_MESSAGE;
  if (outcome !== "normal") return "تعذر التحقق من إمكانية تفعيل هذا الهدف. حدّث المعاينة قبل المتابعة.";
  return null;
}

function isPreviewActivatable(targets: TargetResponse | null): targets is TargetResponse & { preview_hash: string } {
  return Boolean(
    targets?.preview_hash &&
    targets.can_activate === true &&
    targets.safety_outcome === "normal"
  );
}

function profileMatchesAcceptedActivation(
  profile: ProfileResponse,
  submission: ActivationSubmission,
  activation: TargetPlanActivationResponse
): boolean {
  const containsPlan = profile.effective_plan?.id === activation.plan.id || profile.pending_plan?.id === activation.plan.id;
  return containsPlan && normalizeDraft(toDraft(profile)) === normalizeDraft(toDraft(submission.payload));
}

export function ProfilePage() {
  const { session } = useAuth();
  const subjectId = session?.user.id ?? null;
  const accessToken = session?.access_token;
  const sessionSignal = useSessionAbortSignal();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<DraftProfile>(blankDraft);
  const [savedDraft, setSavedDraft] = useState<DraftProfile | null>(null);
  const [savedTargets, setSavedTargets] = useState<TargetResponse | null>(null);
  const [preview, setPreview] = useState<TargetResponse | null>(null);
  const [previewDraftHash, setPreviewDraftHash] = useState<string | null>(null);
  const [previewPending, setPreviewPending] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [activeSheet, setActiveSheet] = useState<SheetKind>(null);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [activationPhase, setActivationPhase] = useState<ActivationPhase>({ kind: "idle" });
  const [pendingServerProfile, setPendingServerProfile] = useState<ProfileResponse | null | undefined>(undefined);
  const [activationErrorCode, setActivationErrorCode] = useState<string | null>(null);
  const [activationSafetyOutcome, setActivationSafetyOutcome] = useState<BlockingSafetyOutcome | null>(null);
  const [safetyAttemptSequence, setSafetyAttemptSequence] = useState(0);
  const previewSequence = useRef(0);
  const heightRef = useRef<HTMLInputElement>(null);
  const weightRef = useRef<HTMLInputElement>(null);
  const birthRef = useRef<HTMLInputElement>(null);
  const proteinRef = useRef<HTMLInputElement>(null);
  const fatRef = useRef<HTMLInputElement>(null);
  const safetyRef = useRef<HTMLDivElement>(null);
  const restoreActivationFocusRef = useRef(true);
  const activationPhaseRef = useRef<ActivationPhase>(activationPhase);
  const mountedRef = useRef(true);
  const formSubjectRef = useRef(subjectId);

  function transitionActivation(next: ActivationPhase) {
    activationPhaseRef.current = next;
    setActivationPhase(next);
  }

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: getProfile });
  const authorityQuery = useQuery({
    queryKey: ["calendar-authority"],
    queryFn: () => getCalendarAuthority({ accessToken: accessToken!, signal: sessionSignal }),
    enabled: Boolean(accessToken)
  });
  const registryQuery = useQuery({
    queryKey: ["nutrition-registry"],
    queryFn: getNutritionRegistry,
    staleTime: 300_000
  });
  const planHistoryQuery = useInfiniteQuery({
    queryKey: ["target-plan-history"],
    queryFn: ({ pageParam }) => listTargetPlanHistory(pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
  });
  const registryReady = registryQuery.data?.registry_schema_version === 2;
  const dirty = savedDraft != null && normalizeDraft(draft) !== normalizeDraft(savedDraft);
  const activationOwnsAuthority = ["reconciling", "recovery", "committed"].includes(activationPhase.kind);

  useEffect(() => {
    if (profileQuery.data === undefined) return;
    if (["reconciling", "recovery"].includes(activationPhaseRef.current.kind)) return;
    const nextDraft = profileQuery.data ? toDraft(profileQuery.data) : blankDraft();
    const responsePhaseOwnsAuthority = ["reconciling", "recovery", "committed"].includes(activationPhaseRef.current.kind);
    if (dirty && !responsePhaseOwnsAuthority) {
      if (normalizeDraft(nextDraft) !== normalizeDraft(savedDraft ?? blankDraft())) {
        // Preserve an in-progress draft when a newer server response arrives.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setPendingServerProfile(profileQuery.data);
      }
      return;
    }
    setDraft(nextDraft);
    setSavedDraft(nextDraft);
    setSavedTargets(profileQuery.data?.targets ?? null);
    setPreview(null);
    setPreviewDraftHash(null);
    setErrors({});
    setPendingServerProfile(undefined);
    // Dirty state is intentionally observed when a response arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileQuery.data]);

  const { requestDiscard } = useUnsavedChanges({
    identity: "profile",
    dirty,
    enabled: !activationOwnsAuthority,
    discard: () => {
      setSavedDraft(draft);
      setPendingServerProfile(undefined);
    }
  });

  useLayoutEffect(() => {
    if (formSubjectRef.current === subjectId) return;
    formSubjectRef.current = subjectId;
    setDraft(blankDraft());
    setSavedDraft(null);
    setSavedTargets(null);
    setPendingServerProfile(undefined);
    setPreview(null);
    setPreviewDraftHash(null);
    setErrors({});
  }, [subjectId]);
  const authoritativeDate = authorityQuery.data?.current_diary_date ?? null;
  const validation = useMemo(
    () => validateDraft(draft, authoritativeDate),
    [draft, authoritativeDate]
  );
  const currentDraftHash = normalizeDraft(draft);
  const currentPreview = previewDraftHash === currentDraftHash ? preview : null;

  const requestPreview = () => {
    if (sessionSignal.aborted) return;
    if (!dirty || !validation.payload || !registryReady) {
      setPreview(null);
      setPreviewDraftHash(null);
      setPreviewPending(false);
      setPreviewFailed(false);
      return;
    }
    const sequence = ++previewSequence.current;
    const requestedDraftHash = currentDraftHash;
    setPreviewPending(true);
    setPreviewFailed(false);
    previewProfile(validation.payload, accessToken, sessionSignal)
      .then((result) => {
        if (sessionSignal.aborted || sequence !== previewSequence.current) return;
        setPreview(result);
        setPreviewDraftHash(requestedDraftHash);
        setPreviewFailed(false);
        setActivationSafetyOutcome(null);
        setSafetyAttemptSequence(0);
      })
      .catch((error) => {
        if (sessionSignal.aborted || sequence !== previewSequence.current) return;
        const mapped = mapProfileApiErrors(error);
        if (Object.keys(mapped).length > 0) {
          setErrors((current) => ({ ...current, ...mapped }));
        }
        setPreview(null);
        setPreviewDraftHash(null);
        setPreviewFailed(true);
      })
      .finally(() => {
        if (!sessionSignal.aborted && sequence === previewSequence.current) setPreviewPending(false);
      });
  };

  useEffect(() => {
    const timer = window.setTimeout(requestPreview, 400);
    return () => window.clearTimeout(timer);
    // requestPreview intentionally follows the normalized draft and saved baseline.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirty, normalizeDraft(draft), registryReady]);

  useEffect(() => {
    if (activationSafetyOutcome) return;
    // Reset the confirmation attempt when the authoritative preview changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSafetyAttemptSequence(0);
    if (activationPhaseRef.current.kind === "confirming") {
      transitionActivation({ kind: "idle" });
    }
  }, [activationSafetyOutcome, currentDraftHash, currentPreview?.preview_hash]);

  useEffect(() => {
    if (safetyAttemptSequence === 0 || ["confirming", "submitting"].includes(activationPhase.kind)) return;
    safetyRef.current?.focus();
  }, [activationPhase.kind, activationSafetyOutcome, currentPreview?.safety_outcome, safetyAttemptSequence]);

  useEffect(() => {
    if (activationPhase.kind !== "committed") return;
    const timer = window.setTimeout(() => transitionActivation({ kind: "idle" }), 2800);
    return () => window.clearTimeout(timer);
  }, [activationPhase.kind]);

  async function reconcileAcceptedActivation(
    submission: ActivationSubmission,
    accepted: TargetPlanActivationResponse
  ) {
    transitionActivation({ kind: "reconciling", submission, accepted });
    try {
      const refreshed = await profileQuery.refetch();
      if (sessionSignal.aborted || !mountedRef.current) return;
      const profile = refreshed.data;
      if (!profile || !profileMatchesAcceptedActivation(profile, submission, accepted)) {
        transitionActivation({ kind: "recovery", submission, accepted });
        return;
      }
      const confirmed = toDraft(profile);
      queryClient.setQueryData(["profile"], profile);
      setDraft(confirmed);
      setSavedDraft(confirmed);
      setSavedTargets(profile.targets ?? accepted.plan.targets);
      setPendingServerProfile(undefined);
      transitionActivation({ kind: "committed", accepted });
    } catch {
      if (!sessionSignal.aborted && mountedRef.current) {
        transitionActivation({ kind: "recovery", submission, accepted });
      }
    }
  }

  async function activateConfirmedPlan() {
    const current = activationPhaseRef.current;
    if (current.kind !== "confirming") return;
    const { submission } = current;
    transitionActivation({ kind: "submitting", submission });
    try {
      const accepted = submission.replacesPendingPlan
        ? await replacePendingTargetPlan(
          submission.payload,
          submission.preview.preview_hash,
          submission.idempotencyKey,
          accessToken,
          sessionSignal
        )
        : await activateTargetPlan(
          submission.payload,
          submission.preview.preview_hash,
          submission.idempotencyKey,
          accessToken,
          sessionSignal
        );
      if (sessionSignal.aborted || !mountedRef.current) return;
      const committedDraft = toDraft(submission.payload);
      setDraft(committedDraft);
      setSavedDraft(committedDraft);
      setSavedTargets(accepted.plan.targets);
      setPendingServerProfile(undefined);
      setPreview(null);
      setPreviewDraftHash(null);
      setPreviewFailed(false);
      setErrors({});
      setActivationErrorCode(null);
      setActivationSafetyOutcome(null);
      setSafetyAttemptSequence(0);
      void queryClient.invalidateQueries({ queryKey: ["target-plan-history"] });
      await reconcileAcceptedActivation(submission, accepted);
    } catch (error) {
      if (sessionSignal.aborted || !mountedRef.current) return;
      const mapped = mapProfileApiErrors(error);
      if (Object.keys(mapped).length > 0) setErrors(mapped);
      else if (error instanceof ApiError && ["SPECIALIST_REVIEW_REQUIRED", "VERY_LOW_ENERGY_TARGET_BLOCKED"].includes(error.code ?? "")) {
        restoreActivationFocusRef.current = false;
        setActivationSafetyOutcome(
          error.code === "SPECIALIST_REVIEW_REQUIRED"
            ? "specialist_review_required"
            : "very_low_energy_blocked"
        );
        setActivationErrorCode(error.code ?? null);
        setPreview(null);
        setPreviewDraftHash(null);
        setPreviewFailed(false);
        setSafetyAttemptSequence((sequence) => sequence + 1);
        transitionActivation({ kind: "idle" });
      }
      else if (error instanceof ApiError && ["PREVIEW_RESULT_CHANGED", "IDEMPOTENCY_KEY_REUSED"].includes(error.code ?? "")) {
        setActivationErrorCode(error.code ?? null);
        setPreview(null);
        setPreviewDraftHash(null);
        transitionActivation({ kind: "idle" });
        requestPreview();
      } else {
        transitionActivation({ kind: "failed", submission });
      }
    } finally {
      if (activationPhaseRef.current.kind === "submitting") {
        activationPhaseRef.current = { kind: "idle" };
        if (mountedRef.current) {
          setActivationPhase({ kind: "idle" });
        }
      }
    }
  }

  function update<K extends keyof DraftProfile>(key: K, value: DraftProfile[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setErrors((current) => {
      const next = { ...current };
      delete next[key];
      return next;
    });
    transitionActivation({ kind: "idle" });
    setActivationErrorCode(null);
    setActivationSafetyOutcome(null);
    setSafetyAttemptSequence(0);
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
    transitionActivation({ kind: "idle" });
    setActivationErrorCode(null);
    setActivationSafetyOutcome(null);
    setSafetyAttemptSequence(0);
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const result = validateDraft(draft, authoritativeDate);
    setErrors(result.errors);
    if (!registryReady) return;
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
    if (!currentPreview?.preview_hash) {
      requestPreview();
      return;
    }
    if (!isPreviewActivatable(currentPreview)) {
      setSafetyAttemptSequence((current) => current + 1);
      transitionActivation({ kind: "idle" });
      return;
    }
    restoreActivationFocusRef.current = true;
    const failedSubmission = activationPhaseRef.current.kind === "failed"
      ? activationPhaseRef.current.submission
      : null;
    const idempotencyKey = failedSubmission &&
      normalizeDraft(toDraft(failedSubmission.payload)) === normalizeDraft(toDraft(result.payload)) &&
      failedSubmission.preview.preview_hash === currentPreview.preview_hash
      ? failedSubmission.idempotencyKey
      : crypto.randomUUID();
    transitionActivation({
      kind: "confirming",
      submission: {
        payload: result.payload,
        preview: currentPreview,
        idempotencyKey,
        replacesPendingPlan: Boolean(profileQuery.data?.pending_plan)
      }
    });
  }

  if (profileQuery.isPending || authorityQuery.isPending) return <ProfileSkeleton />;
  if ((profileQuery.isError && savedDraft === null) || authorityQuery.isError) return <ProfileLoadError onRetry={() => {
    profileQuery.refetch();
    authorityQuery.refetch();
  }} />;

  const displayBirthDate = draft.birth_date ? formatArabicGregorianDate(draft.birth_date) : "غير محدد";

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

        <TargetsCard title="الأهداف اليومية" badge="محسوبة تلقائيًا" targets={savedTargets} />
        {profileQuery.data?.pending_plan ? <ScheduledPlanCard plan={profileQuery.data.pending_plan} /> : null}
        {registryQuery.isPending ? <RegistryState kind="loading" /> : registryQuery.isError ? <RegistryState kind="unavailable" onRetry={() => registryQuery.refetch()} /> : !registryReady ? <RegistryState kind="incompatible" onRetry={() => registryQuery.refetch()} /> : <AdditionalTargetsCard targets={savedTargets} registry={registryQuery.data} />}
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
            recoveryOutcome={activationSafetyOutcome}
            safetyAttemptSequence={safetyAttemptSequence}
            safetyRef={safetyRef}
            onRetry={requestPreview}
          />
        ) : null}

      </form>

      {dirty ? (
        <div className="profile-save-bar" role="region" aria-label="حفظ تغييرات الملف الشخصي">
          <span>{Object.keys(errors).length > 0 ? "صحح الحقول المعلّمة للمتابعة" : activationSafetyOutcome ? "راجع قرار السلامة وحدّث المعاينة قبل المتابعة" : activationErrorCode ? "تغيّرت المعاينة. راجع الأهداف المحدثة ثم أكد مجددًا" : activationPhase.kind === "failed" ? PROFILE_WRITE_ERROR : !registryReady ? "سجل التغذية غير جاهز" : "تغييرات غير محفوظة"}</span>
          {activationPhase.kind === "failed" ? <small>تحقق من الاتصال ثم أعد المحاولة</small> : null}
          <button className="btn primary" type="button" onClick={() => submit()} disabled={!registryReady || activationPhase.kind === "submitting" || previewPending || (Boolean(validation.payload) && !currentPreview?.preview_hash && !activationSafetyOutcome)}>
            {activationPhase.kind === "submitting" ? <><LoaderCircle className="spin" size={17} /> جارٍ تفعيل الخطة…</> : activationSafetyOutcome ? "تحديث المعاينة" : activationErrorCode ? "مراجعة المعاينة" : activationPhase.kind === "failed" ? <><RotateCcw size={17} /> إعادة المحاولة</> : "مراجعة وتأكيد"}
          </button>
        </div>
      ) : null}

      {["reconciling", "committed"].includes(activationPhase.kind) ? <div className="profile-save-status" role="status"><Check size={17} /> تم حفظ التغييرات</div> : null}
      {activationPhase.kind === "recovery" ? (
        <div className="profile-reconciliation-status" role="status">
          <div><Check size={17} /><span><strong>تم حفظ التغييرات</strong><small>تعذر تحديث البيانات المعروضة. الأهداف المحفوظة أدناه ما زالت معتمدة.</small></span></div>
          <button className="btn" type="button" onClick={() => void reconcileAcceptedActivation(activationPhase.submission, activationPhase.accepted)}>
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

      {(activationPhase.kind === "confirming" || activationPhase.kind === "submitting") ? (
        <ProfileConfirm
          title={activationPhase.submission.replacesPendingPlan ? "استبدال الخطة المجدولة؟" : "تأكيد الأهداف الجديدة؟"}
          description={activationPhase.submission.replacesPendingPlan
            ? "سيتم الاحتفاظ بالخطة المجدولة السابقة في السجل، وتبدأ الخطة البديلة في التاريخ المعروض."
            : `المعاينة وحدها لا تحفظ الأهداف. ستبدأ الخطة في ${profileQuery.data ? "اليوم التالي" : "اليوم"}.`}
          safeLabel="متابعة المراجعة"
          confirmLabel={activationPhase.submission.replacesPendingPlan ? "استبدال الخطة" : "تفعيل الخطة"}
          restoreFocusRef={restoreActivationFocusRef}
          pending={activationPhase.kind === "submitting"}
          onClose={() => {
            if (activationPhaseRef.current.kind === "confirming") transitionActivation({ kind: "idle" });
          }}
          onConfirm={() => void activateConfirmedPlan()}
        />
      ) : null}

    </main>
  );
}

function SettingsButton({ icon, label, value, onClick, ariaLabel }: { icon: ReactNode; label: string; value: string; onClick: () => void; ariaLabel: string }) {
  return <button className="profile-setting-row" type="button" onClick={onClick} aria-label={ariaLabel}>{icon}<span className="profile-setting-copy"><strong>{label}</strong><bdi>{value}</bdi></span><ChevronLeft size={18} aria-hidden="true" /></button>;
}

function NumericSettingsRow({ ref, icon, label, value, unit, step, min, max, error, help, onChange }: { ref: RefObject<HTMLInputElement | null>; icon?: ReactNode; label: string; value: string; unit: string; step: string; min?: number; max?: number; error?: string; help?: string; onChange: (value: string) => void }) {
  const id = `profile-${label.replaceAll(" ", "-")}`;
  return (
    <label className={`profile-setting-row profile-number-row ${error ? "has-error" : ""}`}>
      {icon ?? <span className="profile-row-spacer" />}
      <span className="profile-setting-copy"><strong>{label}</strong>{help ? <small>{help}</small> : null}</span>
      <span className="profile-number-control" dir="ltr"><input ref={ref} id={id} type="text" inputMode="decimal" value={value} min={min} max={max} step={step} onChange={(event) => onChange(event.target.value)} aria-label={label} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : help ? `${id}-help` : undefined} /><bdi>{unit}</bdi></span>
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

const cutIntensityOptions: Array<{ value: CutIntensity; label: string; percent: string; recommended?: boolean }> = [
  { value: 0.15, label: "خفيف", percent: "15%" },
  { value: 0.2, label: "عادي", percent: "20%", recommended: true },
  { value: 0.25, label: "قوي", percent: "25%" }
];

function CutIntensitySelector({ value, onChange }: { value: CutIntensity; onChange: (value: CutIntensity) => void }) {
  return (
    <fieldset className="profile-cut-intensity" role="radiogroup">
      <legend>شدة خفض الوزن</legend>
      <div className="profile-cut-intensity-options">
        {cutIntensityOptions.map((option) => (
          <label key={option.value}>
            <input
              type="radio"
              name="profile-cut-intensity"
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            <span>
              <strong>{option.label}</strong>
              <bdi dir="ltr">{option.percent}</bdi>
              {option.recommended ? <small>موصى به</small> : null}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
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

function AdditionalTargetsCard({ targets, registry }: { targets: TargetResponse | null; registry: NutritionRegistryResponse }) {
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

function RegistryState({ kind, onRetry }: { kind: "loading" | "unavailable" | "incompatible"; onRetry?: () => void }) {
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

function TargetPlanHistory({ plans, pending, failed, hasMore, loadingMore, onRetry, onLoadMore }: { plans: TargetPlanSummary[]; pending: boolean; failed: boolean; hasMore: boolean; loadingMore: boolean; onRetry: () => void; onLoadMore: () => void }) {
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

function ScheduledPlanCard({ plan }: { plan: NonNullable<ProfileResponse["pending_plan"]> }) {
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

function ExpectedTargetsCard({
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

function OptionList({ value, options, onChoose }: { value: string; options: Array<{ value: string; label: string; description?: string }>; onChoose: (value: string) => void }) {
  return <div className="profile-option-list" role="radiogroup">{options.map((option) => <button key={option.value} type="button" role="radio" aria-checked={value === option.value} onClick={() => onChoose(option.value)}><span><strong>{option.label}</strong>{option.description ? <small>{option.description}</small> : null}</span>{value === option.value ? <Check size={19} aria-label="محدد" /> : <span className="profile-radio-dot" />}</button>)}</div>;
}

function ProfileSheet({ title, children, onClose, restoreFocusRef, dismissible = true, busy = false }: { title: string; children: ReactNode; onClose: () => void; restoreFocusRef?: RefObject<boolean>; dismissible?: boolean; busy?: boolean }) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  const dismissibleRef = useRef(dismissible);
  useEffect(() => {
    onCloseRef.current = onClose;
    dismissibleRef.current = dismissible;
  }, [dismissible, onClose]);
  useEffect(() => {
    triggerRef.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    closeRef.current?.focus();
    const keydown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        if (dismissibleRef.current) onCloseRef.current();
      }
      if (event.key !== "Tab" || !panel) return;
      const focusable = [...panel.querySelectorAll<HTMLElement>("button:not(:disabled), input:not(:disabled), [tabindex]:not([tabindex='-1'])")];
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", keydown);
    document.body.classList.add("modal-open");
    return () => {
      document.removeEventListener("keydown", keydown);
      document.body.classList.remove("modal-open");
      if (restoreFocusRef?.current !== false) triggerRef.current?.focus();
    };
  }, [restoreFocusRef]);
  useEffect(() => {
    if (busy) panelRef.current?.focus();
  }, [busy]);
  return <div className="profile-sheet-backdrop" role="presentation" onMouseDown={(event) => { if (dismissible && event.target === event.currentTarget) onClose(); }}><section ref={panelRef} className="profile-sheet" role="dialog" aria-modal="true" aria-labelledby="profile-sheet-title" aria-busy={busy || undefined} tabIndex={-1}><div className="profile-sheet-handle" /><header><h2 id="profile-sheet-title">{title}</h2><button ref={closeRef} type="button" onClick={onClose} aria-label={`إغلاق ${title}`} disabled={!dismissible}><X size={19} /></button></header><div className="profile-sheet-content">{children}</div></section></div>;
}

function ProfileConfirm({ title, description, safeLabel, confirmLabel, destructive = false, pending = false, onClose, onConfirm, restoreFocusRef }: { title: string; description: string; safeLabel: string; confirmLabel: string; destructive?: boolean; pending?: boolean; onClose: () => void; onConfirm: () => void; restoreFocusRef?: RefObject<boolean> }) {
  return <ProfileSheet title={title} onClose={onClose} restoreFocusRef={restoreFocusRef} dismissible={!pending} busy={pending}><div className="profile-confirm"><p>{description}</p><button className="btn primary" type="button" onClick={onClose} disabled={pending}>{safeLabel}</button><button className={destructive ? "btn danger" : "btn"} type="button" onClick={onConfirm} disabled={pending}>{pending ? <><LoaderCircle className="spin" size={17} /> جارٍ التفعيل…</> : confirmLabel}</button></div></ProfileSheet>;
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
