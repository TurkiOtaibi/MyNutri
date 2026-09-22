import type { LabCatalogResponse, LabCreateRequest, LabCreateReceipt, LabFieldError } from "@/lib/types";

export type LabDraftRow = { testKey: string; value: string; unit: string };
export type BatchDraft = {
  actorId: string; date: string; panelKeys: string[]; individualKeys: string[];
  rows: Record<string, { value: string; unit: string }>;
  step: "date" | "selection" | "values";
};
export type PendingBatch = { actorId: string; key: string; payload: LabCreateRequest };
export type BatchPhase =
  | { kind: "editing"; draft: BatchDraft }
  | { kind: "submitting" | "ambiguous"; draft: BatchDraft; pending: PendingBatch }
  | { kind: "validation_error"; draft: BatchDraft; errors: LabFieldError[] }
  | { kind: "saved"; receipt: LabCreateReceipt; replayed: boolean };
export type BatchAction =
  | { type: "OPEN"; draft: BatchDraft }
  | { type: "RESET" | "CANCEL" | "NEXT" | "BACK" | "NETWORK_AMBIGUOUS" | "RETRY" }
  | { type: "EDIT_DATE"; date: string }
  | { type: "EDIT_VALUE"; testKey: string; value: string }
  | { type: "EDIT_UNIT"; testKey: string; unit: string }
  | { type: "PANEL" | "INDIVIDUAL"; key: string; selected: boolean; catalog: LabCatalogResponse }
  | { type: "SUBMIT"; pending: PendingBatch }
  | { type: "VALIDATION_ERROR"; errors: LabFieldError[] }
  | { type: "SAVED"; receipt: LabCreateReceipt; replayed: boolean };

function selectedRows(draft: BatchDraft, catalog: LabCatalogResponse): BatchDraft["rows"] {
  return Object.fromEntries(selectedTestKeys(draft.panelKeys, draft.individualKeys, catalog).map((key) => [
    key, draft.rows[key] ?? { value: "", unit: catalog.tests.find((test) => test.test_key === key)!.default_input_unit },
  ]));
}

export function createBatchDraft(actorId: string, serverToday: string, catalog: LabCatalogResponse, individualKeys: string[] = []): BatchDraft {
  const draft: BatchDraft = { actorId, date: serverToday, panelKeys: [], individualKeys, rows: {}, step: "date" };
  return { ...draft, rows: selectedRows(draft, catalog) };
}

export function populatedCount(draft: BatchDraft): number {
  return Object.values(draft.rows).filter((row) => row.value.trim() !== "").length;
}

export function freezeBatch(draft: BatchDraft, key: string): PendingBatch {
  const results = buildLabRows(Object.entries(draft.rows).map(([testKey, row]) => ({ testKey, ...row })));
  if (!results.length) throw new Error("أدخل نتيجة واحدة على الأقل.");
  results.forEach(Object.freeze);
  Object.freeze(results);
  return Object.freeze({ actorId: draft.actorId, key, payload: Object.freeze({ test_date: draft.date, results }) });
}

export function batchErrorTarget(error: LabFieldError): { step: BatchDraft["step"]; id: string } {
  if (error.code === "LAB_PROFILE_REQUIRED") return { step: "date", id: "lab-batch-errors" };
  const field = error.field ?? [...error.loc].reverse().find((part) => typeof part === "string");
  if (error.test_key) return { step: "values", id: `lab-${error.test_key}-${field === "entered_unit" ? "unit" : "value"}` };
  if (field === "test_date") return { step: "date", id: "lab-batch-date" };
  return { step: "values", id: "lab-batch-errors" };
}

export function batchReducer(state: BatchPhase | null, action: BatchAction): BatchPhase | null {
  if (action.type === "RESET") return null;
  if (action.type === "OPEN") return !state || state.kind === "saved" ? { kind: "editing", draft: action.draft } : state;
  if (!state) return state;
  if (state.kind === "submitting" || state.kind === "ambiguous") {
    if (action.type === "NETWORK_AMBIGUOUS") return { ...state, kind: "ambiguous" };
    if (action.type === "RETRY" && state.kind === "ambiguous") return { ...state, kind: "submitting" };
    if (action.type === "SAVED") return { kind: "saved", receipt: action.receipt, replayed: action.replayed };
    if (action.type === "VALIDATION_ERROR") return {
      kind: "validation_error", draft: { ...state.draft, step: action.errors[0] ? batchErrorTarget(action.errors[0]).step : "values" }, errors: action.errors,
    };
    return state;
  }
  if (action.type === "CANCEL") return null;
  if (state.kind === "saved") return state;
  let draft = state.draft;
  switch (action.type) {
    case "EDIT_DATE": draft = { ...draft, date: action.date }; break;
    case "EDIT_VALUE":
    case "EDIT_UNIT": {
      if (!draft.rows[action.testKey]) return state;
      draft = { ...draft, rows: { ...draft.rows, [action.testKey]: { ...draft.rows[action.testKey], ...(action.type === "EDIT_VALUE" ? { value: action.value } : { unit: action.unit }) } } };
      break;
    }
    case "PANEL":
    case "INDIVIDUAL": {
      const field = action.type === "PANEL" ? "panelKeys" : "individualKeys";
      const keys = draft[field].filter((key) => key !== action.key);
      if (action.selected) keys.push(action.key);
      draft = { ...draft, [field]: keys };
      draft = { ...draft, rows: selectedRows(draft, action.catalog) };
      break;
    }
    case "NEXT": draft = { ...draft, step: draft.step === "date" ? "selection" : "values" }; break;
    case "BACK": draft = { ...draft, step: draft.step === "values" ? "selection" : "date" }; break;
    case "SUBMIT": return action.pending.actorId === draft.actorId ? { kind: "submitting", draft, pending: action.pending } : state;
    default: return state;
  }
  return { kind: "editing", draft };
}
export type LabRowErrors = { entered_value?: string; entered_unit?: string; form?: string };
export type LabMappedErrors = {
  test_date?: string;
  rows: Record<string, LabRowErrors>;
  form?: string;
};

const arabicDigits = "٠١٢٣٤٥٦٧٨٩";
const persianDigits = "۰۱۲۳۴۵۶۷۸۹";

export function normalizeLabNumber(raw: string): string {
  const normalized = raw
    .trim()
    .replace(/[٠-٩]/g, (digit) => String(arabicDigits.indexOf(digit)))
    .replace(/[۰-۹]/g, (digit) => String(persianDigits.indexOf(digit)))
    .replace(/٫/g, ".");
  // Remove grouping only when it is unambiguous. Invalid text stays invalid for server validation.
  return /^[0-9]{1,3}(?:٬[0-9]{3})+(?:\.[0-9]+)?$/.test(normalized)
    ? normalized.replace(/٬/g, "")
    : normalized;
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
    if (!row.value.trim()) return [];
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
