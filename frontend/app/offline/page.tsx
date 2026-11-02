import { WifiOff } from "lucide-react";

export default function OfflinePage() {
  return (
    <section className="section-panel offline-panel" aria-labelledby="offline-title">
      <h1 id="offline-title" className="page-title"><WifiOff size={26} aria-hidden="true" />الاتصال غير متاح</h1>
      <p>النظام يحتاج اتصالًا بالإنترنت لتحميل بيانات التغذية وحفظ التغييرات.</p>
      <p className="offline-save-note">لا يتم حفظ التغييرات محليًا ولا توجد مزامنة لاحقة.</p>
      <form action="/diary" method="get">
        <p id="offline-retry-note">تحقق من الاتصال ثم أعد المحاولة لفتح اليوميات.</p>
        <button aria-describedby="offline-retry-note" className="btn primary" type="submit">إعادة المحاولة</button>
      </form>
    </section>
  );
}
