import { expect, test as base, type APIRequestContext, type Page } from "@playwright/test";

export const API_URL = process.env.PLAYWRIGHT_API_URL ?? "http://127.0.0.1:8000";
export const API_TOKEN = process.env.PLAYWRIGHT_API_TOKEN ?? "dev-token";

const apiHost = new URL(API_URL).hostname;
if (apiHost !== "127.0.0.1" && apiHost !== "localhost") {
  throw new Error(`Foods test helper refuses non-local API target ${API_URL}`);
}

export type FoodPayload = {
  name: string;
  brand: string | null;
  category: string | null;
  primary_category_key: string | null;
  food_kind: "simple" | "composite" | "unknown";
  group_data_status: "known" | "estimated" | "unknown";
  group_data_completeness: "complete" | "partial" | "unknown";
  nutrition_basis: "per_100g" | "per_100ml";
  default_unit_type: "g" | "ml" | "cup" | "slice" | "piece" | "scoop" | "serving" | "tablespoon" | "teaspoon";
  unit_amount: number;
  unit_basis: "g" | "ml";
  calories: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  fiber_g: number | null;
  sugar_g: number | null;
  added_sugar_g: number | null;
  saturated_fat_g: number | null;
  trans_fat_g: number | null;
  sodium_mg: number | null;
  cholesterol_mg: number | null;
  potassium_mg: number | null;
  calcium_mg: number | null;
  iron_mg: number | null;
  magnesium_mg: number | null;
  zinc_mg: number | null;
  selenium_mcg: number | null;
  vitamin_d_mcg: number | null;
  vitamin_b12_mcg: number | null;
  vitamin_c_mg: number | null;
  vitamin_a_mcg: number | null;
  vitamin_a_rae_mcg: number | null;
  folate_mcg: number | null;
  folate_dfe_mcg: number | null;
  vitamin_k_mcg: number | null;
  iodine_mcg: number | null;
  notes: string | null;
  data_source: string | null;
  nutrition_source: { type: string; name: string | null; reference: string | null };
  ingredients: { text: string | null; source_type: string | null; source_name: string | null; source_reference: string | null };
  nova: { classification: "1" | "2" | "3" | "4" | "unknown" } | null;
  group_contributions: Array<{ group_key: string; subtype_key?: string | null; amount_per_100_basis: number; data_status: "known" | "estimated" }>;
  analytical_traits: string[];
};

export type FoodRecord = Omit<FoodPayload, "nutrition_source" | "nova" | "group_contributions"> & {
  id: string;
  net_carbs_g: number;
  created_at: string;
  updated_at: string;
  nutrition_source: FoodPayload["nutrition_source"] & { reliability: string; reliability_rules_version: string };
  nova: { classification: "1" | "2" | "3" | "4" | "unknown"; review_status: "unreviewed" | "reviewed"; rules_version: string };
  group_contributions: Array<FoodPayload["group_contributions"][number] & { food_group_rules_version: string }>;
};

