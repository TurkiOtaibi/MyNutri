"use client";

import { useInfiniteQuery, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type FormEvent,
  type RefObject,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState
} from "react";

import { ApiError, getCalendarAuthority, getNutritionRegistry, getProfile, listTargetPlanHistory, previewProfile, writeTargetPlan } from "@/lib/api";
import type { ActivityLevel, Goal, ProfileResponse, Sex, TargetPlanWriteResponse, TargetResponse } from "@/lib/types";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";
import { useUnsavedChanges } from "./UnsavedChangesProvider";
import { ProfileLoadError, ProfileSkeleton } from "@/features/profile/profile-dialogs";
import { ProfileView } from "@/features/profile/profile-view";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";
import { FAT_DEFAULTS, PROTEIN_DEFAULT, blankDraft, didConfirmedBirthDateChange, formatArabicGregorianDate, isPreviewActivatable, mapProfileApiErrors, normalizeDraft, normalizeNumber, profileMatchesAcceptedPlan, targetPlanSubmissionMatches, toDraft, validateDraft, withUpdatedSex, withoutProfileFieldError, type BlockingSafetyOutcome, type DraftProfile, type FieldErrors, type ProfileField, type SheetKind, type TargetPlanSubmission, type TargetPlanWritePhase } from "@/features/profile/profile-model";

