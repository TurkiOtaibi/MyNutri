import { readFileSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const root = resolve(import.meta.dirname, "../..");
const read = (relativePath: string) => readFileSync(resolve(root, relativePath), "utf8");
const walk = (relativePath: string): string[] => readdirSync(resolve(root, relativePath))
  .flatMap((name) => {
    const child = `${relativePath}/${name}`;
    return statSync(resolve(root, child)).isDirectory() ? walk(child) : [child];
  });
const featureSource = (domain: string) => walk(`features/${domain}`)
  .filter((path) => /\.(?:ts|tsx)$/.test(path))
  .map(read)
  .join("\n");

const manifests = {
  "features/profile/profile-model.ts": [
    "DraftProfile", "ProfileField", "FieldErrors", "SheetKind", "ActivationSubmission",
    "ActivationPhase", "BlockingSafetyOutcome", "PROTEIN_DEFAULT", "FAT_DEFAULTS",
    "PROFILE_LIMITS", "activityDescriptions", "activityDisplayLabels", "goalDescriptions",
    "goalDisplayLabels", "toDraft", "blankDraft", "formatEditableNumber", "normalizeNumber",
    "normalizeDraft", "validateDraft", "blockingSafetyMessage", "isPreviewActivatable",
    "profileMatchesAcceptedActivation", "formatArabicGregorianDate", "formatTargetNumber",
    "mapProfileApiErrors",
  ],
  "features/profile/profile-controls.tsx": [
    "SettingsButton", "NumericSettingsRow", "SelectionCard", "OptionList",
    "cutIntensityOptions", "CutIntensitySelector",
  ],
  "features/profile/profile-targets.tsx": [
    "TargetsCard", "TargetValue", "AdditionalTargetsCard", "RegistryState",
    "TargetPlanHistory", "ScheduledPlanCard", "ExpectedTargetsCard",
  ],
  "features/profile/profile-dialogs.tsx": [
    "ProfileSheet", "ProfileConfirm", "ProfileSkeleton", "ProfileLoadError",
  ],
  "features/profile/profile-view.tsx": ["ProfileView"],
  "features/diary/diary-summary.tsx": [
    "CompactWeekNavigator", "DayLoggingStatusCard", "DailyProgressSummary", "MacroProgress", "MealSections",
    "DiaryEntryRow", "DailyNutritionDetails", "DailyNutrientRow",
  ],
  "features/diary/diary-entry-dialogs.tsx": [
    "AddEntrySheet", "FoodResultGroup", "FoodResultRow", "FoodResultSkeletons",
    "SelectedFoodSummary", "EditEntryDialog", "MealTypeSelector", "QuantityStepper",
    "ConfirmDialog", "ModalFocusScope", "modalFocusScopes", "focusableElements",
    "topModalScope", "syncModalFocusOwnership", "handleModalKeyDown",
    "registerModalFocusScope", "unregisterModalFocusScope", "ModalFrame", "RetryState",
    "DiaryEntriesSkeleton",
  ],
  "features/diary/diary-model.ts": [
    "dayLoggingStatusLabels", "isDayAnalysisEligible", "isFutureDiaryStatus", "mealLabels", "standardMeals", "shortWeekdays", "mealAddLabels",
    "mealItemCountLabel", "emptyNutritionTotals", "formatDiarySelectedDate",
    "pickerServingNutrition", "multiplyServing", "scaleEntryPreview", "parseQuantity",
    "validateQuantity", "entryQuantityLabel", "snapshotUnitLabel",
  ],
  "features/diary/diary-hooks.ts": ["useDebouncedValue", "invalidateDiary"],
  "features/foods/food-form-model.ts": [
    "optionalFields", "traitGroups", "traitHelp", "relevantTraitKeys",
    "suggestedGroupKey", "subtypeKeys", "fieldId", "mapFoodApiError",
  ],
  "features/foods/food-form-fields.tsx": [
    "FormSection", "FoodGroupFields", "FoodFormActions", "TextField",
    "TextAreaField", "NumberField", "SelectField",
  ],
  "features/progress/progress-model.ts": [
    "ANALYSIS_COPY", "metricLabels", "AnalysisDisplayState", "displayState",
    "visibleMetrics", "metricLabel", "metricStatusText", "formatMetricValue",
    "AnalysisAttempt", "stableAnalysisAttempt", "PRIORITY_COPY", "goalStateCopy",
    "goalActionCopy", "GoalCommandAttempt", "stableGoalCommandAttempt", "priorityMessage",
  ],
  "features/progress/progress-view.tsx": ["ProgressView"],
} as const;

function expectTransportBoundary(source: string) {
  expect(source).toContain('cache: "no-store"');
  expect(source).toContain('headers.set("Authorization", `Bearer ${data.session.access_token}`)');
  expect(source).toContain('headers: { "Idempotency-Key": idempotencyKey }');
  expect(source).toContain('apiFetch<ProfileResponse>("/profile"');
  expect(source).toContain('apiFetch<TargetResponse>("/profile/preview"');
  expect(source).toContain('apiFetch<FoodPickerResponse>');
  expect(source).toContain('`/admin/users/${principalId}/diary?${params.toString()}`');
  expect(source).toContain('apiFetch<DiaryEntryResponse>("/diary/entries"');
  expect(source).toContain('`/diary/days/${diaryDate}/status`');
  expect(source).toContain('`/diary/days/${diaryDate}/${action}`');
  expect(source).toContain('"/progress/nutrition-analysis/current"');
  expect(source).toContain('"/progress/nutrition-analysis/evaluate"');
  expect(source).toContain('"/progress/weekly-priorities/current"');
  expect(source).toContain('"/progress/behavior-goals/current"');
  expect(source).toContain('`/progress/behavior-goals/${goalId}/commands`');
  expect(source).toContain('"If-Match": etag ?? \'"analysis-none"\'');
  expect(source).toContain('headers: { "If-Match": `"day-${dayVersion}"` }');
  expect(source).toContain('throw new ApiError(message, response.status, detail, code)');
}

function expectCriticalDialogSemantics(source: string) {
  expect(source).toContain('role="dialog"');
  expect(source).toContain('aria-modal="true"');
  expect(source).toContain('aria-labelledby="profile-sheet-title"');
  expect(source).toContain('aria-live="polite"');
}

const movedSelectors = [
  ["features/profile/profile.module.css", ["profile-page", "profile-preview-card"]],
  ["features/diary/diary.module.css", ["diary-page", "compact-week-day"]],
  ["features/foods/food-form.module.css", ["food-form-layout", "food-form-section"]],
] as const;

const cssDomains = [
  ["profile", "features/profile/profile.module.css", "components/ProfilePage.tsx"],
  ["diary", "features/diary/diary.module.css", "components/DiaryPage.tsx"],
  ["foods", "features/foods/food-form.module.css", "components/FoodFormPage.tsx"],
] as const;

function expectMovedSelectorOwnership(globals: string) {
  for (const [modulePath, selectors] of movedSelectors) {
    const moduleCss = read(modulePath);
    for (const selector of selectors) {
      expect(moduleCss).toContain(`:global(.${selector})`);
      expect(globals).not.toContain(`.${selector} {`);
    }
  }
}

describe("domain boundaries", () => {
  it("freezes transport paths, authorization, cache, and error mapping", () => {
    expectTransportBoundary(read("lib/api.ts"));
  });

  it("proves the transport oracle rejects a controlled path mutation", () => {
    const source = read("lib/api.ts").replace('"/profile/preview"', '"/profile-preview"');
    expect(() => expectTransportBoundary(source)).toThrow();
  });

  it("freezes critical dialog and live-region accessibility semantics", () => {
    expectCriticalDialogSemantics(`${featureSource("profile")}\n${featureSource("diary")}`);
  });

  it("proves the DOM oracle rejects a controlled accessibility mutation", () => {
    const source = `${featureSource("profile")}\n${featureSource("diary")}`
      .replace('role="dialog"', 'role="region"');
    expect(() => expectCriticalDialogSemantics(source)).toThrow();
  });

  it("enforces the exact extraction manifest and stable thin orchestrators", () => {
    for (const [path, symbols] of Object.entries(manifests)) {
      const source = read(path);
      for (const symbol of symbols) {
        expect(source, `${symbol} must live in ${path}`).toMatch(
          new RegExp(`(?:export\\s+)?(?:function|const|type|interface)\\s+${symbol}\\b`),
        );
      }
    }

    for (const [path, exportName, limit] of [
      ["components/ProfilePage.tsx", "ProfilePage", 550],
      ["components/DiaryPage.tsx", "DiaryPage", 430],
      ["components/FoodFormPage.tsx", "FoodFormPage", 450],
    ] as const) {
      const source = read(path);
      expect(source.split(/\r?\n/).length - 1, path).toBeLessThanOrEqual(limit);
      expect(source).toContain(`export function ${exportName}(`);
      expect([...source.matchAll(/^(?:export\s+)?function\s+(\w+)/gm)].map((match) => match[1]))
        .toEqual([exportName]);
    }

    const view = read("features/profile/profile-view.tsx");
    expect(view).not.toMatch(/\b(?:useQuery|useInfiniteQuery|useMutation|useState|useEffect|useLayoutEffect)\b/);
    expect(read("components/ProfilePage.tsx")).toMatch(/\buseQuery\b/);
  });

  it("keeps query keys and critical Arabic copy in their owning domains", () => {
    const sources = [
      read("components/ProfilePage.tsx"), read("components/DiaryPage.tsx"),
      read("components/FoodFormPage.tsx"), featureSource("profile"),
      featureSource("diary"), featureSource("foods"),
    ].join("\n");
    for (const key of [
      '["profile"]', '["calendar-authority"]', '["nutrition-registry"]',
      '["target-plan-history"]', '["week", session?.user.id, weekStart]',
      '["entries", session?.user.id, activeDate]',
      '["diary-day-status", session?.user.id, activeDate]',
      '["diary-food-picker", session?.user.id, normalizedSearch]',
      '["food", foodId]', '["foods"]',
    ]) expect(sources).toContain(key);
    for (const copy of [
      "تعذر تحميل بياناتك",
      "لا يمكن تفعيل هذا الهدف لأنه غير مناسب لحالتك الحالية",
      "لا يمكن تسجيل يوميات بتاريخ مستقبلي.",
      "تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.",
      "راجع الحقول المحددة ثم حاول مرة أخرى.",
    ]) expect(sources).toContain(copy);
  });

  it("enforces private feature direction and generated transport ownership", () => {
    for (const domain of ["profile", "diary", "foods", "progress"]) {
      for (const path of walk(`features/${domain}`).filter((item) => /\.(?:ts|tsx)$/.test(item))) {
        expect(read(path), path).not.toMatch(new RegExp(`@/features/(?!${domain}/)`));
      }
    }
    expect(read("lib/types.ts")).toContain('from "./generated/openapi"');
    expect(read("lib/api.ts")).toContain('from "./generated/openapi"');
    expect(read("components/AdminUserDetailsPage.tsx")).not.toMatch(/Record<string, unknown>|as unknown as/);
    expect(read("features/progress/progress-view.tsx")).not.toMatch(/\b(?:useQuery|useMutation|useState|useEffect)\b/);
    expect(read("components/ProgressPage.tsx")).toMatch(/\buseQuery\b/);
  });

  it("moves representative exclusively owned selectors without global duplicates", () => {
    expectMovedSelectorOwnership(read("app/globals.css"));
  });

  it("proves every class moved to a CSS Module is referenced only by its domain", () => {
    const tsxPaths = ["app", "components", "features"]
      .flatMap(walk)
      .filter((path) => path.endsWith(".tsx"));
    const sources = new Map(tsxPaths.map((path) => [path, read(path)]));

    for (const [domain, modulePath, pagePath] of cssDomains) {
      const classes = [
        ...read(modulePath).matchAll(/:global\(\.([A-Za-z0-9_-]+)\)/g),
      ].map((match) => match[1]);
      for (const className of new Set(classes)) {
        const references = tsxPaths.filter((path) => sources.get(path)!.includes(className));
        expect(references.length, `${className} must have a JSX owner`).toBeGreaterThan(0);
        expect(
          references.every(
            (path) => path === pagePath || path.startsWith(`features/${domain}/`),
          ),
          `${className} escaped the ${domain} domain: ${references.join(", ")}`,
        ).toBe(true);
      }
    }
  });

  it("proves the style oracle rejects a controlled global ownership regression", () => {
    const globals = `${read("app/globals.css")}\n.profile-page { color: red; }\n`;
    expect(() => expectMovedSelectorOwnership(globals)).toThrow();
  });
});
