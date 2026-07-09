import { WifiOff } from "lucide-react";

export default function OfflinePage() {
  return (
    <section className="section-panel">
      <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <WifiOff size={26} />
        دون اتصال
      </h1>
      <p className="page-kicker">يمكنك الرجوع للبيانات المخزنة محليًا، وستتم مزامنة التغييرات عند عودة الاتصال.</p>
    </section>
  );
}
