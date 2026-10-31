// Date/time helpers. Every instant from the API is an ISO string in UTC; display happens in the
// visitor's chosen timezone, with "Anywhere on Earth" (UTC−12) alongside for CS deadlines.

const AOE_OFFSET_MS = 12 * 60 * 60 * 1000;
const formatters = new Map<string, Intl.DateTimeFormat>();

function formatter(timeZone: string, options: Intl.DateTimeFormatOptions) {
  const key = timeZone + JSON.stringify(options);
  let f = formatters.get(key);
  if (!f) {
    try {
      f = new Intl.DateTimeFormat("en-US", { timeZone, ...options });
    } catch {
      f = new Intl.DateTimeFormat("en-US", { timeZone: "UTC", ...options });
    }
    formatters.set(key, f);
  }
  return f;
}

export const browserTimeZone = (() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
})();

const DATE: Intl.DateTimeFormatOptions = { month: "short", day: "numeric", year: "numeric" };
const DATE_SHORT: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
const TIME: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit", hourCycle: "h23" };

/** "Nov 15, 2026" in the given zone. Plain dates ("2026-11-15") are rendered as calendar dates. */
export function formatDate(iso: string | null | undefined, timeZone = "UTC", short = false) {
  if (!iso) return "—";
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) return formatter("UTC", short ? DATE_SHORT : DATE).format(new Date(`${iso}T12:00:00Z`));
  return formatter(timeZone, short ? DATE_SHORT : DATE).format(new Date(iso));
}

/** "Nov 15, 2026, 23:59" in the given zone. */
export function formatDateTime(iso: string | null | undefined, timeZone = "UTC") {
  if (!iso) return "—";
  return formatter(timeZone, { ...DATE, ...TIME }).format(new Date(iso));
}

export function formatTime(iso: string, timeZone = "UTC") {
  return formatter(timeZone, TIME).format(new Date(iso));
}

/** The same instant expressed in Anywhere-on-Earth time, e.g. "Nov 14, 2026, 23:59 AoE". */
export function formatAoE(iso: string | null | undefined) {
  if (!iso) return "—";
  const shifted = new Date(new Date(iso).getTime() - AOE_OFFSET_MS);
  return `${formatter("UTC", { ...DATE, ...TIME }).format(shifted)} AoE`;
}

export function formatDateRange(start: string | null, end: string | null) {
  if (!start) return "—";
  if (!end || end === start) return formatDate(start);
  const a = new Date(`${start}T12:00:00Z`);
  const b = new Date(`${end}T12:00:00Z`);
  const sameYear = a.getUTCFullYear() === b.getUTCFullYear();
  const sameMonth = sameYear && a.getUTCMonth() === b.getUTCMonth();
  if (sameMonth) return `${formatter("UTC", { month: "short" }).format(a)} ${a.getUTCDate()}–${b.getUTCDate()}, ${b.getUTCFullYear()}`;
  if (sameYear) return `${formatDate(start, "UTC", true)} – ${formatDate(end, "UTC", true)}, ${b.getUTCFullYear()}`;
  return `${formatDate(start)} – ${formatDate(end)}`;
}

/** Short zone label, e.g. "GMT+1" or "PST", for the given zone at the given instant. */
export function zoneLabel(timeZone: string, at = new Date()) {
  try {
    const part = formatter(timeZone, { timeZoneName: "short" })
      .formatToParts(at)
      .find((p) => p.type === "timeZoneName");
    return part?.value ?? timeZone;
  } catch {
    return timeZone;
  }
}

export interface CountdownParts {
  total: number;
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  done: boolean;
}

export function countdown(targetIso: string, now = Date.now()): CountdownParts {
  const total = new Date(targetIso).getTime() - now;
  if (total <= 0) return { total: 0, days: 0, hours: 0, minutes: 0, seconds: 0, done: true };
  const s = Math.floor(total / 1000);
  return {
    total,
    days: Math.floor(s / 86400),
    hours: Math.floor((s % 86400) / 3600),
    minutes: Math.floor((s % 3600) / 60),
    seconds: s % 60,
    done: false,
  };
}

export type Urgency = "closed" | "critical" | "soon" | "normal";

export function urgency(targetIso: string | null | undefined, now = Date.now()): Urgency {
  if (!targetIso) return "normal";
  const ms = new Date(targetIso).getTime() - now;
  if (ms <= 0) return "closed";
  if (ms < 3 * 86400_000) return "critical";
  if (ms < 14 * 86400_000) return "soon";
  return "normal";
}

export function daysUntil(iso: string, now = Date.now()) {
  return Math.ceil((new Date(iso).getTime() - now) / 86400_000);
}

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

export function relativeTime(iso: string, now = Date.now()) {
  const diff = new Date(iso).getTime() - now;
  const abs = Math.abs(diff);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["year", 365 * 86400_000],
    ["month", 30 * 86400_000],
    ["week", 7 * 86400_000],
    ["day", 86400_000],
    ["hour", 3600_000],
    ["minute", 60_000],
  ];
  for (const [unit, ms] of units) {
    if (abs >= ms) return rtf.format(Math.round(diff / ms), unit);
  }
  return "just now";
}

const pad = (n: number) => String(n).padStart(2, "0");

export function compactCountdown(parts: CountdownParts) {
  if (parts.done) return "Closed";
  if (parts.days > 0) return `${parts.days}d ${pad(parts.hours)}h ${pad(parts.minutes)}m`;
  return `${pad(parts.hours)}h ${pad(parts.minutes)}m ${pad(parts.seconds)}s`;
}

export { pad };
