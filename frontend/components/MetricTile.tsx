export function MetricTile({ label, value, unit }: { label: string; value: string | number; unit: string }) {
  return (
    <div className="metric-tile">
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
      <span className="metric-unit">{unit}</span>
    </div>
  );
}