export function uniqueName(label = "Food"): string {
  return `E2E-${label}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function validFood(overrides: Partial<FoodPayload> = {}): FoodPayload {
  return {
    name: uniqueName("Food"),
    brand: "E2E Brand",
    category: "E2E Category",
    primary_category_key: "other",
    food_kind: "simple",
    group_data_status: "unknown",
    group_data_completeness: "unknown",
    nutrition_basis: "per_100g",
    default_unit_type: "serving",
    unit_amount: 100,
    unit_basis: "g",
    calories: 180,
    protein_g: 10,
    carb_g: 20,
    fat_g: 6,
    fiber_g: null,
    sugar_g: null,
    added_sugar_g: null,
    saturated_fat_g: null,
    trans_fat_g: null,
    sodium_mg: null,
    cholesterol_mg: null,
    potassium_mg: null,
    calcium_mg: null,
    iron_mg: null,
    magnesium_mg: null,
    zinc_mg: null,
    selenium_mcg: null,
    vitamin_d_mcg: null,
    vitamin_b12_mcg: null,
    vitamin_c_mg: null,
    vitamin_a_mcg: null,
    vitamin_a_rae_mcg: null,
    folate_mcg: null,
    folate_dfe_mcg: null,
    vitamin_k_mcg: null,
    iodine_mcg: null,
    notes: null,
    data_source: null,
    nutrition_source: { type: "unknown", name: null, reference: null },
    ingredients: { text: null, source_type: null, source_name: null, source_reference: null },
    nova: null,
    group_contributions: [],
    analytical_traits: [],
    ...overrides
  };
}

export class FoodsApi {
  private readonly foodIds = new Set<string>();
  private readonly diaryIds = new Set<string>();

  constructor(private readonly request: APIRequestContext) {}

  private headers() {
    return { Authorization: `Bearer ${API_TOKEN}` };
  }

  async create(payload: Partial<FoodPayload> = {}): Promise<FoodRecord> {
    const response = await this.request.post(`${API_URL}/foods`, {
      headers: this.headers(),
      data: validFood(payload)
    });
    expect(response.status(), await response.text()).toBe(201);
    const food = (await response.json()) as FoodRecord;
    this.foodIds.add(food.id);
    return food;
  }

  async createRaw(payload: unknown) {
    return this.request.post(`${API_URL}/foods`, { headers: this.headers(), data: payload });
  }

  async update(id: string, payload: Partial<FoodPayload>) {
    return this.request.put(`${API_URL}/foods/${id}`, { headers: this.headers(), data: payload });
  }

  async list(query = ""): Promise<FoodRecord[]> {
    const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
    const response = await this.request.get(`${API_URL}/foods${suffix}`, { headers: this.headers() });
    expect(response.status()).toBe(200);
    return response.json() as Promise<FoodRecord[]>;
  }

  async get(id: string): Promise<FoodRecord> {
    const response = await this.request.get(`${API_URL}/foods/${id}`, { headers: this.headers() });
    expect(response.status()).toBe(200);
    return response.json() as Promise<FoodRecord>;
  }

  async remove(id: string): Promise<void> {
    const response = await this.request.delete(`${API_URL}/foods/${id}`, { headers: this.headers() });
    expect([204, 404]).toContain(response.status());
    this.foodIds.delete(id);
  }

  async createDiary(foodId: string, entryDate: string, quantity = 1, mealType = "breakfast") {
    const response = await this.request.post(`${API_URL}/diary`, {
      headers: this.headers(),
      data: { food_id: foodId, entry_date: entryDate, quantity, meal_type: mealType }
    });
    expect(response.status(), await response.text()).toBe(201);
    const entry = (await response.json()) as { id: string; nutrition_snapshot: { name: string }; totals: { calories: number } };
    this.diaryIds.add(entry.id);
    return entry;
  }

  async listDiary(entryDate: string) {
    const response = await this.request.get(`${API_URL}/diary?entry_date=${entryDate}`, { headers: this.headers() });
    expect(response.status()).toBe(200);
    return response.json() as Promise<Array<{ id: string; nutrition_snapshot: { name: string }; totals: { calories: number } }>>;
  }

  async cleanup(): Promise<void> {
    const diaryResponse = await this.request.get(`${API_URL}/diary`, { headers: this.headers() });
    if (diaryResponse.ok()) {
      const entries = (await diaryResponse.json()) as Array<{ id: string; nutrition_snapshot?: { name?: string } }>;
      for (const entry of entries) {
        if (entry.nutrition_snapshot?.name?.startsWith("E2E-")) {
          await this.request.delete(`${API_URL}/diary/${entry.id}`, { headers: this.headers() });
        }
      }
    }
    for (const id of this.diaryIds) {
      await this.request.delete(`${API_URL}/diary/${id}`, { headers: this.headers() });
    }
    for (const id of this.foodIds) {
      await this.request.delete(`${API_URL}/foods/${id}`, { headers: this.headers() });
    }
    this.diaryIds.clear();
    this.foodIds.clear();
  }
}

type Fixtures = { foodsApi: FoodsApi };

export const test = base.extend<Fixtures>({
  foodsApi: async ({ request }, use) => {
    const api = new FoodsApi(request);
    await use(api);
    await api.cleanup();
  }
});

export { expect };

async function waitForReactForm(page: Page): Promise<void> {
  await page.locator("form").waitFor({ state: "attached" });
  await page.waitForFunction(() => {
    const form = document.querySelector("form");
    return form != null && Object.keys(form).some((key) => key.startsWith("__reactProps$"));
  });
}

export async function fillRequiredFoodForm(page: Page, payload: Partial<FoodPayload> = {}): Promise<FoodPayload> {
  await waitForReactForm(page);
  const food = validFood(payload);
  await page.getByLabel(/اسم الطعام/).fill(food.name);
  if (food.brand != null) await page.getByLabel("العلامة التجارية").fill(food.brand);
  if (food.category != null) await page.getByLabel("الفئة القديمة (للتوافق)").fill(food.category);
  await page.getByLabel(/التصنيف الأساسي/).selectOption(food.primary_category_key ?? "other");
  await page.getByLabel(/نوع الطعام/).selectOption(food.food_kind);
  await page.getByLabel(/أساس القيم/).selectOption(food.nutrition_basis);
  await page.getByLabel(/السعرات/).fill(String(food.calories));
  await page.getByLabel(/البروتين g/).fill(String(food.protein_g));
  await page.getByLabel(/الكارب g/).fill(String(food.carb_g));
  await page.getByLabel(/الدهون g/).fill(String(food.fat_g));
  await page.getByLabel(/الوحدة الافتراضية/).selectOption(food.default_unit_type);
  await page.getByLabel(/مقدار الوحدة/).fill(String(food.unit_amount));
  await page.getByLabel(/أساس الوحدة/).selectOption(food.unit_basis);
  return food;
}

export async function submitFoodForm(page: Page, mode: "create" | "edit" = "create") {
  await waitForReactForm(page);
  await page.getByRole("button", { name: mode === "create" ? "حفظ الطعام" : "حفظ التعديل" }).click();
}

export function field(page: Page, label: string | RegExp) {
  return page.getByLabel(label);
}

export async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({ width: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.width + 1);
}
