import { LoaderCircle, RotateCcw, X } from "lucide-react";
import type { ReactNode, RefObject } from "react";
import { useEffect, useRef } from "react";

const PROFILE_READ_ERROR = "تعذر تحميل بياناتك";
const PROFILE_READ_HELP = "تحقق من الاتصال ثم أعد المحاولة";

export function ProfileSheet({ title, children, onClose, restoreFocusRef, dismissible = true, busy = false }: { title: string; children: ReactNode; onClose: () => void; restoreFocusRef?: RefObject<boolean>; dismissible?: boolean; busy?: boolean }) {
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
    const shouldRestoreFocus = restoreFocusRef;
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
      if (shouldRestoreFocus?.current !== false) triggerRef.current?.focus();
    };
  }, [restoreFocusRef]);
  useEffect(() => {
    if (busy) panelRef.current?.focus();
  }, [busy]);
  return <div className="profile-sheet-backdrop" role="presentation" onMouseDown={(event) => { if (dismissible && event.target === event.currentTarget) onClose(); }}><section ref={panelRef} className="profile-sheet" role="dialog" aria-modal="true" aria-labelledby="profile-sheet-title" aria-busy={busy || undefined} tabIndex={-1}><div className="profile-sheet-handle" /><header><h2 id="profile-sheet-title">{title}</h2><button ref={closeRef} type="button" onClick={onClose} aria-label={`إغلاق ${title}`} disabled={!dismissible}><X size={19} /></button></header><div className="profile-sheet-content">{children}</div></section></div>;
}

export function ProfileConfirm({ title, description, safeLabel, confirmLabel, destructive = false, pending = false, onClose, onConfirm, restoreFocusRef }: { title: string; description: string; safeLabel: string; confirmLabel: string; destructive?: boolean; pending?: boolean; onClose: () => void; onConfirm: () => void; restoreFocusRef?: RefObject<boolean> }) {
  return <ProfileSheet title={title} onClose={onClose} restoreFocusRef={restoreFocusRef} dismissible={!pending} busy={pending}><div className="profile-confirm"><p>{description}</p><button className="btn primary" type="button" onClick={onClose} disabled={pending}>{safeLabel}</button><button className={destructive ? "btn danger" : "btn"} type="button" onClick={onConfirm} disabled={pending}>{pending ? <><LoaderCircle className="spin" size={17} /> جارٍ التفعيل…</> : confirmLabel}</button></div></ProfileSheet>;
}

export function ProfileSkeleton() {
  return <main className="profile-page profile-loading" aria-label="جارٍ تحميل بياناتك"><header className="profile-page-head"><span /><span /></header><div className="profile-card-skeleton tall" /><div className="profile-card-skeleton" /><div className="profile-card-skeleton" /><div className="profile-card-skeleton targets" /></main>;
}

export function ProfileLoadError({ onRetry }: { onRetry: () => void }) {
  return <main className="profile-page"><header className="profile-page-head"><h1>بياناتك وأهدافك</h1><p>حدّث بياناتك لنحسب احتياجك اليومي.</p></header><section className="profile-load-error" role="alert"><strong>{PROFILE_READ_ERROR}</strong><span>{PROFILE_READ_HELP}</span><button className="btn" type="button" onClick={onRetry}><RotateCcw size={17} /> إعادة المحاولة</button></section></main>;
}
