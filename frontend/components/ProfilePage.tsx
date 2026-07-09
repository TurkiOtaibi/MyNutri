"use client";

import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getProfile, previewProfile, saveProfile } from "@/lib/api";
import { cacheProfile, getCachedProfile, queueMutation } from "@/lib/db";
import { activityLabels, goalLabels, sexLabels } from "@/lib/labels";
import type { ActivityLevel, Goal, ProfileInput, ProfileResponse, Sex, TargetResponse } from "@/lib/types";

import { TargetStrip } from "./TargetStrip";

const defaultProfile: ProfileInput = {
  sex: "male",
  birth_date: "1995-01-01",
  height_cm: 175,
  weight_kg: 80,
  activity_level: "moderate",
  goal: "cut",
  protein_per_kg: 1.8,
  fat_pct: 0.25
};

export function ProfilePage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ProfileInput>(defaultProfile);
  const [preview, setPreview] = useState<TargetResponse | null>(null);
  const [note, setNote] = useState("");

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

  useEffect(() => {
    if (profileQuery.data) {
      const { id, updated_at, targets, ...input } = profileQuery.data;
      setForm(input);
      setPreview(targets);
    }
  }, [profileQuery.data]);

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      try {
        setPreview(await previewProfile(form));
      } catch {
        setPreview(profileQuery.data?.targets ?? null);
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [form, profileQuery.data?.targets]);

  const mutation = useMutation({
    mutationFn: saveProfile,
    onSuccess: async (profile: ProfileResponse) => {
      await cacheProfile(profile);
      queryClient.setQueryData(["profile"], profile);
      setPreview(profile.targets);
      setNote("تم حفظ الملف.");
    },
    onError: async () => {
      await queueMutation({ method: "PUT", path: "/profile", body: form });
      setNote("تم حفظ التعديل محليًا وسيزامن عند الاتصال.");
    }
  });

  function update<K extends keyof ProfileInput>(key: K, value: ProfileInput[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1 className="page-title">الملف والأهداف</h1>
          <p className="page-kicker">الأهداف محسوبة من الخادم بمحرك Mifflin-St Jeor.</p>
        </div>
      </div>

      <div className="workspace-grid">
        <section className="form-panel">
          <h2 className="panel-title">بيانات الجسم</h2>
          <div className="form-grid">
            <label className="field">
              <span>الجنس</span>
              <select className="select" value={form.sex} onChange={(event) => update("sex", event.target.value as Sex)}>
                {Object.entries(sexLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>تاريخ الميلاد</span>
              <input
                className="input"
                type="date"
                value={form.birth_date}
                onChange={(event) => update("birth_date", event.target.value)}
              />
            </label>

            <label className="field">
              <span>الطول</span>
              <input
                className="input"
                type="number"
                min="1"
                value={form.height_cm}
                onChange={(event) => update("height_cm", Number(event.target.value))}
              />
            </label>

            <label className="field">
              <span>الوزن</span>
              <input
                className="input"
                type="number"
                min="1"
                step="0.1"
                value={form.weight_kg}
                onChange={(event) => update("weight_kg", Number(event.target.value))}
              />
            </label>

            <label className="field">
              <span>النشاط</span>
              <select
                className="select"
                value={form.activity_level}
                onChange={(event) => update("activity_level", event.target.value as ActivityLevel)}
              >
                {Object.entries(activityLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span>الهدف</span>
              <select className="select" value={form.goal} onChange={(event) => update("goal", event.target.value as Goal)}>
                {Object.entries(goalLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <details className="details-block">
            <summary>خيارات متقدمة</summary>
            <div className="form-grid" style={{ marginTop: 12 }}>
              <label className="field">
                <span>بروتين لكل كجم</span>
                <input
                  className="input"
                  type="number"
                  min="1.6"
                  max="2.2"
                  step="0.1"
                  value={form.protein_per_kg}
                  onChange={(event) => update("protein_per_kg", Number(event.target.value))}
                />
              </label>
              <label className="field">
                <span>نسبة الدهون</span>
                <input
                  className="input"
                  type="number"
                  min="0.2"
                  max="0.3"
                  step="0.01"
                  value={form.fat_pct}
                  onChange={(event) => update("fat_pct", Number(event.target.value))}
                />
              </label>
            </div>
          </details>

          <div className="actions">
            <button className="btn primary" type="button" onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
              <Save size={18} />
              حفظ
            </button>
            {note ? <span className="row-subtitle">{note}</span> : null}
          </div>
        </section>

        <section className="section-panel">
          <h2 className="panel-title">الأهداف اليومية</h2>
          <TargetStrip targets={preview} />
          {preview?.carb_clamped ? <p className="state-note">تم تصفير الكارب لأن السعرات لا تكفي بعد البروتين والدهون.</p> : null}
        </section>
      </div>
    </>
  );
}
