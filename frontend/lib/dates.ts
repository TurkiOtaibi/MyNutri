export function todayInputValue(): string {
  return toInputValue(new Date());
}

export function toInputValue(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

export function addDays(input: string, days: number): string {
  const date = new Date(`${input}T00:00:00`);
  date.setDate(date.getDate() + days);
  return toInputValue(date);
}

export function weekStartSunday(input: string): string {
  const date = new Date(`${input}T00:00:00`);
  date.setDate(date.getDate() - date.getDay());
  return toInputValue(date);
}

export function formatShortDate(input: string): string {
  const { day, month } = parseGregorianDate(input);
  return `${day} ${gregorianMonths[month - 1]}`;
}

export function formatLongArabicDate(input: string): string {
  const { year, month, day, weekday } = parseGregorianDate(input);
  return `${gregorianWeekdays[weekday]}، ${day} ${gregorianMonths[month - 1]} ${year}`;
}

export function formatDayNumber(input: string): string {
  return String(parseGregorianDate(input).day);
}

const gregorianMonths = [
  "يناير",
  "فبراير",
  "مارس",
  "أبريل",
  "مايو",
  "يونيو",
  "يوليو",
  "أغسطس",
  "سبتمبر",
  "أكتوبر",
  "نوفمبر",
  "ديسمبر"
];

const gregorianWeekdays = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];

function parseGregorianDate(input: string): { year: number; month: number; day: number; weekday: number } {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(input);
  if (!match) throw new Error(`Invalid ISO date: ${input}`);
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
  return { year, month, day, weekday };
}
