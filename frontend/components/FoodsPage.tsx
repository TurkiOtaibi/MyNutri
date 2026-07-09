"use client";

import { Info, Pencil, Plus, Save, Search, Trash2, X } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createFood, deleteFood, listFoods, updateFood } from "@/lib/api";
import { cacheFoods, getCachedFoods, getDb, queueMutation } from "@/lib/db";
import type { FoodInput, FoodResponse } from "@/lib/types";

const emptyFood: FoodInput = {
  name: "",
  serving_label: "",
  serving_grams: null,
  calories: 0,
  protein_g: 0,
  carb_g: 0,
  fat_g: 0,
  saturated_fat_g: null,
  trans_fat_g: null,
  cholesterol_mg: null,
  sodium_mg: null,
  fiber_g: null,
  total_sugars_g: null,
  added_sugar_g: null
};

export function FoodsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState<FoodInput>(emptyFood);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [note, setNote] = useState("");

  const foodsQuery = useQuery({
    queryKey: ["foods", search],
    queryFn: async () => {
      try {
        const foods = await listFoods(search);
        await cacheFoods(foods);
        return foods;
      } catch {
        const cached = await getCachedFoods();
        return search.trim()
          ? cached.filter((food) => food.name.toLowerCase().includes(search.trim().toLowerCase()))
          : cached;
      }
    }
  });

  const foods = foodsQuery.data ?? [];

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingId) return updateFood(editingId, draft);
      return createFood(draft);
    },
    onSuccess: async () => {
      setDraft(emptyFood);
      setEditingId(null);
      setNote("تم حفظ الطعام.");
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
    },
    onError: async () => {
      const now = new Date().toISOString();
      if (editingId) {
        await getDb().foods.update(editingId, { ...draft, updated_at: now });
        await queueMutation({ method: "PUT", path: `/foods/${editingId}`, body: draft });
      } else {
        const localId = crypto.randomUUID();
        const localFood: FoodResponse = {
          ...draft,
          id: localId,
          net_carbs_g: Number((draft.carb_g - (draft.fiber_g ?? 0)).toFixed(2)),
          created_at: now,
          updated_at: now
        };
        await getDb().foods.put(localFood);
        await queueMutation({ method: "POST", path: "/foods", body: { ...draft, id: localId } });
      }
      setDraft(emptyFood);
      setEditingId(null);
      setNote("تم حفظ الطعام محليًا وسيزامن عند الاتصال.");
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteFood,
    onSuccess: async () => {
      setNote("تم حذف الطعام.");
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
    },
    onError: async (_error, foodId) => {
      await getDb().foods.delete(foodId);
      await queueMutation({ method: "DELETE", path: `/foods/${foodId}` });
      setNote("تم حذف الطعام محليًا وسيزامن عند الاتصال.");
      await queryClient.invalidateQueries({ queryKey: ["foods"] });
    }
  });

  const filteredFoods = useMemo(() => foods, [foods]);

  function update<K extends keyof FoodInput>(key: K, value: FoodInput[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function edit(food: FoodResponse) {
    const { id, net_carbs_g, created_at, updated_at, ...input } = food;
    setDraft(input);
    setEditingId(id);
    setNote("");
  }

  function resetForm() {
    setDraft(emptyFood);
    setEditingId(null);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    saveMutation.mutate();
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">الأطعمة</h1>
          <p className="page-kicker">كل القيم لكل حصة واحدة، وصافي الكارب يحسب تلقائيًا.</p>
        </div>
      </div>

      <div className="workspace-grid">
        <section className="section-panel">
          <h2 className="panel-title">
            القائمة
            <span className="row-subtitle">{filteredFoods.length} عنصر</span>
          </h2>

          <label className="field" style={{ marginBottom: 12 }}>
            <span>بحث</span>
            <span style={{ position: "relative" }}>
              <Search size={18} style={{ position: "absolute", insetInlineStart: 10, top: 12, color: "var(--muted)" }} />
              <input
                className="input"
                style={{ paddingInlineStart: 36 }}
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="اسم الطعام"
              />
            </span>
          </label>

          <div className="food-list">
            {filteredFoods.map((food) => (
              <article className="food-row" key={food.id}>
                <div>
                  <div className="row-title">{food.name}</div>
                  <div className="row-subtitle">
                    {food.serving_label} · {food.calories} كالوري · بروتين {food.protein_g}g · كارب {food.carb_g}g · دهون{" "}
                    {food.fat_g}g
                  </div>
                  <div className="row-subtitle">صافي الكارب {food.net_carbs_g}g</div>
                </div>
                <div className="row-actions">
                  <button
                    className="btn icon"
                    type="button"
                    title="تفاصيل"
                    onClick={() => setDetailId((current) => (current === food.id ? null : food.id))}
                  >
                    <Info size={17} />
                  </button>
                  <button className="btn icon" type="button" title="تعديل" onClick={() => edit(food)}>
                    <Pencil size={17} />
                  </button>
                  <button className="btn icon danger" type="button" title="حذف" onClick={() => deleteMutation.mutate(food.id)}>
                    <Trash2 size={17} />
                  </button>
                </div>
                {detailId === food.id ? <FoodDetails food={food} /> : null}
              </article>
            ))}
            {filteredFoods.length === 0 ? <div className="state-note">لا توجد أطعمة بعد.</div> : null}
          </div>
        </section>

        <form className="form-panel" onSubmit={submit}>
          <h2 className="panel-title">{editingId ? "تعديل طعام" : "إضافة طعام"}</h2>
          <div className="form-grid">
            <label className="field">
              <span>الاسم</span>
              <input className="input" value={draft.name} onChange={(event) => update("name", event.target.value)} required />
            </label>
            <label className="field">
              <span>الحصة</span>
              <input
                className="input"
                value={draft.serving_label}
                onChange={(event) => update("serving_label", event.target.value)}
                placeholder="15 g / حبة / طبق"
                required
              />
            </label>
            <NumberField label="غرام الحصة" value={draft.serving_grams} onChange={(value) => update("serving_grams", value)} />
            <NumberField label="السعرات" value={draft.calories} onChange={(value) => update("calories", value ?? 0)} required />
            <NumberField label="البروتين g" value={draft.protein_g} onChange={(value) => update("protein_g", value ?? 0)} required />
            <NumberField label="الكارب g" value={draft.carb_g} onChange={(value) => update("carb_g", value ?? 0)} required />
            <NumberField label="الدهون g" value={draft.fat_g} onChange={(value) => update("fat_g", value ?? 0)} required />
          </div>

          <details className="details-block">
            <summary>تفاصيل اختيارية</summary>
            <div className="form-grid" style={{ marginTop: 12 }}>
              <NumberField label="دهون مشبعة g" value={draft.saturated_fat_g} onChange={(value) => update("saturated_fat_g", value)} />
              <NumberField label="دهون متحولة g" value={draft.trans_fat_g} onChange={(value) => update("trans_fat_g", value)} />
              <NumberField label="كوليسترول mg" value={draft.cholesterol_mg} onChange={(value) => update("cholesterol_mg", value)} />
              <NumberField label="صوديوم mg" value={draft.sodium_mg} onChange={(value) => update("sodium_mg", value)} />
              <NumberField label="ألياف g" value={draft.fiber_g} onChange={(value) => update("fiber_g", value)} />
              <NumberField label="سكر كلي g" value={draft.total_sugars_g} onChange={(value) => update("total_sugars_g", value)} />
              <NumberField label="سكر مضاف g" value={draft.added_sugar_g} onChange={(value) => update("added_sugar_g", value)} />
            </div>
          </details>

          <div className="actions">
            <button className="btn primary" type="submit" disabled={saveMutation.isPending}>
              {editingId ? <Save size={18} /> : <Plus size={18} />}
              {editingId ? "حفظ" : "إضافة"}
            </button>
            {editingId ? (
              <button className="btn" type="button" onClick={resetForm}>
                <X size={18} />
                إلغاء
              </button>
            ) : null}
            {note ? <span className="row-subtitle">{note}</span> : null}
          </div>
        </form>
      </div>
    </>
  );
}

function FoodDetails({ food }: { food: FoodResponse }) {
  return (
    <div className="details-block" style={{ gridColumn: "1 / -1", marginTop: 0 }}>
      <div className="form-grid">
        <Detail label="غرام الحصة" value={food.serving_grams} unit="g" />
        <Detail label="ألياف" value={food.fiber_g} unit="g" />
        <Detail label="دهون مشبعة" value={food.saturated_fat_g} unit="g" />
        <Detail label="دهون متحولة" value={food.trans_fat_g} unit="g" />
        <Detail label="كوليسترول" value={food.cholesterol_mg} unit="mg" />
        <Detail label="صوديوم" value={food.sodium_mg} unit="mg" />
        <Detail label="سكر كلي" value={food.total_sugars_g} unit="g" />
        <Detail label="سكر مضاف" value={food.added_sugar_g} unit="g" />
      </div>
    </div>
  );
}

function Detail({ label, value, unit }: { label: string; value: number | null; unit: string }) {
  return (
    <div>
      <div className="metric-label">{label}</div>
      <div className="row-title">{value == null ? "-" : `${value} ${unit}`}</div>
    </div>
  );
}

function NumberField({
  label,
  value,
  onChange,
  required = false
}: {
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  required?: boolean;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        className="input"
        type="number"
        min="0"
        step="0.01"
        value={value ?? ""}
        required={required}
        onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
      />
    </label>
  );
}
