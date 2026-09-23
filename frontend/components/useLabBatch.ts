"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { ApiError, createLabResults, getLabs, type LabsAuth } from "@/lib/api";
import type { LabCatalogResponse, LabFieldError } from "@/lib/types";
import { batchReducer, createBatchDraft, freezeBatch, populatedCount, type BatchAction, type BatchPhase, type PendingBatch } from "@/features/labs/lab-batch-model";
import { labsQueryKeys } from "@/features/labs/lab-query-keys";

function fieldErrors(error: ApiError): LabFieldError[] {
  if (Array.isArray(error.detail)) {
    const errors = error.detail.filter((item): item is LabFieldError => (
      typeof item === "object" && item !== null && Array.isArray(item.loc)
      && item.loc.every((part: unknown) => typeof part === "string" || typeof part === "number")
      && typeof item.msg === "string" && typeof item.type === "string"
      && (item.field == null || typeof item.field === "string")
      && (item.test_key == null || typeof item.test_key === "string")
      && (item.code == null || typeof item.code === "string")
    ));
    if (errors.length) return errors;
  }
  return [{ loc: ["body"], msg: error.message, type: "request_error" }];
}

export function useLabBatch(
  actorId: string | undefined,
  auth: LabsAuth,
  catalog: LabCatalogResponse | undefined,
  serverToday: string | undefined,
  onSaved?: () => void,
) {
  const queryClient = useQueryClient();
  const [phase, setPhase] = useState<BatchPhase | null>(null);
  const [opening, setOpening] = useState(false);
  const [openError, setOpenError] = useState<string | null>(null);
  const [refreshError, setRefreshError] = useState(false);
  const [sessionCatalog, setSessionCatalog] = useState(catalog);
  const [sessionToday, setSessionToday] = useState(serverToday);
  const phaseRef = useRef<BatchPhase | null>(null);
  const generation = useRef(0);
  const openingRef = useRef(false);
  const [owner, setOwner] = useState({ actorId, signal: auth.signal });

  // Adjust during render so the old actor's private state is never committed.
  if (owner.actorId !== actorId || owner.signal !== auth.signal) {
    setOwner({ actorId, signal: auth.signal });
    setPhase(null);
    setOpening(false);
    setOpenError(null);
    setRefreshError(false);
    setSessionCatalog(undefined);
    setSessionToday(undefined);
  }

  // Also protects consumers outside the keyed session subtree. Cleanup invalidates
  // callbacks even when a transport deliberately delivers an aborted response.
  useLayoutEffect(() => {
    generation.current += 1;
    phaseRef.current = null;
    openingRef.current = false;
    return () => { generation.current += 1; phaseRef.current = null; openingRef.current = false; };
  }, [actorId, auth.signal]);

  function dispatch(action: BatchAction) {
    if (auth.signal.aborted) return;
    const next = batchReducer(phaseRef.current, action);
    phaseRef.current = next;
    setPhase(next);
  }

  async function open(individualKeys: string[] = []) {
    if (!actorId || !catalog || auth.signal.aborted || openingRef.current
      || (phaseRef.current && phaseRef.current.kind !== "saved")) return;
    const operation = generation.current;
    openingRef.current = true;
    setOpening(true);
    setOpenError(null);
    try {
      // A direct read deliberately avoids initializing from a cached/pending older
      // overview. This is a new-session calendar read, not a timer or polling.
      const fresh = await getLabs(auth);
      if (auth.signal.aborted || generation.current !== operation) return;
      if (!fresh.eligibility.allowed || fresh.read_only) {
        setOpenError(fresh.read_only ? "التحاليل متاحة للمشرف للقراءة فقط." : fresh.eligibility.reason === "profile_required"
          ? "أكمل بيانات الملف الشخصي قبل إضافة نتائج التحاليل." : "يمكن إضافة نتائج أُجريت عند عمر 18 سنة فأكثر فقط.");
        return;
      }
      setSessionCatalog(catalog);
      setSessionToday(fresh.server_today);
      dispatch({ type: "OPEN", draft: createBatchDraft(actorId, fresh.server_today, catalog, individualKeys) });
    } catch {
      if (!auth.signal.aborted && generation.current === operation) setOpenError("تعذر تحميل التحاليل. حاول مرة أخرى.");
    } finally {
      if (!auth.signal.aborted && generation.current === operation) { openingRef.current = false; setOpening(false); }
    }
  }

  async function refresh() {
    if (!actorId || auth.signal.aborted) return;
    const operation = generation.current;
    setRefreshError(false);
    try {
      await queryClient.invalidateQueries({ queryKey: labsQueryKeys.ownerRoot(actorId) }, { throwOnError: true });
    } catch {
      if (!auth.signal.aborted && generation.current === operation) setRefreshError(true);
    }
  }

  async function send(pending: PendingBatch) {
    if (pending.actorId !== actorId || auth.signal.aborted) return;
    const operation = generation.current;
    try {
      const result = await createLabResults(pending.payload, pending.key, auth);
      if (auth.signal.aborted || generation.current !== operation) return;
      dispatch({ type: "SAVED", ...result });
      onSaved?.();
      if (auth.signal.aborted || generation.current !== operation) return;
      await refresh();
    } catch (error) {
      if (auth.signal.aborted || generation.current !== operation) return;
      if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
        dispatch({ type: "VALIDATION_ERROR", errors: fieldErrors(error) });
      } else {
        dispatch({ type: "NETWORK_AMBIGUOUS" });
      }
    }
  }

  function save() {
    const current = phaseRef.current;
    if (!current || (current.kind !== "editing" && current.kind !== "validation_error") || !populatedCount(current.draft) || auth.signal.aborted) return;
    const pending = freezeBatch(current.draft, crypto.randomUUID());
    dispatch({ type: "SUBMIT", pending });
    void send(pending);
  }

  function retry() {
    const current = phaseRef.current;
    if (!current || current.kind !== "ambiguous" || auth.signal.aborted) return;
    dispatch({ type: "RETRY" });
    void send(current.pending);
  }

  return { phase, opening, openError, refreshError, catalog: sessionCatalog, serverToday: sessionToday, open, refresh, save, retry, dispatch };
}
