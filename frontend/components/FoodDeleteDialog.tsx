"use client";

import { AlertTriangle, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { FoodResponse } from "@/lib/types";

export function FoodDeleteDialog({
  food,
  pending,
  onCancel,
  onConfirm
}: {
  food: FoodResponse | null;
  pending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const panelRef = useRef<HTMLElement | null>(null);
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const confirmRef = useRef<HTMLButtonElement | null>(null);
  const onCancelRef = useRef(onCancel);
  const deletingRef = useRef(false);
  const submittedRef = useRef(false);
  const sawPendingRef = useRef(false);
  const [submitted, setSubmitted] = useState(false);
  const deleting = pending || submitted;
  onCancelRef.current = onCancel;
  deletingRef.current = deleting;

  useEffect(() => {
    if (!food) {
      submittedRef.current = false;
      sawPendingRef.current = false;
      setSubmitted(false);
      return;
    }
    if (pending) {
      sawPendingRef.current = true;
    } else if (sawPendingRef.current) {
      submittedRef.current = false;
      sawPendingRef.current = false;
      setSubmitted(false);
    }
  }, [food, pending]);

  useEffect(() => {
    if (!food) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    cancelRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape" && !deletingRef.current) {
        onCancelRef.current();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = [...panelRef.current.querySelectorAll<HTMLElement>("button:not(:disabled), a[href], [tabindex]:not([tabindex='-1'])")];
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previous?.focus();
    };
  }, [food]);

  function confirmOnce() {
    if (submittedRef.current || pending) return;
    submittedRef.current = true;
    setSubmitted(true);
    onConfirm();
  }

  if (!food) return null;

  return (
    <div className="dialog-backdrop" role="presentation">
      <section
        ref={panelRef}
        className="dialog-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-food-title"
        aria-describedby="delete-food-description"
      >
        <div className="dialog-title-row">
          <AlertTriangle size={22} aria-hidden="true" />
          <h2 id="delete-food-title">حذف الطعام نهائيًا</h2>
        </div>
        <p id="delete-food-description" className="page-kicker">
          سيتم حذف {food.name} نهائيًا من كتالوج الأطعمة. ستبقى اليوميات السابقة كما هي لأنها تستخدم نسخة غذائية محفوظة.
        </p>
        <div className="actions">
          <button ref={cancelRef} className="btn" type="button" onClick={onCancel} disabled={deleting}>
            <X size={18} />
            إلغاء
          </button>
          <button ref={confirmRef} className="btn danger" type="button" onClick={confirmOnce} disabled={deleting}>
            <Trash2 size={18} />
            {deleting ? "جاري الحذف..." : "حذف نهائي"}
          </button>
        </div>
      </section>
    </div>
  );
}
