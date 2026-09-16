import Link from "next/link";
import { Users } from "lucide-react";

export default function AdminPage() {
  return <>
    <div className="page-head"><div><h1 className="page-title">الإدارة</h1><p className="page-kicker">إدارة الحسابات ومتابعة بيانات التغذية.</p></div></div>
    <div className="admin-home-grid">
      <Link className="section-panel admin-home-link" href="/admin/users"><Users /><strong>المستخدمون</strong><span>عرض الحسابات وبيانات التغذية للمتابعة فقط.</span></Link>
    </div>
  </>;
}
