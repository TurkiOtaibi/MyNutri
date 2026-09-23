import { LabTestPage } from "@/components/LabTestPage";

export default async function LabTestRoute({ params }: { params: Promise<{ testKey: string }> }) {
  const { testKey } = await params;
  return <LabTestPage key={testKey} testKey={testKey} />;
}
