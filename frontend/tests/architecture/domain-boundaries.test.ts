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
    "DraftProfile", "ProfileField", "FieldErrors", "SheetKind", "TargetPlanSubmission",
    "TargetPlanWritePhase", "BlockingSafetyOutcome", "PROTEIN_DEFAULT", "FAT_DEFAULTS",
    "PROFILE_LIMITS", "activityDescriptions", "activityDisplayLabels", "goalDescriptions",
    "goalDisplayLabels", "toDraft", "blankDraft", "formatEditableNumber", "normalizeNumber",
    "normalizeDraft", "validateDraft", "blockingSafetyMessage", "isPreviewActivatable",
    "profileMatchesAcceptedPlan", "formatArabicGregorianDate", "formatTargetNumber",
    "mapProfileApiErrors",
  ],
  "features/profile/profile-controls.tsx": [
    "SettingsButton", "NumericSettingsRow", "SelectionCard", "OptionList",
    "cutIntensityOptions", "CutIntensitySelector",
  ],
  "features/profile/profile-targets.tsx": [
    "TargetsCard", "TargetValue", "AdditionalTargetsCard", "RegistryState",
    "TargetPlanHistory", "ExpectedTargetsCard",
  ],
  "features/profile/profile-dialogs.tsx": [
    "ProfileSheet", "ProfileConfirm", "ProfileSkeleton", "ProfileLoadError",
  ],
  "features/profile/profile-view.tsx": ["ProfileView"],
  "features/diary/diary-summary.tsx": [
    "CompactWeekNavigator", "DailyProgressSummary", "MacroProgress", "MealSections",
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
    "mealLabels", "standardMeals", "shortWeekdays", "mealAddLabels",
    "mealItemCountLabel", "emptyNutritionTotals", "formatDiarySelectedDate",
    "pickerServingNutrition", "multiplyServing", "scaleEntryPreview", "parseQuantity",
    "validateQuantity", "entryQuantityLabel",
  ],
  "features/diary/diary-hooks.ts": ["useDebouncedValue", "invalidateDiary"],
  "features/foods/food-form-model.ts": ["fieldId", "mapFoodApiError"],
  "features/foods/food-form-fields.tsx": [
    "FormSection", "FoodFormActions", "TextField",
    "TextAreaField", "NumberField", "SelectField",
  ],
  "features/foods/food-nutrients.ts": [
    "EditableFoodNutrient", "FoodNutrientSpec", "FoodNutrientGroup",
    "FoodNutrientAdapter", "createFoodNutrientAdapter",
  ],
  "features/foods/food-catalog-view.tsx": [
    "FoodTableRow", "FoodCard", "DesktopPagination", "FoodsLoading", "EmptyFoodsState",
  ],
  "features/foods/food-details-view.tsx": [
    "FoodDetailsLoading", "DetailServingMetric", "NutritionCompleteness",
    "NutrientGroup", "MetadataRow", "formatFoodDate",
  ],
  "features/labs/lab-model.ts": [
    "LabListItem", "LabSort", "toLabListItems", "filterLabs", "sortLabs",
  ],
  "features/labs/lab-query-keys.ts": ["labsQueryKeys"],
  "features/labs/lab-batch-model.ts": [
    "LabDraftRow", "BatchDraft", "LabRowErrors", "LabMappedErrors",
    "normalizeLabNumber", "selectedTestKeys", "buildLabRows", "mapLabErrors",
  ],
  "features/labs/labs-overview-view.tsx": ["OwnedLabsView", "LabCatalogView"],
} as const;

