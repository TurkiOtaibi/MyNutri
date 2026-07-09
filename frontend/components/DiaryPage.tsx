"use client";

import { ChevronLeft, ChevronRight, Plus, Trash2 } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createDiaryEntry, deleteDiaryEntry, getProfile, getWeekSummary, listDiaryEntries, listFoods } from "@/lib/api";
import { addDays, formatShortDate, todayInputValue, weekStartSunday } from "@/lib/dates";
import {
  addLocalDiaryEntry,
  buildOfflineWeek,
  cacheDiaryEntries,
  cacheFoods,
  cacheProfile,
  getCachedEntriesByDate,
  getCachedFoods,
  getCachedProfile,
  getDb,
  queueMutation
} from "@/lib/db";
import { weekdays } from "@/lib/labels";
import type { DiaryEntryInput, FoodResponse, ProfileResponse, TargetResponse, WeekSummary } from "@/lib/types";

import { MetricTile } from "./MetricTile";
import { ProgressBar } from "./ProgressBar";
import { TargetStrip } from "./TargetStrip";

export function DiaryPage() {
  const queryClient = useQueryClient();
  const [selectedDate, setSelectedDate] = useState(todayInputValue());
  const [foodId, setFoodId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [note, setNote] = useState("");
  const weekStart = useMemo(() => weekStartSunday(selectedDate), [selectedDate]);

  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      try {
        const profile = await getProfile();
        await cacheProfile(profile);
        return profile;
      } catch {
        return getCachedProfile();
      }
    }
  });

  const foodsQuery = useQuery({
    queryKey: ["foods"],
    queryFn: async () => {
      try {
        const foods = await listFoods();
        await cacheFoods(foods);
        return foods;
      } catch {
        return getCachedFoods();
      }
    }
  });

  const weekQuery = useQuery({
    queryKey: ["week", weekStart, profileQuery.data?.id],
    queryFn: async () => {
      try {
        return await getWeekSummary(weekStart);
      } catch {
        return buildOfflineWeek(weekStart, profileQuery.data?.targets ?? null);
      }
    }
  });

  const entriesQuery = useQuery({
    queryKey: ["entries", selectedDate],
    queryFn: async () => {
      try {
        const entries = await listDiaryEntries(selectedDate);
        await cacheDiaryEntries(entries);
        return entries;
      } catch {
        return getCachedEntriesByDate(selectedDate);
      }
    }
  });

  const profile = profileQuery.data as ProfileResponse | null | undefined;
  const targets = profile?.targets ?? weekQuery.data?.targets ?? null;
  const foods = foodsQuery.data ?? [];
  const entries = entriesQuery.data ?? [];
  const selectedFood = foods.find((food) => food.id === foodId) ?? foods[0];
  const selectedDay = weekQuery.data?.days.find((day) => day.date === selectedDate);

  const addMutation = useMutation({
    mutationFn: async (payload: DiaryEntryInput) => createDiaryEntry(payload),
    onSuccess: async (entry) => {
      await cacheDiaryEntries([entry]);
      setQuantity(1);
      setNote("تم تسجيل الوجبة.");
      await invalidateDiary(queryClient);
    },
    onError: async (_error, payload) => {
      const food = foods.find((item) => item.id === payload.food_id);
      if (!food) return;
      await addLocalDiaryEntry(payload, food);
      setQuantity(1);
      setNote("تم تسجيل الوجبة محليًا وسيتم رفعها عند الاتصال.");
      await invalidateDiary(queryClient);
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDiaryEntry,
    onSuccess: async (_result, entryId) => {
      await getDb().diaryEntries.delete(entryId);
      setNote("تم حذف السجل.");
      await invalidateDiary(queryClient);
    },
    onError: async (_error, entryId) => {
      await getDb().diaryEntries.delete(entryId);
      await queueMutation({ method: "DELETE", path: `/diary/${entryId}` });
      setNote("تم حذف السجل محليًا وسيزامن عند الاتصال.");
      await invalidateDiary(queryClient);
    }
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const chosenFood = foods.find((food) => food.id === foodId) ?? selectedFood;
    if (!chosenFood) {
      setNote("أضف طعامًا أولًا.");
      return;
    }
    addMutation.mutate({
      entry_date: selectedDate,
      food_id: chosenFood.id,
      quantity
    });
  }

  function moveWeek(days: number) {
    setSelectedDate(addDays(selectedDate, days));
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">اليوميات</h1>
          <p className="page-kicker">الأسبوع يبدأ من الأحد، والتجميع اليومي يحسب من السجلات لا من كيان أسبوع مستقل.</p>
        </div>
        <div className="actions" style={{ marginTop: 0 }}>
          <button className="btn icon" type="button" title="الأسبوع السابق" onClick={() => moveWeek(-7)}>
            <ChevronRight size={18} />
          </button>
          <input className="input" type="date" value={selectedDate} onChange={(event) => setSelectedDate(event.target.value)} />
          <button className="btn icon" type="button" title="الأسبوع التالي" onClick={() => moveWeek(7)}>
            <ChevronLeft size={18} />
          </button>
        </div>
      </div>

      <section className="section-panel" style={{ marginBottom: 18 }}>
        <h2 className="panel-title">أهداف اليوم</h2>
        <TargetStrip targets={targets} />
      </section>

      <section className="section-panel" style={{ marginBottom: 18 }}>
        <h2 className="panel-title">
          الأسبوع
          <span className="row-subtitle">{weekQuery.data ? `${formatShortDate(weekQuery.data.start)} - ${formatShortDate(weekQuery.data.end)}` : ""}</span>
        </h2>
        <WeekGrid
          week={weekQuery.data}
          selectedDate={selectedDate}
          targets={targets}
          onSelect={(date) => setSelectedDate(date)}
        />
      </section>

      <div className="workspace-grid">
        <section className="section-panel">
          <h2 className="panel-title">
            {formatShortDate(selectedDate)}
            <span className="row-subtitle">{entries.length} سجل</span>
          </h2>

          <div className="target-strip" style={{ marginBottom: 14 }}>
            <MetricTile label="المستهلك" value={Math.round(selectedDay?.totals.calories ?? 0)} unit="كيلو كالوري" />
            <MetricTile
              label="المتبقي"
              value={targets ? Math.round(targets.target_calories - (selectedDay?.totals.calories ?? 0)) : "-"}
              unit="كيلو كالوري"
            />
            <MetricTile label="بروتين" value={selectedDay?.totals.protein_g ?? 0} unit="غرام" />
            <MetricTile label="كارب" value={selectedDay?.totals.carb_g ?? 0} unit="غرام" />
          </div>

          {targets ? (
            <div className="details-block" style={{ marginBottom: 14 }}>
              <MacroProgress label="السعرات" value={selectedDay?.totals.calories ?? 0} max={targets.target_calories} unit="كالوري" />
              <MacroProgress label="البروتين" value={selectedDay?.totals.protein_g ?? 0} max={targets.protein_g} unit="g" />
              <MacroProgress label="الكارب" value={selectedDay?.totals.carb_g ?? 0} max={targets.carb_g} unit="g" />
              <MacroProgress label="الدهون" value={selectedDay?.totals.fat_g ?? 0} max={targets.fat_g} unit="g" />
            </div>
          ) : null}

          <div className="entry-list">
            {entries.map((entry) => (
              <article className="entry-row" key={entry.id}>
                <div>
                  <div className="row-title">{entry.nutrition_snapshot.name}</div>
                  <div className="row-subtitle">
                    {entry.quantity} × {entry.nutrition_snapshot.serving_label} · {entry.totals.calories} كالوري
                  </div>
                  <div className="row-subtitle">
                    بروتين {entry.totals.protein_g}g · كارب {entry.totals.carb_g}g · دهون {entry.totals.fat_g}g
                  </div>
                </div>
                <button className="btn icon danger" type="button" title="حذف" onClick={() => deleteMutation.mutate(entry.id)}>
                  <Trash2 size={17} />
                </button>
              </article>
            ))}
            {entries.length === 0 ? <div className="state-note">لا توجد وجبات مسجلة لهذا اليوم.</div> : null}
          </div>
        </section>

        <form className="form-panel" onSubmit={submit}>
          <h2 className="panel-title">إضافة وجبة</h2>
          <div className="form-grid">
            <label className="field">
              <span>الطعام</span>
              <select className="select" value={foodId} onChange={(event) => setFoodId(event.target.value)}>
                {foods.map((food) => (
                  <option key={food.id} value={food.id}>
                    {food.name} - {food.serving_label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>الكمية بالحصة</span>
              <input
                className="input"
                type="number"
                min="0.01"
                step="0.01"
                value={quantity}
                onChange={(event) => setQuantity(Number(event.target.value))}
              />
            </label>
          </div>
          <div className="actions">
            <button className="btn primary" type="submit" disabled={addMutation.isPending || foods.length === 0}>
              <Plus size={18} />
              تسجيل
            </button>
            {note ? <span className="row-subtitle">{note}</span> : null}
          </div>
          {foods.length === 0 ? <p className="state-note">أضف عناصر في صفحة الأطعمة قبل تسجيل اليوميات.</p> : null}
        </form>
      </div>
    </>
  );
}

function WeekGrid({
  week,
  selectedDate,
  targets,
  onSelect
}: {
  week: WeekSummary | undefined;
  selectedDate: string;
  targets: TargetResponse | null;
  onSelect: (date: string) => void;
}) {
  if (!week) {
    return <div className="state-note">جاري تحميل الأسبوع.</div>;
  }

  return (
    <div className="week-grid">
      {week.days.map((day, index) => {
        const target = targets?.target_calories ?? 0;
        return (
          <button
            className={`day-button ${day.date === selectedDate ? "selected" : ""}`}
            key={day.date}
            type="button"
            onClick={() => onSelect(day.date)}
          >
            <span className="day-name">{weekdays[index]}</span>
            <span className="day-date">{formatShortDate(day.date)}</span>
            <span className="row-subtitle">{Math.round(day.totals.calories)} كالوري</span>
            <ProgressBar value={day.totals.calories} max={target} />
          </button>
        );
      })}
    </div>
  );
}

function MacroProgress({ label, value, max, unit }: { label: string; value: number; max: number; unit: string }) {
  return (
    <div className="field" style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <span className="label">{label}</span>
        <span className="row-subtitle">
          {Number(value.toFixed(1))} / {Number(max.toFixed(1))} {unit}
        </span>
      </div>
      <ProgressBar value={value} max={max} />
    </div>
  );
}

async function invalidateDiary(queryClient: ReturnType<typeof useQueryClient>) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ["entries"] }),
    queryClient.invalidateQueries({ queryKey: ["week"] })
  ]);
}
