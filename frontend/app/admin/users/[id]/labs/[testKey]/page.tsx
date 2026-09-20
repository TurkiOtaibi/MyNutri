import { AdminUserLabTestPage } from "@/components/AdminUserLabTestPage";

export default async function AdminUserLabTestRoute({ params }: { params: Promise<{ id: string; testKey: string }> }) {
  const { id, testKey } = await params;
  return <AdminUserLabTestPage key={`${id}:${testKey}`} principalId={id} testKey={testKey} />;
}
