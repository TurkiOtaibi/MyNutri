import { AdminUserDetailsPage } from "@/components/AdminUserDetailsPage";

export const metadata = { title: "متابعة المستخدم | myNutri" };

export default async function AdminUserRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AdminUserDetailsPage principalId={id} />;
}
