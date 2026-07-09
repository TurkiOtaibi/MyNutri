import type { ActivityLevel, Goal, Sex } from "./types";

export const sexLabels: Record<Sex, string> = {
  male: "ذكر",
  female: "أنثى"
};

export const activityLabels: Record<ActivityLevel, string> = {
  sedentary: "خامل",
  light: "نشاط خفيف",
  moderate: "نشاط متوسط",
  active: "نشط",
  very_active: "نشط جدًا"
};

export const goalLabels: Record<Goal, string> = {
  cut: "تنشيف",
  maintain: "ثبات",
  bulk: "زيادة"
};

export const weekdays = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
