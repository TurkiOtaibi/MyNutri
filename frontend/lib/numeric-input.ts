/** Normalize only explicit digits/decimal separators; grouping is never inferred. */
export function normalizeNumericInput(value: string): string {
  return value.trim().replace(/[٠-٩۰-۹]/g, (digit) =>
    String(digit.charCodeAt(0) - (digit >= "۰" ? 0x06f0 : 0x0660)),
  ).replaceAll("٫", ".");
}

/** Parse at validation/submission boundaries, leaving the editable draft untouched. */
export function parseNumericInput(value: string): number | null {
  const normalized = normalizeNumericInput(value);
  if (!/^(?:\d+\.?\d*|\.\d+)$/.test(normalized)) return null;
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : null;
}
