"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState
} from "react";

import { useAuth } from "./AuthProvider";

type GuardRegistration = {
  identity: string;
  dirty: boolean;
  enabled?: boolean;
  discard: () => void;
};

type PendingDecision = {
  continue: () => void;
  opener: HTMLElement | null;
  discardOnConfirm: boolean;
};

type UnsavedChangesContextValue = {
  register: (registration: GuardRegistration) => () => void;
  requestDiscard: (continueAction: () => void) => void;
  requestGuardedAction: (continueAction: () => void, options: { discardOnConfirm: boolean }) => void;
  navigate: (href: string, replace?: boolean) => void;
  completeAndNavigate: (href: string, replace?: boolean) => void;
};

const UnsavedChangesContext = createContext<UnsavedChangesContextValue | null>(null);
const HISTORY_POSITION = "__mynutriHistoryPosition";

export function UnsavedChangesProvider({ children }: { children: React.ReactNode }) {
  const { session } = useAuth();
  const router = useRouter();
  const registrationRef = useRef<GuardRegistration | null>(null);
  const registrationTokenRef = useRef<symbol | null>(null);
  const subjectRef = useRef<string | null>(session?.user.id ?? null);
  const [pending, setPending] = useState<PendingDecision | null>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const historyPositionRef = useRef(0);
  const suppressPopRef = useRef(false);
  const revertedTraversalRef = useRef<number | null>(null);

  const register = useCallback((registration: GuardRegistration) => {
    const token = Symbol(registration.identity);
    registrationTokenRef.current = token;
    registrationRef.current = registration;
    return () => {
      if (registrationTokenRef.current !== token) return;
      registrationTokenRef.current = null;
      registrationRef.current = null;
      setPending(null);
    };
  }, []);

  const requestGuardedAction = useCallback((continueAction: () => void, options: { discardOnConfirm: boolean }) => {
    const registration = registrationRef.current;
    if (!registration?.enabled || !registration.dirty) {
      continueAction();
      return;
    }
    setPending({
      continue: continueAction,
      opener: document.activeElement instanceof HTMLElement ? document.activeElement : null,
      discardOnConfirm: options.discardOnConfirm
    });
  }, []);
  const requestDiscard = useCallback((continueAction: () => void) => {
    requestGuardedAction(continueAction, { discardOnConfirm: true });
  }, [requestGuardedAction]);

  const navigate = useCallback((href: string, replace = false) => {
    requestDiscard(() => {
      registrationRef.current?.discard();
      registrationRef.current = null;
      if (replace) router.replace(href);
      else router.push(href);
    });
  }, [requestDiscard, router]);
  const completeAndNavigate = useCallback((href: string, replace = false) => {
    registrationRef.current?.discard();
    registrationRef.current = null;
    if (replace) router.replace(href);
    else router.push(href);
  }, [router]);

  useLayoutEffect(() => {
    const nextSubject = session?.user.id ?? null;
    if (subjectRef.current === nextSubject) return;
    subjectRef.current = nextSubject;
    registrationRef.current?.discard();
    registrationRef.current = null;
    registrationTokenRef.current = null;
    setPending(null);
  }, [session?.user.id]);

  useEffect(() => {
    const beforeUnload = (event: BeforeUnloadEvent) => {
      const registration = registrationRef.current;
      if (!registration?.enabled || !registration.dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", beforeUnload);
    return () => window.removeEventListener("beforeunload", beforeUnload);
  }, []);

  useEffect(() => {
    const interceptNavigation = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = (event.target as Element | null)?.closest("a[href]") as HTMLAnchorElement | null;
      if (!anchor || anchor.target || anchor.hasAttribute("download") || anchor.origin !== window.location.origin) return;
      const href = `${anchor.pathname}${anchor.search}${anchor.hash}`;
      const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      if (href === current) return;
      const registration = registrationRef.current;
      if (!registration?.enabled || !registration.dirty) return;
      event.preventDefault();
      event.stopPropagation();
      navigate(href);
    };
    document.addEventListener("click", interceptNavigation, true);
    return () => document.removeEventListener("click", interceptNavigation, true);
  }, [navigate]);

  useEffect(() => {
    const currentState = history.state && typeof history.state === "object" ? history.state : {};
    const existing = currentState[HISTORY_POSITION];
    if (typeof existing === "number") historyPositionRef.current = existing;
    else history.replaceState({ ...currentState, [HISTORY_POSITION]: 0 }, "");

    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;
    history.pushState = (data: unknown, unused: string, url?: string | URL | null) => {
      const nextPosition = historyPositionRef.current + 1;
      const nextData = data && typeof data === "object" ? data : {};
      originalPushState.call(history, { ...nextData, [HISTORY_POSITION]: nextPosition }, unused, url);
      historyPositionRef.current = nextPosition;
    };
    history.replaceState = (data: unknown, unused: string, url?: string | URL | null) => {
      const nextData = data && typeof data === "object" ? data : {};
      originalReplaceState.call(history, { ...nextData, [HISTORY_POSITION]: historyPositionRef.current }, unused, url);
    };

    const onPopState = (event: PopStateEvent) => {
      if (suppressPopRef.current) {
        suppressPopRef.current = false;
        const position = event.state?.[HISTORY_POSITION];
        if (typeof position === "number") historyPositionRef.current = position;
        const revertedDelta = revertedTraversalRef.current;
        revertedTraversalRef.current = null;
        if (revertedDelta != null) {
          requestDiscard(() => {
            registrationRef.current?.discard();
            registrationRef.current = null;
            suppressPopRef.current = true;
            history.go(revertedDelta);
          });
        }
        return;
      }
      const registration = registrationRef.current;
      if (!registration?.enabled || !registration.dirty) {
        const position = event.state?.[HISTORY_POSITION];
        if (typeof position === "number") historyPositionRef.current = position;
        return;
      }
      const destinationPosition = event.state?.[HISTORY_POSITION];
      const delta = typeof destinationPosition === "number"
        ? destinationPosition - historyPositionRef.current
        : -1;
      revertedTraversalRef.current = delta;
      suppressPopRef.current = true;
      history.go(-delta);
    };
    window.addEventListener("popstate", onPopState);
    return () => {
      window.removeEventListener("popstate", onPopState);
      history.pushState = originalPushState;
      history.replaceState = originalReplaceState;
    };
  }, [requestDiscard]);

  useEffect(() => {
    if (!pending) return;
    cancelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        const opener = pending.opener;
        setPending(null);
        window.requestAnimationFrame(() => opener?.focus());
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>("button:not(:disabled), [href], input, select, textarea, [tabindex]:not([tabindex='-1'])"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [pending]);

  const value = useMemo(
    () => ({ register, requestDiscard, requestGuardedAction, navigate, completeAndNavigate }),
    [completeAndNavigate, navigate, register, requestDiscard, requestGuardedAction]
  );
  const cancel = () => {
    const opener = pending?.opener;
    setPending(null);
    window.requestAnimationFrame(() => opener?.focus());
  };
  const confirm = () => {
    if (!pending) return;
    const continueAction = pending.continue;
    setPending(null);
    if (pending.discardOnConfirm) {
      registrationRef.current?.discard();
      registrationRef.current = null;
    }
    continueAction();
  };

  return (
    <UnsavedChangesContext.Provider value={value}>
      {children}
      {pending ? (
        <div className="unsaved-dialog-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) cancel();
        }}>
          <div
            ref={dialogRef}
            className="unsaved-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="unsaved-dialog-title"
            aria-describedby="unsaved-dialog-description"
          >
            <h2 id="unsaved-dialog-title">تغييرات غير محفوظة</h2>
            <p id="unsaved-dialog-description">ستفقد التغييرات التي لم تحفظها إذا غادرت هذه الصفحة.</p>
            <div className="actions">
              <button ref={cancelRef} className="btn" type="button" onClick={cancel}>متابعة التعديل</button>
              <button className="btn danger" type="button" onClick={confirm}>تجاهل التغييرات والمغادرة</button>
            </div>
          </div>
        </div>
      ) : null}
    </UnsavedChangesContext.Provider>
  );
}

export function useUnsavedChanges(registration?: GuardRegistration) {
  const context = useContext(UnsavedChangesContext);
  if (!context) throw new Error("useUnsavedChanges must be used within UnsavedChangesProvider.");
  const registrationRef = useRef(registration);
  registrationRef.current = registration;

  useEffect(() => {
    if (!registration) return;
    return context.register({
      ...registration,
      discard: () => registrationRef.current?.discard()
    });
  }, [context, registration?.dirty, registration?.enabled, registration?.identity]);

  return context;
}
