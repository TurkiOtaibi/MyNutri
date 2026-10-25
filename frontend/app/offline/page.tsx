import { WifiOff } from "lucide-react";

export default function OfflinePage() {
  return (
    <section className="section-panel">
      <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <WifiOff size={26} />
        الاتصال غير متاح
      </h1>
      <p className="page-kicker">
        النظام يحتاج اتصالًا بالإنترنت لتحميل بيانات التغذية وحفظ التغييرات. لا يتم حفظ التغييرات محليًا ولا توجد
        مزامنة لاحقة. تحقق من الاتصال ثم أعد المحاولة.
      </p>
      <form action="/diary" method="get">
        <button className="btn primary" type="submit">إعادة المحاولة</button>
      </form>
    </section>
  );
}
