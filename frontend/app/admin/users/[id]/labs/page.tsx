import { AdminUserLabsPage } from "@/components/AdminUserLabsPage";

export const metadata = { title: "تحاليل المستخدم | myNutri" };

export default async function AdminUserLabsRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AdminUserLabsPage principalId={id} />;
}
