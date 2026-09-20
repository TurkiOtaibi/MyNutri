import type {
  LabCatalogResponse,
  LabChartZoneSegment,
  LabCreateRequest,
  LabResultResponse,
} from "@/lib/types";
import type { BatchDraft } from "@/features/labs/lab-batch-model";
import type { LabListItem } from "@/features/labs/lab-model";

const tests = [
  {
    test_key: "ferritin",
    name_ar: "الفيريتين",
    name_en: "Ferritin",
    abbreviation: null,
    primary_category: "iron",
    measurement: "Ferritin",
    specimen_context: "serum_or_plasma_biochemistry",
    default_input_unit: "ng/mL",
    canonical_unit: "ng/mL",
    supported_units: ["ng/mL", "µg/L"],
    fasting_assumption: "fasting",
    panels: ["iron_studies"],
  },
  {
    test_key: "eosinophils_pct",
    name_ar: "نسبة الحمضات",
    name_en: "Eosinophils %",
    abbreviation: null,
    primary_category: "blood",
    measurement: "Eosinophils %",
    specimen_context: "whole_blood",
    default_input_unit: "%",
    canonical_unit: "%",
    supported_units: ["%"],
    fasting_assumption: "not_required",
    panels: ["cbc"],
  },
  {
    test_key: "hba1c",
    name_ar: "السكر التراكمي",
    name_en: "Hemoglobin A1c",
    abbreviation: "HbA1c",
    primary_category: "glycemic",
    measurement: "Hemoglobin A1c",
    specimen_context: "whole_blood",
    default_input_unit: "%",
    canonical_unit: "%",
    supported_units: ["%", "mmol/mol"],
    fasting_assumption: "not_required",
    panels: [],
  },
] satisfies LabCatalogResponse["tests"];

export const catalogFixture: LabCatalogResponse = {
  medical_rules_version: "labs-v1",
  categories: [
    { key: "glycemic", name_ar: "السكر", order: 0 },
    { key: "blood", name_ar: "الدم", order: 2 },
    { key: "iron", name_ar: "الحديد", order: 3 },
  ],
  panels: [
    {
      key: "cbc",
      name_ar: "صورة الدم",
      name_en: "CBC",
      test_keys: ["eosinophils_pct"],
    },
    {
      key: "iron_studies",
      name_ar: "دراسات الحديد",
      name_en: "Iron Studies",
      test_keys: ["ferritin"],
    },
  ],
  tests,
};

export const createFixture: LabCreateRequest = {
  test_date: "2026-09-19",
  results: [{ test_key: "hba1c", entered_value: "5.270", entered_unit: "%" }],
};

export const draftFixture: BatchDraft = {
  actorId: "actor-a",
  testDate: "2026-09-19",
  rows: [{ testKey: "hba1c", value: "5.270", unit: "%" }],
};

export function resultFixture(
  testKey: string,
  testDate: string,
  updatedAt: string,
): LabResultResponse {
  const keyOrdinal = catalogFixture.tests.findIndex((item) => item.test_key === testKey) + 1;
  const idSuffix = `${Math.max(keyOrdinal, 0)}${testDate.replace(/\D/g, "")}`.padEnd(12, "0").slice(0, 12);
  const unit = testKey === "ferritin" ? "ng/mL" : "%";
  return {
    id: `00000000-0000-4000-8000-${idSuffix}`,
    test_key: testKey,
    test_date: testDate,
    entered_value: "5.270",
    entered_unit: unit,
    created_at: `${testDate}T08:00:00Z`,
    updated_at: `${updatedAt}T08:00:00Z`,
    display_value: "5.27",
    display_unit: unit,
    display_is_approximate: false,
    status: { code: "normal", label_ar: "طبيعي", tone: "positive" },
    age_years: 30,
    reference_zones: [],
    medical_rules_version: "labs-v1",
  };
}

export function overviewItem(testKey: string, date: string, updated: string): LabListItem {
  const test = catalogFixture.tests.find((item) => item.test_key === testKey);
  if (!test) throw new Error(`Unknown fixture test: ${testKey}`);
  return {
    test_key: testKey,
    test,
    latest: resultFixture(testKey, date, updated),
    last_updated_at: `${updated}T08:00:00Z`,
  };
}

export function historyFixture(count: number): LabResultResponse[] {
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(Date.UTC(2026, 8, 19));
    date.setUTCDate(date.getUTCDate() - (count - index - 1));
    const day = date.toISOString().slice(0, 10);
    return resultFixture("hba1c", day, day);
  });
}

export const zoneFixture: LabChartZoneSegment[] = [{
  from_date: "2026-05-23",
  to_date_exclusive: "2026-09-20",
  age_min: 30,
  zones: [],
}];

export const ferritinFemaleHistory: LabResultResponse[] = [
  { ...resultFixture("ferritin", "2020-01-01", "2020-01-01"), age_years: 50 },
  { ...resultFixture("ferritin", "2022-01-01", "2022-01-01"), age_years: 52 },
];

export const ferritinAge51Segments: LabChartZoneSegment[] = [
  {
    from_date: "2020-01-01",
    to_date_exclusive: "2021-01-01",
    age_min: 18,
    zones: [
      { status: { code: "low", label_ar: "منخفض", tone: "negative" }, low: null, high: "6", low_inclusive: false, high_inclusive: false },
      { status: { code: "in_range", label_ar: "ضمن النطاق", tone: "positive" }, low: "6", high: "175", low_inclusive: true, high_inclusive: true },
      { status: { code: "high", label_ar: "مرتفع", tone: "negative" }, low: "175", high: null, low_inclusive: false, high_inclusive: false },
    ],
  },
  {
    from_date: "2021-01-01",
    to_date_exclusive: "2022-01-02",
    age_min: 51,
    zones: [
      { status: { code: "low", label_ar: "منخفض", tone: "negative" }, low: null, high: "11", low_inclusive: false, high_inclusive: false },
      { status: { code: "in_range", label_ar: "ضمن النطاق", tone: "positive" }, low: "11", high: "328", low_inclusive: true, high_inclusive: true },
      { status: { code: "high", label_ar: "مرتفع", tone: "negative" }, low: "328", high: null, low_inclusive: false, high_inclusive: false },
    ],
  },
];
