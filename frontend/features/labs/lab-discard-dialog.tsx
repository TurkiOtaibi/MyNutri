import { AlertDialog } from "@base-ui-components/react/alert-dialog";
import styles from "./labs.module.css";

export function LabDiscardDialog({ open, onContinue, onDiscard }: { open: boolean; onContinue: () => void; onDiscard: () => void }) {
  return <AlertDialog.Root open={open} onOpenChange={value => { if (!value) onContinue(); }}>
    <AlertDialog.Portal><AlertDialog.Backdrop className={`${styles.batchBackdrop} ${styles.discardBackdrop}`} />
      <AlertDialog.Popup className={`${styles.batchDialog} ${styles.discardDialog}`} dir="rtl">
        <AlertDialog.Title>تجاهل التغييرات؟</AlertDialog.Title>
        <AlertDialog.Description>لديك تغييرات غير محفوظة. سيؤدي الإغلاق إلى فقدانها.</AlertDialog.Description>
        <footer className={styles.batchActions}>
          <button type="button" className="btn" onClick={onContinue}>متابعة التعديل</button>
          <button type="button" className="btn danger" onClick={onDiscard}>تجاهل التغييرات</button>
        </footer>
      </AlertDialog.Popup>
    </AlertDialog.Portal>
  </AlertDialog.Root>;
}
