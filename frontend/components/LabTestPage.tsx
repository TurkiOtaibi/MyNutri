"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/AuthProvider";
import { useSessionAbortSignal } from "@/components/SessionQueryProvider";
import { useLabBatch } from "@/components/useLabBatch";
import { LabBatchDialog } from "@/features/labs/lab-batch-dialog";
import { LabTestView } from "@/features/labs/lab-test-view";
import { LabDeleteDialog, LabEditDialog } from "@/features/labs/lab-result-dialogs";
import { freezeResultPatch, readbackResult, resultFieldErrors, type ResultReadback } from "@/features/labs/lab-result-model";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";
import styles from "@/features/labs/labs.module.css";
import { ApiError, deleteLabResult, getLabCatalog, getLabTest, updateLabResult } from "@/lib/api";
import type { LabCatalogTest, LabFieldError, LabResultPatch, LabResultResponse } from "@/lib/types";

type ResultDialog = {
  kind: "edit" | "delete"; actorId: string; generation: number;
  result: LabResultResponse; test: LabCatalogTest; serverToday: string; opener: HTMLElement | null;
  submitted?: LabResultPatch; blocked?: boolean; errors: LabFieldError[];
  recovery?: ResultReadback | { kind: "reading" | "failed" }; deleteError?: string;
};

