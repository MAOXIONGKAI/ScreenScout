export function formatDuration(minutes: number): string {
  if (!minutes || minutes <= 0) return "N/A";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}min`;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return "N/A";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export const MAX_ACTIVE_SUBSCRIPTIONS = 10;

export function canAddActiveSubscription(currentActiveCount: number): boolean {
  return currentActiveCount < MAX_ACTIVE_SUBSCRIPTIONS;
}
