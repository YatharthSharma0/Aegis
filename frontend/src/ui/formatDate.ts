/** Compact absolute timestamp, e.g. "4 Sep 2026, 14:03". Locale-stable
 * (en-GB) so evidence timestamps read the same for every investigator. */
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