export function LabTestPage({ testKey }: { testKey: string }) {
  const { session } = useAuth();
  const sessionSignal = useSessionAbortSignal();
  const actorId = session?.user.id, accessToken = session?.access_token;
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const batchOpener = useRef<HTMLElement | null>(null);
  const queryClient = useQueryClient();
  const [resultDialog, setResultDialog] = useState<ResultDialog | null>(null);
  const [resultPending, setResultPending] = useState(false);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [resultOpenError, setResultOpenError] = useState<string | null>(null);
  const [resultRefreshError, setResultRefreshError] = useState(false);
  const dialogRef = useRef<ResultDialog | null>(null);
  const busy = useRef(false);
  const generation = useRef(0);
  const [owner, setOwner] = useState({ actorId, signal: sessionSignal, testKey });
  if (owner.actorId !== actorId || owner.signal !== sessionSignal || owner.testKey !== testKey) {
    setOwner({ actorId, signal: sessionSignal, testKey });
    setResultDialog(null); setResultPending(false); setResultMessage(null);
    setResultOpenError(null); setResultRefreshError(false); setSelectedResultId(null);
  }
  useLayoutEffect(() => {
    generation.current += 1; dialogRef.current = null; busy.current = false;
    return () => { generation.current += 1; dialogRef.current = null; busy.current = false; };
  }, [actorId, sessionSignal, testKey]);
  const queryPolicy = { staleTime: 0, refetchOnMount: "always" as const, refetchOnWindowFocus: "always" as const, retry: false };
  const catalog = useQuery({
    queryKey: labsQueryKeys.catalog(actorId ?? "anonymous"),
    queryFn: ({ signal }) => getLabCatalog({ accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken), ...queryPolicy,
  });
  const detail = useQuery({
    queryKey: labsQueryKeys.ownerTest(actorId ?? "anonymous", testKey),
    queryFn: ({ signal }) => getLabTest(testKey, { accessToken: accessToken!, signal: AbortSignal.any([signal, sessionSignal]) }),
    enabled: Boolean(actorId && accessToken), ...queryPolicy,
  });
  const batch = useLabBatch(actorId, { accessToken: accessToken ?? "", signal: sessionSignal }, catalog.data, detail.data?.server_today);
  const batchActive = batch.opening || Boolean(batch.phase && batch.phase.kind !== "saved");
  const auth = { accessToken: accessToken ?? "", signal: sessionSignal };
  const isCurrent = (operation: number) => !sessionSignal.aborted && generation.current === operation;
  function showDialog(next: ResultDialog | null) { dialogRef.current = next; setResultDialog(next); }

  async function refreshResults(operation = generation.current) {
    if (!actorId || !isCurrent(operation)) return;
    setResultRefreshError(false);
    try {
      await queryClient.invalidateQueries({ queryKey: labsQueryKeys.ownerRoot(actorId) }, { throwOnError: true });
    } catch { if (isCurrent(operation)) setResultRefreshError(true); }
  }
  async function openResult(kind: ResultDialog["kind"], result: LabResultResponse, opener: HTMLElement) {
    if (!actorId || !accessToken || busy.current || dialogRef.current || batchActive || detail.data?.read_only || sessionSignal.aborted) return;
    const operation = generation.current;
    busy.current = true; setResultPending(true); setResultMessage(null); setResultOpenError(null);
    try {
      // Every new edit starts with the current same-id facts, including after an
      // explicitly closed ambiguous edit. Never seed from a stale cached row.
      const fresh = await getLabTest(testKey, auth);
      if (!isCurrent(operation)) return;
      const current = fresh.results.find(item => item.id === result.id);
      if (fresh.read_only || !current) {
        setResultOpenError(fresh.read_only ? "التحاليل متاحة للمشرف للقراءة فقط." : "هذه النتيجة لم تعد موجودة. أعد تحميل التحاليل الحالية.");
        await refreshResults(operation); return;
      }
      showDialog({ kind, actorId, generation: operation, result: current, test: fresh.test, serverToday: fresh.server_today, opener, errors: [] });
    } catch { if (isCurrent(operation)) setResultOpenError("تعذر تحميل النتيجة الحالية. حاول مرة أخرى."); }
    finally { if (isCurrent(operation)) { busy.current = false; setResultPending(false); } }
  }
  function closeResult() {
    if (busy.current || sessionSignal.aborted) return;
    showDialog(null);
  }
  async function confirmResult(target: ResultDialog) {
    if (!isCurrent(target.generation) || target.actorId !== actorId) return;
    // Start owner-root invalidation before closing. A failing fresh GET must not
    // reclassify an already confirmed write as a retryable mutation failure.
    const refresh = refreshResults(target.generation);
    showDialog(null);
    setResultMessage(target.kind === "edit" ? "تم حفظ التعديل." : "تم حذف النتيجة.");
    await refresh;
  }
  async function reconcileResult(target: ResultDialog) {
    if (!isCurrent(target.generation) || target.actorId !== actorId) return;
    const reading = { ...target, blocked: true, recovery: { kind: "reading" as const } };
    showDialog(reading);
    try {
      const fresh = await getLabTest(target.test.test_key, auth);
      if (!isCurrent(target.generation)) return;
      const recovery = readbackResult(fresh.results, target.result.id, target.submitted);
      if (target.kind === "delete" && recovery.kind === "absent") { await confirmResult(target); return; }
      showDialog({ ...target, recovery, blocked: true, deleteError: target.kind === "delete" ? "النتيجة ما زالت موجودة. يمكنك إعادة محاولة حذف النتيجة نفسها." : undefined });
      // Make the observed server version available to a subsequent fresh edit.
      // A matching GET never confirms PATCH provenance or clears its draft.
      await refreshResults(target.generation);
    } catch {
      if (isCurrent(target.generation)) showDialog({ ...target, blocked: true, recovery: { kind: "failed" }, deleteError: "تعذر تأكيد الحذف. أعد قراءة النتيجة للتحقق." });
    }
  }
  async function rereadResult() {
    const target = dialogRef.current;
    if (!target || busy.current || target.actorId !== actorId || !isCurrent(target.generation)) return;
    busy.current = true; setResultPending(true);
    try { await reconcileResult(target); }
    finally { if (isCurrent(target.generation)) { busy.current = false; setResultPending(false); } }
  }
  async function mutateResult(payload?: LabResultPatch) {
    const target = dialogRef.current;
    if (!target || busy.current || target.actorId !== actorId || !isCurrent(target.generation)) return;
    if (target.kind === "edit" && (target.blocked || !payload)) return;
    if (target.kind === "delete" && target.blocked && target.recovery?.kind !== "different") return;
    const submitted = target.kind === "edit" ? freezeResultPatch(payload!) : undefined;
    const pending = { ...target, submitted, errors: [], deleteError: undefined };
    busy.current = true; setResultPending(true); showDialog(pending);
    try {
      if (target.kind === "edit") await updateLabResult(target.result.id, submitted!, auth);
      else await deleteLabResult(target.result.id, auth);
      if (!isCurrent(target.generation)) return;
      await confirmResult(pending);
    } catch (error) {
      if (!isCurrent(target.generation)) return;
      if (!(error instanceof ApiError) || error.status >= 500 || (target.kind === "delete" && error.status === 404)) {
        await reconcileResult(pending);
      } else if (target.kind === "edit" && error.status === 404) {
        showDialog({ ...pending, blocked: true, recovery: { kind: "absent" } });
        await refreshResults(target.generation);
      } else {
        // 401/403 are request errors even if a server sends field-like detail.
        const errors = resultFieldErrors(error.status === 409 || error.status === 422 ? error.detail : undefined, error.message);
        showDialog({ ...pending, errors, deleteError: errors[0]?.msg });
      }
    } finally { if (isCurrent(target.generation)) { busy.current = false; setResultPending(false); } }
  }
  const recovery = resultDialog?.recovery;
  const recoveryView = recovery ? <div role="alert" className={styles.batchError}>
    {recovery.kind === "reading" ? <p>لم يتم تأكيد الحفظ. جارٍ قراءة النتيجة الحالية...</p>
      : recovery.kind === "matches" ? <p>القيم الحالية على الخادم تطابق القيم المرسلة، لكن لم يتم تأكيد استجابة الحفظ. أغلق النافذة لبدء تعديل جديد.</p>
      : recovery.kind === "different" ? <><p>تختلف النتيجة الحالية على الخادم عن القيم المرسلة. أغلق النافذة لبدء تعديل جديد.</p><p data-testid="lab-current-facts">القيم الحالية: <bdi dir="ltr">{recovery.current.entered_value} {recovery.current.entered_unit} — {recovery.current.test_date}</bdi></p></>
      : recovery.kind === "absent" ? <p>هذه النتيجة لم تعد موجودة. لم يتم تأكيد الحفظ.</p>
      : <p>تعذر تأكيد الحفظ أو قراءة النتيجة الحالية. أعد قراءة النتيجة للتحقق.</p>}
  </div> : null;
  const dialogActor = resultDialog?.actorId, dialogGeneration = resultDialog?.generation;
  const dialogCurrent = useCallback(() => Boolean(dialogActor && dialogActor === actorId
    && !sessionSignal.aborted && generation.current === dialogGeneration), [actorId, dialogActor, dialogGeneration, sessionSignal]);
  const returnResultFocus = () => {
    if (!dialogCurrent()) return false;
    if (resultDialog?.opener?.isConnected) return resultDialog.opener;
    return document.getElementById("lab-detail-add");
  };
  return <div className={styles.labsPage}>
    <Link href="/labs">رجوع إلى التحاليل</Link>
    {detail.isPending ? <p role="status">جارٍ تحميل التحاليل...</p> : null}
    {batch.opening ? <p role="status">جارٍ تحميل تاريخ التحاليل...</p> : null}
    {batch.openError ? <p role="alert">{batch.openError}</p> : null}
    {resultPending && !resultDialog ? <p role="status">جارٍ تحميل النتيجة الحالية...</p> : null}
    {resultOpenError ? <p role="alert">{resultOpenError}</p> : null}
    {resultMessage ? <p role="status">{resultMessage}</p> : null}
    {batch.phase?.kind === "saved" ? <p role="status">{batch.phase.replayed ? "تم تأكيد نجاح عملية الحفظ السابقة." : "تم حفظ النتائج."}</p> : null}
    {batch.refreshError || resultRefreshError || detail.isError || catalog.isError ? <div role="alert">تعذر تحميل التحاليل الحالية. حاول مرة أخرى.
      <button type="button" className="btn" onClick={() => {
        if (sessionSignal.aborted) return;
        if (catalog.isError) void catalog.refetch();
        setResultRefreshError(false);
        if (batch.refreshError) void batch.refresh(); else void refreshResults();
      }}>إعادة تحميل التحاليل</button>
    </div> : null}
    {detail.data ? <LabTestView detail={detail.data} selectedResultId={selectedResultId} onSelectResult={setSelectedResultId}
      ownerResultActions={result => <div className={styles.batchActions}>
        <button type="button" className="btn" disabled={resultPending || batchActive} aria-label={`تعديل نتيجة ${result.test_date}`} onClick={event => { void openResult("edit", result, event.currentTarget); }}>تعديل</button>
        <button type="button" className="btn" disabled={resultPending || batchActive} aria-label={`حذف نتيجة ${result.test_date}`} onClick={event => { void openResult("delete", result, event.currentTarget); }}>حذف</button>
      </div>}
      ownerActions={<button id="lab-detail-add" className="btn primary" type="button" disabled={batch.opening || !catalog.data || resultPending} onClick={() => {
        if (busy.current || dialogRef.current || sessionSignal.aborted) return;
        batchOpener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        void batch.open([testKey]);
      }}>إضافة نتيجة</button>} /> : null}
    <LabBatchDialog phase={batch.phase} catalog={batch.catalog} returnFocusRef={batchOpener}
      onDate={(date) => batch.dispatch({ type: "EDIT_DATE", date })}
      onPanel={(key, selected) => { if (batch.catalog) batch.dispatch({ type: "PANEL", key, selected, catalog: batch.catalog }); }}
      onIndividual={(key, selected) => { if (batch.catalog) batch.dispatch({ type: "INDIVIDUAL", key, selected, catalog: batch.catalog }); }}
      onValue={(testKey, value) => batch.dispatch({ type: "EDIT_VALUE", testKey, value })}
      onUnit={(testKey, unit) => batch.dispatch({ type: "EDIT_UNIT", testKey, unit })}
      onNext={() => batch.dispatch({ type: "NEXT" })} onBack={() => batch.dispatch({ type: "BACK" })}
      onSave={batch.save} onRetry={batch.retry} onCancel={() => batch.dispatch({ type: "CANCEL" })} />
    {resultDialog?.kind === "edit" ? <LabEditDialog key={`${resultDialog.generation}:${resultDialog.result.id}`} result={resultDialog.result} test={resultDialog.test} serverToday={resultDialog.serverToday}
      pending={resultPending} errors={resultDialog.errors} writeBlocked={resultDialog.blocked} recovery={recoveryView}
      onSubmit={mutateResult} onCancel={closeResult} onReread={resultDialog.blocked ? () => { void rereadResult(); } : undefined} isCurrent={dialogCurrent} returnFocus={returnResultFocus} /> : null}
    {resultDialog?.kind === "delete" ? <LabDeleteDialog key={`${resultDialog.generation}:${resultDialog.result.id}`} result={resultDialog.result} test={resultDialog.test}
      pending={resultPending} error={resultDialog.deleteError} retryAllowed={!resultDialog.blocked || resultDialog.recovery?.kind === "different"}
      onConfirm={() => mutateResult()} onCancel={closeResult} onReread={resultDialog.blocked ? () => { void rereadResult(); } : undefined} isCurrent={dialogCurrent} returnFocus={returnResultFocus} /> : null}
  </div>;
}