export function ProfilePage() {
  const { session } = useAuth();
  const subjectId = session?.user.id ?? null;
  const accessToken = session?.access_token;
  const sessionSignal = useSessionAbortSignal();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<DraftProfile>(blankDraft);
  const [savedDraft, setSavedDraft] = useState<DraftProfile | null>(null);
  const [hasSavedProfile, setHasSavedProfile] = useState(false);
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [savedEffectiveFrom, setSavedEffectiveFrom] = useState<string | null>(null);
  const [savedTargets, setSavedTargets] = useState<TargetResponse | null>(null);
  const [preview, setPreview] = useState<TargetResponse | null>(null);
  const [previewDraftHash, setPreviewDraftHash] = useState<string | null>(null);
  const [previewPending, setPreviewPending] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [activeSheet, setActiveSheet] = useState<SheetKind>(null);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [writePhase, setWritePhase] = useState<TargetPlanWritePhase>({ kind: "idle" });
  const [pendingServerProfile, setPendingServerProfile] = useState<ProfileResponse | null | undefined>(undefined);
  const [writeErrorCode, setWriteErrorCode] = useState<string | null>(null);
  const [writeSafetyOutcome, setWriteSafetyOutcome] = useState<BlockingSafetyOutcome | null>(null);
  const [safetyAttemptSequence, setSafetyAttemptSequence] = useState(0);
  const previewSequence = useRef(0);
  const heightRef = useRef<HTMLInputElement>(null);
  const weightRef = useRef<HTMLInputElement>(null);
  const birthRef = useRef<HTMLInputElement>(null);
  const sexRef = useRef<HTMLDivElement>(null);
  const proteinRef = useRef<HTMLInputElement>(null);
  const fatRef = useRef<HTMLInputElement>(null);
  const safetyRef = useRef<HTMLDivElement>(null);
  const effectiveFromRef = useRef<HTMLInputElement>(null);
  const restoreWriteFocusRef = useRef(true);
  const writePhaseRef = useRef<TargetPlanWritePhase>(writePhase);
  const mountedRef = useRef(true);
  const formSubjectRef = useRef(subjectId);
  const savedProfileSubjectRef = useRef<string | null | undefined>(undefined);

  function transitionWrite(next: TargetPlanWritePhase) {
    writePhaseRef.current = next;
    setWritePhase(next);
  }

  function focusMappedProfileError(mapped: FieldErrors) {
    const target = mapped.sex ? sexRef : mapped.birth_date ? birthRef : null;
    if (target) window.setTimeout(() => target.current?.focus(), 0);
  }

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  const profileQueryKey = ["profile", subjectId] as const;
  const profileQuery = useQuery({
    queryKey: profileQueryKey,
    queryFn: getProfile,
    enabled: Boolean(accessToken)
  });
  const authorityQuery = useQuery({
    queryKey: ["calendar-authority", subjectId],
    queryFn: () => getCalendarAuthority({ accessToken: accessToken!, signal: sessionSignal }),
    enabled: Boolean(accessToken)
  });
  const registryQuery = useQuery({
    queryKey: ["nutrition-registry"],
    queryFn: getNutritionRegistry,
    staleTime: 300_000
  });
  const planHistoryQuery = useInfiniteQuery({
    queryKey: ["target-plan-history", subjectId],
    queryFn: ({ pageParam }) => listTargetPlanHistory(pageParam),
    initialPageParam: null as string | null,
    enabled: Boolean(accessToken),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined
  });
  const registryReady = Boolean(registryQuery.data);
  const authoritativeDate = authorityQuery.data?.current_diary_date ?? null;
  const selectedEffectiveFrom = effectiveFrom || authoritativeDate || "";
  const dirty = savedDraft != null && (
    normalizeDraft(draft) !== normalizeDraft(savedDraft) ||
    (authoritativeDate != null && selectedEffectiveFrom !== (savedEffectiveFrom ?? authoritativeDate))
  );
  const writeOwnsAuthority = ["reconciling", "recovery", "committed"].includes(writePhase.kind);

  useEffect(() => {
    if (profileQuery.data === undefined) return;
    if (["reconciling", "recovery"].includes(writePhaseRef.current.kind)) return;
    if (profileQuery.data === null && hasSavedProfile) return;
    const nextDraft = profileQuery.data ? toDraft(profileQuery.data) : blankDraft();
    const responsePhaseOwnsAuthority = ["reconciling", "recovery", "committed"].includes(writePhaseRef.current.kind);
    const savedProfileBelongsToSubject = savedProfileSubjectRef.current === subjectId;
    if (dirty && savedProfileBelongsToSubject && !responsePhaseOwnsAuthority) {
      if (normalizeDraft(nextDraft) !== normalizeDraft(savedDraft ?? blankDraft())) {
        // Preserve an in-progress draft when a newer server response arrives.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setPendingServerProfile(profileQuery.data);
      }
      return;
    }
    setDraft(nextDraft);
    setSavedDraft(nextDraft);
    setHasSavedProfile((known) => known || profileQuery.data !== null);
    savedProfileSubjectRef.current = subjectId;
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
    enabled: !writeOwnsAuthority,
    discard: () => {
      setSavedDraft(draft);
      savedProfileSubjectRef.current = subjectId;
      setSavedEffectiveFrom(selectedEffectiveFrom || null);
      setPendingServerProfile(undefined);
    }
  });

  useLayoutEffect(() => {
    if (formSubjectRef.current === subjectId) return;
    formSubjectRef.current = subjectId;
    savedProfileSubjectRef.current = undefined;
    setHasSavedProfile(false);
    setDraft(blankDraft());
    setSavedDraft(null);
    setEffectiveFrom("");
    setSavedEffectiveFrom(null);
    setSavedTargets(null);
    setPendingServerProfile(undefined);
    setPreview(null);
    setPreviewDraftHash(null);
    setErrors({});
  }, [subjectId]);
  const validation = useMemo(
    () => validateDraft(draft, authoritativeDate, selectedEffectiveFrom),
    [draft, authoritativeDate, selectedEffectiveFrom]
  );
  const currentDraftHash = `${normalizeDraft(draft)}:${selectedEffectiveFrom}`;
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
    previewProfile(validation.payload, selectedEffectiveFrom, accessToken, sessionSignal)
      .then((result) => {
        if (sessionSignal.aborted || sequence !== previewSequence.current) return;
        setPreview(result);
        setPreviewDraftHash(requestedDraftHash);
        setPreviewFailed(false);
        setWriteSafetyOutcome(null);
        setSafetyAttemptSequence(0);
      })
      .catch((error) => {
        if (sessionSignal.aborted || sequence !== previewSequence.current) return;
        const mapped = mapProfileApiErrors(error);
        if (Object.keys(mapped).length > 0) {
          setErrors((current) => ({ ...current, ...mapped }));
          focusMappedProfileError(mapped);
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
  }, [dirty, normalizeDraft(draft), selectedEffectiveFrom, registryReady]);

  useEffect(() => {
    if (writeSafetyOutcome) return;
    // Reset the confirmation attempt when the authoritative preview changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSafetyAttemptSequence(0);
    if (writePhaseRef.current.kind === "confirming") {
      transitionWrite({ kind: "idle" });
    }
  }, [writeSafetyOutcome, currentDraftHash, currentPreview?.preview_hash]);

  useEffect(() => {
    if (safetyAttemptSequence === 0 || ["confirming", "submitting"].includes(writePhase.kind)) return;
    safetyRef.current?.focus();
  }, [writePhase.kind, writeSafetyOutcome, currentPreview?.safety_outcome, safetyAttemptSequence]);

  useEffect(() => {
    if (writePhase.kind !== "committed") return;
    const timer = window.setTimeout(() => transitionWrite({ kind: "idle" }), 2800);
    return () => window.clearTimeout(timer);
  }, [writePhase.kind]);

  async function reconcileAcceptedPlan(
    submission: TargetPlanSubmission,
    accepted: TargetPlanWriteResponse
  ) {
    transitionWrite({ kind: "reconciling", submission, accepted });
    try {
      const refreshed = await profileQuery.refetch();
      if (sessionSignal.aborted || !mountedRef.current) return;
      const profile = refreshed.data;
      if (!profile || !profileMatchesAcceptedPlan(profile, submission, accepted)) {
        transitionWrite({ kind: "recovery", submission, accepted });
        return;
      }
      const confirmed = toDraft(profile);
      queryClient.setQueryData(profileQueryKey, profile);
      setDraft(confirmed);
      setSavedDraft(confirmed);
      setHasSavedProfile(true);
      savedProfileSubjectRef.current = subjectId;
      setEffectiveFrom(submission.effectiveFrom);
      setSavedEffectiveFrom(submission.effectiveFrom);
      setSavedTargets(profile.targets);
      setPendingServerProfile(undefined);
      if (didConfirmedBirthDateChange(submission.previouslyConfirmedBirthDate, profile.birth_date) && subjectId) {
        void queryClient.invalidateQueries({ queryKey: labsQueryKeys.ownerRoot(subjectId) });
      }
      transitionWrite({ kind: "committed", accepted });
    } catch {
      if (!sessionSignal.aborted && mountedRef.current) {
        transitionWrite({ kind: "recovery", submission, accepted });
      }
    }
  }

  async function writeConfirmedPlan() {
    const current = writePhaseRef.current;
    if (current.kind !== "confirming") return;
    const { submission } = current;
    transitionWrite({ kind: "submitting", submission });
    try {
      const accepted = await writeTargetPlan(
        submission.payload,
        submission.effectiveFrom,
        submission.preview.preview_hash,
        submission.idempotencyKey,
        accessToken,
        sessionSignal
      );
      if (sessionSignal.aborted || !mountedRef.current) return;
      const labsDobChanged = didConfirmedBirthDateChange(
        submission.previouslyConfirmedBirthDate,
        submission.payload.birth_date
      );
      const committedDraft = toDraft(submission.payload);
      setDraft(committedDraft);
      setSavedDraft(committedDraft);
      setHasSavedProfile(true);
      savedProfileSubjectRef.current = subjectId;
      setEffectiveFrom(submission.effectiveFrom);
      setSavedEffectiveFrom(submission.effectiveFrom);
      setSavedTargets(accepted.plan.targets);
      setPendingServerProfile(undefined);
      setPreview(null);
      setPreviewDraftHash(null);
      setPreviewFailed(false);
      setErrors({});
      setWriteErrorCode(null);
      setWriteSafetyOutcome(null);
      setSafetyAttemptSequence(0);
      void queryClient.invalidateQueries({ queryKey: ["target-plan-history"] });
      if (labsDobChanged && subjectId) {
        void queryClient.invalidateQueries({ queryKey: labsQueryKeys.ownerRoot(subjectId) });
      }
      await reconcileAcceptedPlan(submission, accepted);
    } catch (error) {
      if (sessionSignal.aborted || !mountedRef.current) return;
      const mapped = mapProfileApiErrors(error);
      if (Object.keys(mapped).length > 0) {
        restoreWriteFocusRef.current = false;
        setErrors(mapped);
        focusMappedProfileError(mapped);
      }
      else if (error instanceof ApiError && ["SPECIALIST_REVIEW_REQUIRED", "VERY_LOW_ENERGY_TARGET_BLOCKED"].includes(error.code ?? "")) {
        restoreWriteFocusRef.current = false;
        setWriteSafetyOutcome(
          error.code === "SPECIALIST_REVIEW_REQUIRED"
            ? "specialist_review_required"
            : "very_low_energy_blocked"
        );
        setWriteErrorCode(error.code ?? null);
        setPreview(null);
        setPreviewDraftHash(null);
        setPreviewFailed(false);
        setSafetyAttemptSequence((sequence) => sequence + 1);
        transitionWrite({ kind: "idle" });
      }
      else if (error instanceof ApiError && ["PREVIEW_RESULT_CHANGED", "IDEMPOTENCY_KEY_REUSED", "TARGET_PLAN_EFFECTIVE_DATE_PAST", "TARGET_PLAN_DATE_BOUNDARY_CHANGED"].includes(error.code ?? "")) {
        setWriteErrorCode(error.code ?? null);
        if (["TARGET_PLAN_EFFECTIVE_DATE_PAST", "TARGET_PLAN_DATE_BOUNDARY_CHANGED"].includes(error.code ?? "")) {
          setErrors((currentErrors) => ({ ...currentErrors, effective_from: "اختر تاريخًا يبدأ من اليوم" }));
          void authorityQuery.refetch();
        }
        setPreview(null);
        setPreviewDraftHash(null);
        transitionWrite({ kind: "idle" });
        requestPreview();
      } else {
        transitionWrite({ kind: "failed", submission });
      }
    } finally {
      if (writePhaseRef.current.kind === "submitting") {
        writePhaseRef.current = { kind: "idle" };
        if (mountedRef.current) {
          setWritePhase({ kind: "idle" });
        }
      }
    }
  }

  function update<K extends keyof DraftProfile>(key: K, value: DraftProfile[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setErrors((current) => withoutProfileFieldError(current, key));
    transitionWrite({ kind: "idle" });
    setWriteErrorCode(null);
    setWriteSafetyOutcome(null);
    setSafetyAttemptSequence(0);
  }

  function updateSex(nextSex: Sex) {
    setDraft((current) => withUpdatedSex(current, nextSex));
    setErrors((current) => { const next = { ...current }; delete next.sex; delete next.fat_percent; return next; });
    transitionWrite({ kind: "idle" });
    setWriteErrorCode(null);
    setWriteSafetyOutcome(null);
    setSafetyAttemptSequence(0);
  }

  function submit(event?: FormEvent) {
    event?.preventDefault();
    const result = validateDraft(draft, authoritativeDate, selectedEffectiveFrom);
    setErrors(result.errors);
    if (!registryReady) return;
    if (!result.payload) {
      const order: Array<[ProfileField, RefObject<HTMLInputElement | null>]> = [
        ["birth_date", birthRef], ["height_cm", heightRef], ["weight_kg", weightRef],
        ["protein_per_kg", proteinRef], ["fat_percent", fatRef]
      ];
      const invalid = order.find(([field]) => result.errors[field]);
      if (result.errors.effective_from) effectiveFromRef.current?.focus();
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
      transitionWrite({ kind: "idle" });
      return;
    }
    restoreWriteFocusRef.current = true;
    const failedSubmission = writePhaseRef.current.kind === "failed"
      ? writePhaseRef.current.submission
      : null;
    const idempotencyKey = failedSubmission &&
      targetPlanSubmissionMatches(failedSubmission, result.payload, selectedEffectiveFrom, currentPreview.preview_hash)
      ? failedSubmission.idempotencyKey
      : crypto.randomUUID();
    transitionWrite({
      kind: "confirming",
      submission: {
        payload: result.payload,
        effectiveFrom: selectedEffectiveFrom,
        preview: currentPreview,
        idempotencyKey,
        previouslyConfirmedBirthDate: hasSavedProfile ? savedDraft?.birth_date ?? null : null
      }
    });
  }

  function acceptServerProfile() {
    const serverProfile = pendingServerProfile;
    if (serverProfile === undefined) return;
    requestDiscard(() => {
      if (serverProfile === null && hasSavedProfile) {
        setPendingServerProfile(undefined);
        return;
      }
      const nextDraft = serverProfile ? toDraft(serverProfile) : blankDraft();
      setDraft(nextDraft);
      setSavedDraft(nextDraft);
      setHasSavedProfile(serverProfile !== null);
      setSavedTargets(serverProfile?.targets ?? null);
      setPreview(null);
      setPreviewDraftHash(null);
      setErrors({});
      setPendingServerProfile(undefined);
    });
  }

  function changeEffectiveFrom(value: string) {
    setEffectiveFrom(value);
    setErrors((current) => withoutProfileFieldError(current, "effective_from"));
    transitionWrite({ kind: "idle" });
    setWriteErrorCode(null);
  }

  function requestRestoreDefaults() {
    const defaultsAlreadySet = normalizeNumber(draft.protein_per_kg) === PROTEIN_DEFAULT &&
      normalizeNumber(draft.fat_percent) === FAT_DEFAULTS[draft.sex] * 100;
    if (!defaultsAlreadySet) setRestoreOpen(true);
  }

  function confirmRestoreDefaults() {
    update("protein_per_kg", String(PROTEIN_DEFAULT));
    update("fat_percent", String(FAT_DEFAULTS[draft.sex] * 100));
    setRestoreOpen(false);
  }

  function retryReconciliation() {
    const current = writePhaseRef.current;
    if (current.kind === "recovery") void reconcileAcceptedPlan(current.submission, current.accepted);
  }

  function cancelWriteConfirmation() {
    if (writePhaseRef.current.kind === "confirming") transitionWrite({ kind: "idle" });
  }

  if (profileQuery.isPending || authorityQuery.isPending) return <ProfileSkeleton />;
  if ((profileQuery.isError && savedDraft === null) || authorityQuery.isError) return <ProfileLoadError onRetry={() => {
    profileQuery.refetch();
    authorityQuery.refetch();
  }} />;

  const displayBirthDate = draft.birth_date ? formatArabicGregorianDate(draft.birth_date) : "غير محدد";

  return (
    <ProfileView
      profile={{
        dirty,
        hasSavedProfile,
        hasPendingServerProfile: pendingServerProfile !== undefined,
        draft,
        errors,
        effectiveFrom: selectedEffectiveFrom,
        authoritativeDate,
        displayBirthDate,
        activeSheet,
        advancedOpen,
        restoreOpen,
        sexRef,
        effectiveFromRef,
        birthRef,
        heightRef,
        weightRef,
        proteinRef,
        fatRef,
      }}
      targets={{
        savedTargets,
        registry: { pending: registryQuery.isPending, failed: registryQuery.isError, data: registryQuery.data },
        history: {
          plans: planHistoryQuery.data?.pages.flatMap((page) => page.items) ?? [],
          pending: planHistoryQuery.isPending,
          failed: planHistoryQuery.isError,
          hasMore: planHistoryQuery.hasNextPage,
          loadingMore: planHistoryQuery.isFetchingNextPage,
        },
        preview: {
          visible: dirty && Boolean(validation.payload),
          current: currentPreview,
          pending: previewPending,
          failed: previewFailed,
          safetyOutcome: writeSafetyOutcome,
          safetyAttemptSequence,
          safetyRef,
        },
      }}
      write={{
        registryReady,
        validationHasPayload: Boolean(validation.payload),
        writeErrorCode,
        writePhase,
        restoreWriteFocusRef,
      }}
      intents={{
        keepLocalProfile: () => setPendingServerProfile(undefined),
        acceptServerProfile,
        updateField: update,
        changeEffectiveFrom,
        openSheet: (sheet) => { if (sheet !== "sex" || !hasSavedProfile) setActiveSheet(sheet); },
        closeSheet: () => setActiveSheet(null),
        selectSex: (sex: Sex) => { if (!hasSavedProfile) updateSex(sex); setActiveSheet(null); },
        selectActivity: (activity: ActivityLevel) => { update("activity_level", activity); setActiveSheet(null); },
        selectGoal: (goal: Goal) => { update("goal", goal); setActiveSheet(null); },
        toggleAdvanced: () => setAdvancedOpen((current) => !current),
        requestRestoreDefaults,
        cancelRestoreDefaults: () => setRestoreOpen(false),
        confirmRestoreDefaults,
        retryRegistry: () => void registryQuery.refetch(),
        retryHistory: () => void planHistoryQuery.refetch(),
        loadMoreHistory: () => void planHistoryQuery.fetchNextPage(),
        retryPreview: requestPreview,
        submit,
        retryReconciliation,
        cancelWriteConfirmation,
        confirmWrite: () => void writeConfirmedPlan(),
      }}
    />
  );
}
