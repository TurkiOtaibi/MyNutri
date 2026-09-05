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

import { ApiError, activateTargetPlan, getCalendarAuthority, getNutritionRegistry, getProfile, listTargetPlanHistory, previewProfile, replacePendingTargetPlan } from "@/lib/api";
import type { ProfileResponse, Sex, TargetPlanActivationResponse, TargetResponse } from "@/lib/types";
import { useAuth } from "./AuthProvider";
import { useSessionAbortSignal } from "./SessionQueryProvider";
import { useUnsavedChanges } from "./UnsavedChangesProvider";
import { ProfileLoadError, ProfileSkeleton } from "@/features/profile/profile-dialogs";
import { ProfileView } from "@/features/profile/profile-view";
import { FAT_DEFAULTS, blankDraft, formatArabicGregorianDate, isPreviewActivatable, mapProfileApiErrors, normalizeDraft, normalizeNumber, profileMatchesAcceptedActivation, toDraft, validateDraft, type ActivationPhase, type ActivationSubmission, type BlockingSafetyOutcome, type DraftProfile, type FieldErrors, type ProfileField, type SheetKind } from "@/features/profile/profile-model";

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
  const registryReady = registryQuery.data?.registry_schema_version === 3;
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
    <ProfileView
      dirty={dirty}
      pendingServerProfile={pendingServerProfile}
      setPendingServerProfile={setPendingServerProfile}
      requestDiscard={requestDiscard}
      setDraft={setDraft}
      setSavedDraft={setSavedDraft}
      setSavedTargets={setSavedTargets}
      setPreview={setPreview}
      setPreviewDraftHash={setPreviewDraftHash}
      setErrors={setErrors}
      draft={draft}
      activeSheet={activeSheet}
      updateSex={updateSex}
      setActiveSheet={setActiveSheet}
      errors={errors}
      birthRef={birthRef}
      authoritativeDate={authoritativeDate}
      displayBirthDate={displayBirthDate}
      heightRef={heightRef}
      weightRef={weightRef}
      update={update}
      advancedOpen={advancedOpen}
      setAdvancedOpen={setAdvancedOpen}
      proteinRef={proteinRef}
      fatRef={fatRef}
      savedTargets={savedTargets}
      profileQuery={profileQuery}
      registryQuery={registryQuery}
      registryReady={registryReady}
      planHistoryQuery={planHistoryQuery}
      currentPreview={currentPreview}
      previewPending={previewPending}
      previewFailed={previewFailed}
      activationSafetyOutcome={activationSafetyOutcome}
      safetyAttemptSequence={safetyAttemptSequence}
      safetyRef={safetyRef}
      requestPreview={requestPreview}
      validation={validation}
      activationErrorCode={activationErrorCode}
      activationPhase={activationPhase}
      submit={submit}
      reconcileAcceptedActivation={reconcileAcceptedActivation}
      restoreOpen={restoreOpen}
      setRestoreOpen={setRestoreOpen}
      transitionActivation={transitionActivation}
      activationPhaseRef={activationPhaseRef}
      restoreActivationFocusRef={restoreActivationFocusRef}
      activateConfirmedPlan={activateConfirmedPlan}
    />
  );
}
