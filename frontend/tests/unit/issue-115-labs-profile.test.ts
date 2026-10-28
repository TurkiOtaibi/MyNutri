import { createElement, type ComponentProps, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";
import { LabBatchDialog } from "@/features/labs/lab-batch-dialog";
import { createBatchDraft } from "@/features/labs/lab-batch-model";
import { activityLabels, activityDisplayLabels, goalLabels, goalDisplayLabels } from "@/features/profile/profile-model";
import { ProfileView } from "@/features/profile/profile-view";
import { catalogFixture } from "./fixtures/labs";
vi.mock("@base-ui-components/react/dialog", () => {
  const Wrapper = ({ children }: { children?: ReactNode }) => createElement("div", null, children);
  return { Dialog: Object.fromEntries(["Root", "Portal", "Backdrop", "Popup", "Title", "Description"].map(key => [key, Wrapper])) };
});
const noop = () => undefined;
const batchProps = {
  phase: { kind: "editing" as const, draft: createBatchDraft("synthetic", "2026-10-17", catalogFixture) },
  catalog: catalogFixture, serverToday: "2026-10-17",
  onDate: noop, onNote: noop, onPanel: noop, onIndividual: noop, onValue: noop, onUnit: noop,
  onNext: noop, onBack: noop, onSave: noop, onRetry: noop, onCancel: noop,
};
it("BR-LAB-013 renders all three governed step labels", () => {
  const html = renderToStaticMarkup(createElement(LabBatchDialog, batchProps));
  expect(html).toMatch(/<li[^>]*>التاريخ<\/li><li[^>]*>اختيار التحاليل<\/li><li[^>]*>القيم<\/li>/);
});
it("BR-LAB-014 displays server today separately from a changed test date", () => {
  const html = renderToStaticMarkup(createElement(LabBatchDialog, { ...batchProps, phase: { kind: "editing", draft: { ...batchProps.phase.draft, date: "2026-10-16" } } }));
  expect(html).toContain('dateTime="2026-10-16">16 أكتوبر 2026');
  expect(html).toMatch(/تاريخ اليوم:.*dateTime="2026-10-17">17 أكتوبر 2026/);
});
it("BR-PRF-027 formats effective date and confirmation while preserving the native ISO input", () => {
  const ref = { current: null };
  const props = {
    profile: { dirty: true, hasSavedProfile: true, hasPendingServerProfile: false,
      draft: { sex: "male", birth_date: "1990-01-01", height_cm: "170", weight_kg: "70", activity_level: "light", goal: "maintain", selected_cut_intensity: 0.2, protein_per_kg: "1.2", fat_percent: "25" },
      errors: {}, effectiveFrom: "2026-10-17", authoritativeDate: "2026-10-17", displayBirthDate: "1 يناير 1990", activeSheet: null, advancedOpen: false, restoreOpen: false,
      sexRef: ref, effectiveFromRef: ref, birthRef: ref, heightRef: ref, weightRef: ref, proteinRef: ref, fatRef: ref },
    targets: { savedTargets: null, registry: { pending: true, failed: false, data: undefined }, history: { plans: [], pending: false, failed: false, hasMore: false, loadingMore: false }, preview: { visible: false, current: null, pending: false, failed: false, safetyOutcome: null, safetyAttemptSequence: 0, safetyRef: ref } },
    write: { registryReady: false, validationHasPayload: true, writeErrorCode: null, writePhase: { kind: "confirming", submission: { effectiveFrom: "2026-10-17" } }, restoreWriteFocusRef: { current: true } },
    intents: new Proxy({}, { get: () => noop }),
  } as unknown as ComponentProps<typeof ProfileView>;
  const html = renderToStaticMarkup(createElement(ProfileView, props));
  expect(html).toContain('value="2026-10-17"');
  expect(html).toContain("المعاينة وحدها لا تحفظ الأهداف. تاريخ السريان 17 أكتوبر 2026.");
  expect(html).toContain('<bdi>17 أكتوبر 2026</bdi>');
  expect(html).not.toContain('>2026-10-17<');
});



it("BR-PRF-002 uses the exact approved activity labels for visible and accessible choices", () => {
  const expected = { sedentary: "خامل", light: "نشاط خفيف", moderate: "نشاط متوسط", active: "نشط", very_active: "نشط جدًا" };
  expect(activityDisplayLabels).toEqual(expected);
  expect(activityLabels).toEqual(expected);
});
it("BR-PRF-003 uses the exact approved goal labels without changing domain keys", () => {
  const expected = { cut: "خفض الوزن", maintain: "المحافظة على الوزن", bulk: "زيادة الوزن" };
  expect(goalDisplayLabels).toEqual(expected);
  expect(goalLabels).toEqual(expected);
});
