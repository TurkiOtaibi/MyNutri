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
  return new Intl.DateTimeFormat("ar-SA", {
    month: "short",
    day: "numeric"
  }).format(new Date(`${input}T00:00:00`));
}
