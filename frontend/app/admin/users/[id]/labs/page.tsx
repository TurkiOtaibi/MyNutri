import { AdminUserLabsPage } from "@/components/AdminUserLabsPage";

export default async function AdminUserLabsRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AdminUserLabsPage principalId={id} />;
}
