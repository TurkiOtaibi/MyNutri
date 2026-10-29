import { MoreVertical, Pencil, Trash2 } from "lucide-react";
import React, { useEffect, useRef, useState, type KeyboardEvent } from "react";
import styles from "./labs.module.css";

// «تعديل» and «حذف» for one history result, behind a «⋯» menu (Product Owner decision, 29 Oct 2026).
// The trigger is handed to the dialogs as their opener so focus returns to it.
export function LabResultMenu({ dateLabel, disabled, onEdit, onDelete }: {
  dateLabel: string; disabled: boolean; onEdit: (opener: HTMLElement) => void; onDelete: (opener: HTMLElement) => void;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    menuRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    const closeOutside = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, [open]);

  function handleMenuKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="menuitem"]'));
    const current = items.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
    } else if (event.key === "Tab") {
      setOpen(false);
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const next = (current + (event.key === "ArrowDown" ? 1 : items.length - 1)) % items.length;
      items[next]?.focus();
    }
  }

  const choose = (action: (opener: HTMLElement) => void) => {
    setOpen(false);
    if (triggerRef.current) action(triggerRef.current);
  };

  return <div className={styles.resultMenu} ref={rootRef}>
    <button ref={triggerRef} type="button" className="icon-button" disabled={disabled} aria-label={`خيارات نتيجة ${dateLabel}`}
      aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(current => !current)}>
      <MoreVertical size={19} aria-hidden="true" />
    </button>
    {open ? <div ref={menuRef} role="menu" className={styles.resultMenuList} onKeyDown={handleMenuKeyDown}>
      <button type="button" role="menuitem" aria-label={`تعديل نتيجة ${dateLabel}`} onClick={() => choose(onEdit)}><Pencil size={16} aria-hidden="true" /> تعديل</button>
      <button type="button" role="menuitem" className={styles.dangerItem} aria-label={`حذف نتيجة ${dateLabel}`} onClick={() => choose(onDelete)}><Trash2 size={16} aria-hidden="true" /> حذف</button>
    </div> : null}
  </div>;
}