function expectTransportBoundary(source: string) {
  expect(source).toContain('cache: "no-store"');
  expect(source).toContain('headers.set("Authorization", `Bearer ${data.session.access_token}`)');
  expect(source).toContain('headers: { "Idempotency-Key": idempotencyKey }');
  expect(source).toContain('apiFetch<ProfileResponse>("/profile"');
  expect(source).toContain('apiFetch<TargetResponse>("/profile/preview"');
  expect(source).toContain('apiFetch<TargetPlanWriteResponse>("/target-plans"');
  expect(source).not.toContain("/target-plans/activate");
  expect(source).not.toContain("/target-plans/pending");
  expect(source).toContain('apiFetch<FoodPickerResponse>');
  expect(source).toContain('`/admin/users/${principalId}/diary?${params.toString()}`');
  expect(source).toContain('apiFetch<DiaryEntryResponse>("/diary/entries"');
  expect(source).not.toContain("/diary/days/");
  expect(source).not.toContain("If-Match");
  expect(source).toContain('throw new ApiError(message, response.status, detail, code)');
  expect(source).toContain('apiFetch<LabCatalogResponse>("/labs/catalog"');
  expect(source).toContain('apiFetch<LabOverviewResponse>("/labs"');
  expect(source).toMatch(/apiFetchWithResponse<LabCreateReceipt>\(\s*"\/labs\/results"/);
  expect(source).toContain('response.headers.get("Idempotent-Replayed")');
  expect(source).toContain('`/admin/users/${encodeURIComponent(principalId)}/labs`');
}

function expectCriticalDialogSemantics(source: string) {
  expect(source).toContain('role="dialog"');
  expect(source).toContain('aria-modal="true"');
  expect(source).toContain('aria-labelledby="profile-sheet-title"');
  expect(source).toContain('aria-live="polite"');
}

function expectFoodsCatalogOwnership(page: string, presentation: string) {
  expect(page).toContain('queryKey: ["foods", "catalog", search, category, sort, page]');
  expect(page).toMatch(/queryFn:\s*\(\) => listFoodsPage\(\{[\s\S]*?search,[\s\S]*?category,[\s\S]*?sort,[\s\S]*?page,[\s\S]*?pageSize: PAGE_SIZE/);
  expect(page).toMatch(/const \[searchInput, setSearchInput\] = useState\(""\)/);
  expect(page).toMatch(/const \[mobileItems, setMobileItems\] = useState<FoodResponse\[]>\(\[\]\)/);
  expect(page).toMatch(/const \[page, setPage\] = useState\(1\)/);
  expect(page).toContain("window.setTimeout");
  expect(page).toContain("resetCollection");
  expect(page).toContain("setMobileItems");
  expect(page).toContain("useFoodDelete");

  expect(presentation).not.toMatch(/@tanstack\/react-query|@\/lib\/api/);
  expect(presentation).not.toMatch(/\b(?:useQuery|useInfiniteQuery|useMutation|useState|useReducer)\b/);
  expect(presentation).not.toMatch(/\b(?:listFoodsPage|getNutritionRegistry|useFoodDelete|resetCollection|setMobileItems)\b/);
}

function expectLabsOverviewOwnership(owner: string, admin: string, presentation: string) {
  expect(owner).toMatch(/\buseQuery\b/);
  expect(owner).toContain("getLabCatalog");
  expect(owner).toContain("getLabs");
  expect(owner).toContain("labsQueryKeys.catalog");
  expect(owner).toContain("labsQueryKeys.ownerOverview");
  expect(owner).toMatch(/const \[search, setSearch\] = useState\(""\)/);
  expect(owner).toMatch(/const \[category, setCategory\] = useState<string \| null>\(null\)/);
  expect(owner).toMatch(/const \[sort, setSort\] = useState<LabSort>\("newest_updated"\)/);
  expect(`${owner}\n${admin}`).toContain('staleTime: 0');
  expect(`${owner}\n${admin}`).toContain('refetchOnMount: "always"');
  expect(`${owner}\n${admin}`).toContain('refetchOnWindowFocus: "always"');
  expect(`${owner}\n${admin}`).not.toContain("refetchInterval");
  expect(`${owner}\n${admin}`).toContain("AbortSignal.any([signal, sessionSignal])");

  expect(admin).toContain("getAdminLabs");
  expect(admin).toContain("labsQueryKeys.adminOverview");
  expect(admin).not.toMatch(/\b(?:createLabResults|updateLabResult|deleteLabResult|useMutation)\b/);

  expect(presentation).not.toMatch(/@tanstack\/react-query|@\/lib\/api/);
  expect(presentation).not.toMatch(/\b(?:useQuery|useInfiniteQuery|useMutation|useState|useReducer)\b/);
  expect(presentation).toContain("OwnedLabsView");
  expect(presentation).toContain("LabCatalogView");
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
    expect(view).not.toMatch(/\b(?:Dispatch|SetStateAction|setPendingServerProfile|reconcileAcceptedPlan|transitionWrite|writePhaseRef)\b/);
    expect(view).toMatch(/type ProfileViewProps = \{\s*profile: ProfileViewState;\s*targets: ProfileTargetsViewState;\s*write: ProfileWriteViewState;\s*intents: ProfileViewIntents;\s*\}/s);
    expect(read("components/ProfilePage.tsx")).toMatch(/\buseQuery\b/);
  });

  it("keeps focused cleanups and food presentation ownership explicit", () => {
    expect(read("components/FoodDeleteDialog.tsx")).not.toContain("confirmRef");
    expect(read("components/AuthProvider.tsx")).not.toContain("export type RecoveryStatus");
    expect(read("components/AdminUserDetailsPage.tsx")).toContain("useErrorOccurrenceFocus");

    const foodsSource = `${read("components/FoodsPage.tsx")}\n${featureSource("foods")}`;
    expect(foodsSource).not.toContain("لا توجد أطعمة نشطة في الكتالوج حاليًا.");
    expect(read("components/FoodsPage.tsx")).not.toMatch(/function\s+(?:FoodTableRow|FoodCard|DesktopPagination|FoodsLoading|EmptyFoodsState)\b/);
    expect(read("components/FoodDetailsPage.tsx")).not.toMatch(/function\s+(?:FoodDetailsLoading|DetailServingMetric|NutritionCompleteness|NutrientGroup|MetadataRow)\b/);
    expectFoodsCatalogOwnership(
      read("components/FoodsPage.tsx"),
      [
        read("features/foods/food-catalog-view.tsx"),
        read("features/foods/food-details-view.tsx"),
        read("features/foods/food-nutrients.ts"),
      ].join("\n"),
    );
  });

  it("proves the Foods ownership oracle rejects query, state, and presentation regressions", () => {
    const page = read("components/FoodsPage.tsx");
    const presentation = read("features/foods/food-catalog-view.tsx");

    expect(() => expectFoodsCatalogOwnership(
      page.replace('queryKey: ["foods", "catalog", search, category, sort, page]', 'queryKey: ["foods"]'),
      presentation,
    )).toThrow();
    expect(() => expectFoodsCatalogOwnership(
      page.replace("setMobileItems", "appendMobileItems"),
      presentation,
    )).toThrow();
    expect(() => expectFoodsCatalogOwnership(
      page,
      `${presentation}\nconst leakedState = useState([]);`,
    )).toThrow();
  });

  it("keeps query keys and critical Arabic copy in their owning domains", () => {
    const sources = [
      read("components/ProfilePage.tsx"), read("components/DiaryPage.tsx"),
      read("components/FoodFormPage.tsx"), read("components/useFoodDelete.ts"), featureSource("profile"),
      featureSource("diary"), featureSource("foods"),
    ].join("\n");
    for (const key of [
      '["profile", subjectId]', '["calendar-authority", subjectId]', '["nutrition-registry"]',
      '["target-plan-history", subjectId]', '["week", session?.user.id, weekStart]',
      '["entries", session?.user.id, activeDate]',
      '["diary-food-picker", session?.user.id, normalizedSearch]',
      '["diary-food-picker"]', '["entries"]', '["admin-user-diary"]',
      '["food", foodId]', '["foods"]',
    ]) expect(sources).toContain(key);
    for (const copy of [
      "تعذر تحميل بياناتك",
      "لا يمكن حفظ هذا الهدف لأنه غير مناسب لحالتك الحالية",
      "تعذر تحميل تفاصيل الطعام. تحقق من الاتصال وحاول مرة أخرى.",
      "راجع الحقول المحددة ثم حاول مرة أخرى.",
    ]) expect(sources).toContain(copy);
  });

  it("enforces private feature direction and generated transport ownership", () => {
    for (const domain of ["profile", "diary", "foods", "labs"]) {
      for (const path of walk(`features/${domain}`).filter((item) => /\.(?:ts|tsx)$/.test(item))) {
        expect(read(path), path).not.toMatch(new RegExp(`@/features/(?!${domain}/)`));
      }
    }
    expect(read("lib/types.ts")).toContain('from "./generated/openapi"');
    expect(read("lib/api.ts")).toContain('from "./generated/openapi"');
    expect(read("components/AdminUserDetailsPage.tsx")).not.toMatch(/Record<string, unknown>|as unknown as/);
    expect(featureSource("labs")).not.toMatch(/prediabetes_range|diabetes_range|toCanonical|resolveRule|referenceThreshold/);
  });

  it("keeps Labs owner/admin queries, volatile filters, and read-only presentation separated", () => {
    const owner = read("components/LabsPage.tsx");
    const admin = read("components/AdminUserLabsPage.tsx");
    const presentation = read("features/labs/labs-overview-view.tsx");
    expectLabsOverviewOwnership(owner, admin, presentation);
    expect(read("components/AdminUserDetailsPage.tsx")).toContain("/labs");
    expect(read("features/labs/labs.module.css")).toContain(".labsPage");
  });

  it("proves the Labs ownership oracle rejects query, write-import, and state regressions", () => {
    const owner = read("components/LabsPage.tsx");
    const admin = read("components/AdminUserLabsPage.tsx");
    const presentation = read("features/labs/labs-overview-view.tsx");
    expect(() => expectLabsOverviewOwnership(
      owner.replace("labsQueryKeys.ownerOverview", "labsQueryKeys.ownerRoot"),
      admin,
      presentation,
    )).toThrow();
    expect(() => expectLabsOverviewOwnership(
      owner,
      `${admin}\nconst leak = deleteLabResult;`,
      presentation,
    )).toThrow();
    expect(() => expectLabsOverviewOwnership(
      owner,
      admin,
      `${presentation}\nconst leakedState = useState([]);`,
    )).toThrow();
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
