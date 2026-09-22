import type { ReactNode } from "react";
import { useEffect, useLayoutEffect, useRef } from "react";
import { createPortal } from "react-dom";

type ModalFocusScope = {
  panel: HTMLDivElement;
  opener: HTMLElement | null;
  fallbackOpener: HTMLElement | null;
  onCloseRef: { current: () => void };
  pendingRef: { current: boolean };
};

const modalFocusScopes: ModalFocusScope[] = [];

function focusableElements(panel: HTMLElement): HTMLElement[] {
  return Array.from(panel.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )).filter((element) => element.getClientRects().length > 0 && !element.closest("[inert]"));
}

function topModalScope(): ModalFocusScope | undefined {
  return modalFocusScopes[modalFocusScopes.length - 1];
}

function syncModalFocusOwnership() {
  const top = topModalScope();
  for (const scope of modalFocusScopes) {
    if (scope === top) {
      scope.panel.removeAttribute("inert");
      scope.panel.removeAttribute("aria-hidden");
    } else {
      scope.panel.setAttribute("inert", "");
      scope.panel.setAttribute("aria-hidden", "true");
    }
  }
}

function handleModalKeyDown(event: KeyboardEvent) {
  const scope = topModalScope();
  if (!scope) return;
  if (event.key === "Escape") {
    if (!scope.pendingRef.current) {
      event.preventDefault();
      scope.onCloseRef.current();
    }
    return;
  }
  if (event.key !== "Tab") return;
  const items = focusableElements(scope.panel);
  if (!items.length) {
    event.preventDefault();
    scope.panel.focus();
    return;
  }
  const first = items[0];
  const last = items[items.length - 1];
  const active = document.activeElement;
  if (!scope.panel.contains(active)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
  } else if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

function registerModalFocusScope(scope: ModalFocusScope) {
  if (modalFocusScopes.length === 0) {
    document.addEventListener("keydown", handleModalKeyDown);
    document.body.classList.add("modal-open");
  }
  modalFocusScopes.push(scope);
  syncModalFocusOwnership();
  (scope.panel.querySelector<HTMLElement>("[data-initial-focus]") ?? focusableElements(scope.panel)[0] ?? scope.panel).focus();
}

function unregisterModalFocusScope(scope: ModalFocusScope) {
  const wasTop = topModalScope() === scope;
  const index = modalFocusScopes.indexOf(scope);
  if (index >= 0) modalFocusScopes.splice(index, 1);
  syncModalFocusOwnership();
  if (modalFocusScopes.length === 0) {
    document.removeEventListener("keydown", handleModalKeyDown);
    document.body.classList.remove("modal-open");
  }
  if (!wasTop) return;
  const restoreTarget = scope.opener?.isConnected && !scope.opener.closest("[inert]") ? scope.opener : scope.fallbackOpener;
  if (restoreTarget?.isConnected && !restoreTarget.closest("[inert]")) restoreTarget.focus();
}

export function ModalFrame({
  children,
  labelledBy,
  describedBy,
  onClose,
  pending,
  className = "",
  panelClassName = "",
  role = "dialog",
}: {
  children: ReactNode;
  labelledBy: string;
  describedBy?: string;
  onClose: () => void;
  pending: boolean;
  className?: string;
  panelClassName?: string;
  role?: "dialog" | "alertdialog";
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  const pendingRef = useRef(pending);

  useEffect(() => {
    onCloseRef.current = onClose;
    pendingRef.current = pending;
  }, [onClose, pending]);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    const parentScope = topModalScope();
    const opener = document.activeElement as HTMLElement | null;
    const scope: ModalFocusScope = {
      panel,
      opener,
      fallbackOpener: parentScope?.fallbackOpener ?? parentScope?.opener ?? opener,
      onCloseRef,
      pendingRef,
    };
    registerModalFocusScope(scope);
    return () => unregisterModalFocusScope(scope);
  }, []);

  useLayoutEffect(() => {
    const panel = panelRef.current;
    if (!pending || !panel || topModalScope()?.panel !== panel) return;
    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const activeRemainsUsable = Boolean(
      active
      && active.isConnected
      && panel.contains(active)
      && active.getClientRects().length > 0
      && !active.matches(":disabled")
      && active.getAttribute("aria-disabled") !== "true"
      && !active.closest("[inert]")
      && !active.closest('[aria-hidden="true"]'),
    );
    if (!activeRemainsUsable) panel.focus();
  }, [pending]);

  return createPortal(
    <div className={`diary-modal-backdrop ${className}`} role="presentation" onMouseDown={(event) => {
      if (event.target !== event.currentTarget) return;
      if (pendingRef.current) {
        event.preventDefault();
        return;
      }
      onCloseRef.current();
    }}>
      <div
        ref={panelRef}
        className={`diary-modal-panel ${panelClassName}`}
        role={role}
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
