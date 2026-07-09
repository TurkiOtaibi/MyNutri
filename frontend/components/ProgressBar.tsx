export function ProgressBar({ value, max }: { value: number; max: number }) {
  const percent = max > 0 ? Math.min((value / max) * 100, 140) : 0;
  const tone = percent > 110 ? "danger" : percent > 95 ? "warn" : "";

  return (
    <div className="progress-track" aria-label={`${Math.round(percent)}%`}>
      <div className={`progress-fill ${tone}`} style={{ width: `${Math.min(percent, 100)}%` }} />
    </div>
  );
}
