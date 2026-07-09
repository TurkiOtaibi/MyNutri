import type { TargetResponse } from "@/lib/types";

import { MetricTile } from "./MetricTile";

export function TargetStrip({ targets }: { targets: TargetResponse | null | undefined }) {
  if (!targets) {
    return <div className="state-note">أدخل بيانات الملف لحساب السعرات والماكروز.</div>;
  }

  return (
    <div className="target-strip">
      <MetricTile label="السعرات" value={targets.target_calories} unit="كيلو كالوري" />
      <MetricTile label="البروتين" value={targets.protein_g} unit="غرام" />
      <MetricTile label="الكارب" value={targets.carb_g} unit="غرام" />
      <MetricTile label="الدهون" value={targets.fat_g} unit="غرام" />
    </div>
  );
}
