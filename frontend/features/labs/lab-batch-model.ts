import type { LabCatalogResponse, LabCreateRequest, LabFieldError } from "@/lib/types";

export type LabDraftRow = { testKey: string; value: string; unit: string };
export type BatchDraft = { actorId: string; testDate: string; rows: LabDraftRow[] };
export type LabRowErrors = { entered_value?: string; entered_unit?: string; form?: string };
export type LabMappedErrors = {
  test_date?: string;
  rows: Record<string, LabRowErrors>;
  form?: string;
};

const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
const persianDigits = "۰۱۲۳۴۵۶۷۸۹";

export function normalizeLabNumber(raw: string): string {
  return raw
    .trim()
    .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)))
    .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
    .replace(/٬/g, "")
    .replace(/٫/g, ".");
}

export function selectedTestKeys(
  panelKeys: string[],
  individualKeys: string[],
  catalog: LabCatalogResponse,
): string[] {
  const selectedPanels = new Set(panelKeys);
  const selected = new Set(individualKeys);
  for (const panel of catalog.panels) {
    if (!selectedPanels.has(panel.key)) continue;
    for (const testKey of panel.test_keys) selected.add(testKey);
  }
  const categoryOrder = new Map(catalog.categories.map((category) => [category.key, category.order]));
  return catalog.tests
    .map((test, index) => ({ test, index }))
    .sort((left, right) => (
      (categoryOrder.get(left.test.primary_category) ?? Number.MAX_SAFE_INTEGER)
      - (categoryOrder.get(right.test.primary_category) ?? Number.MAX_SAFE_INTEGER)
      || left.index - right.index
    ))
    .map(({ test }) => test.test_key)
    .filter((testKey) => selected.has(testKey));
}

export function buildLabRows(draftRows: LabDraftRow[]): LabCreateRequest["results"] {
  return draftRows.flatMap((row) => {
    const enteredValue = normalizeLabNumber(row.value);
    if (!enteredValue) return [];
    return [{
      test_key: row.testKey,
      entered_value: enteredValue,
      entered_unit: row.unit,
    }];
  });
}

export function mapLabErrors(detail: LabFieldError[]): LabMappedErrors {
  const mapped: LabMappedErrors = { rows: {} };
  for (const error of detail) {
    const locField = [...error.loc].reverse().find((part): part is string => typeof part === "string");
    const field = error.field ?? locField;
    if (field === "test_date" && !error.test_key) {
      mapped.test_date ??= error.msg;
      continue;
    }
    if (error.test_key) {
      const row = (mapped.rows[error.test_key] ??= {});
      if (field === "entered_value" || field === "entered_unit") row[field] ??= error.msg;
      else row.form ??= error.msg;
      continue;
    }
    mapped.form ??= error.msg;
  }
  return mapped;
}
