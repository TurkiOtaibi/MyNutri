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
const featurePaths = (domain: string) => walk(`features/${domain}`)
  .filter((path) => /\.(?:ts|tsx)$/.test(path));

function expectFoodsCatalogOwnership(page: string, presentation: string) {
  expect(page).toMatch(/\buseQuery\s*\(/);
  expect(page).toMatch(/\buseState\s*(?:<[^>]+>)?\s*\(/);
  expect(page).toContain("listFoodsPage");
  expect(page).toContain("useFoodDelete");

  expect(presentation).not.toMatch(/@tanstack\/react-query|@\/lib\/api/);
  expect(presentation).not.toMatch(/\b(?:useQuery|useInfiniteQuery|useMutation|useState|useReducer)\s*(?:<[^>]+>)?\s*\(/);
  expect(presentation).not.toMatch(/\b(?:listFoodsPage|getNutritionRegistry|useFoodDelete)\b/);
}

const cssDomains = [
  ["profile", "features/profile/profile.module.css", "components/ProfilePage.tsx"],
  ["diary", "features/diary/diary.module.css", "components/DiaryPage.tsx"],
  ["foods", "features/foods/food-form.module.css", "components/FoodFormPage.tsx"],
] as const;

const migratedSelectors = [
  ["features/profile/profile.module.css", ["profile-page", "profile-preview-card"]],
  ["features/diary/diary.module.css", ["diary-page", "compact-week-day"]],
  ["features/foods/food-form.module.css", ["food-form-layout", "food-form-section"]],
] as const;

function moduleClasses(modulePath: string): string[] {
  return [...read(modulePath).matchAll(/:global\(\.([A-Za-z0-9_-]+)\)/g)]
    .map((match) => match[1]);
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

describe("domain boundaries", () => {
  it("keeps ProfileView presentation-only and ProfilePage controller-owned", () => {
    const view = read("features/profile/profile-view.tsx");
    expect(view).not.toMatch(/\b(?:useQuery|useInfiniteQuery|useMutation|useState|useEffect|useLayoutEffect)\b/);
    expect(view).not.toMatch(/\b(?:Dispatch|SetStateAction|setPendingServerProfile|reconcileAcceptedPlan|transitionWrite|writePhaseRef)\b/);

    const page = read("components/ProfilePage.tsx");
    expect(page).toMatch(/\buseQuery\s*\(/);
    expect(page).toMatch(/\buseState\s*(?:<[^>]+>)?\s*\(/);
  });

  it("keeps Foods data and interaction state in FoodsPage", () => {
    expectFoodsCatalogOwnership(
      read("components/FoodsPage.tsx"),
      [
        read("features/foods/food-catalog-view.tsx"),
        read("features/foods/food-details-view.tsx"),
        read("features/foods/food-nutrients.ts"),
      ].join("\n"),
    );
  });

  it("keeps private feature dependencies within their owning domain", () => {
    for (const domain of ["profile", "diary", "foods"]) {
      for (const path of featurePaths(domain)) {
        const imports = [...read(path).matchAll(/(?:import|export)[\s\S]*?from\s+["']([^"']+)["']/g)]
          .map((match) => match[1]);
        for (const specifier of imports.filter((item) => item.startsWith("@/features/"))) {
          expect(specifier, `${path} imports ${specifier}`).toMatch(new RegExp(`^@/features/${domain}/`));
        }
      }
    }
  });

  it("keeps generated transport contracts behind lib/api and lib/types", () => {
    expect(read("lib/types.ts")).toContain('from "./generated/openapi"');
    expect(read("lib/api.ts")).toContain('from "./generated/openapi"');

    for (const path of ["app", "components", "features"]
      .flatMap(walk)
      .filter((item) => /\.(?:ts|tsx)$/.test(item))) {
      expect(read(path), path).not.toMatch(/@\/lib\/generated\//);
    }
  });

  it("keeps migrated feature-owned selectors out of the global stylesheet", () => {
    const globals = read("app/globals.css");
    for (const [modulePath, classNames] of migratedSelectors) {
      const ownedClasses = new Set(moduleClasses(modulePath));
      for (const className of classNames) {
        expect(ownedClasses, `${className} must be defined by ${modulePath}`).toContain(className);
        expect(globals, `${className} must remain owned by ${modulePath}`)
          .not.toMatch(new RegExp(`(?:^|[},]\\s*)\\.${escapeRegex(className)}\\s*\\{`, "m"));
      }
    }
  });

  it("keeps every feature-owned selector referenced only by its domain", () => {
    const tsxPaths = ["app", "components", "features"]
      .flatMap(walk)
      .filter((path) => path.endsWith(".tsx"));
    const sources = new Map(tsxPaths.map((path) => [path, read(path)]));

    for (const [domain, modulePath, pagePath] of cssDomains) {
      for (const className of new Set(moduleClasses(modulePath))) {
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
});
