// URL search params are the single source of truth for Explore filters, so every view is shareable.

export const FILTER_KEYS = [
  "q",
  "type",
  "domain",
  "tag",
  "core",
  "ccf",
  "quartile",
  "min_if",
  "country",
  "continent",
  "review",
  "oa",
  "status",
  "within",
] as const;
export const VIEW_KEYS = ["view", "sort", "dir", "page"] as const;
export type View = "grid" | "table" | "timeline" | "calendar";

export function currentView(params: URLSearchParams): View {
  const v = params.get("view");
  return v === "table" || v === "timeline" || v === "calendar" ? v : "grid";
}

export function activeFilterCount(params: URLSearchParams) {
  return FILTER_KEYS.reduce((n, key) => n + params.getAll(key).filter(Boolean).length, 0);
}

/** Copy params, apply a mutation, reset pagination. */
export function edit(params: URLSearchParams, fn: (p: URLSearchParams) => void) {
  const next = new URLSearchParams(params);
  fn(next);
  next.delete("page");
  return next;
}

export function toggleValue(params: URLSearchParams, key: string, value: string) {
  return edit(params, (p) => {
    const values = p.getAll(key);
    p.delete(key);
    const set = values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
    set.forEach((v) => p.append(key, v));
  });
}

export function setValue(params: URLSearchParams, key: string, value: string | null) {
  return edit(params, (p) => {
    if (value === null || value === "") p.delete(key);
    else p.set(key, value);
  });
}

export function removeChip(params: URLSearchParams, name: string, value: string) {
  return edit(params, (p) => {
    const values = p.getAll(name).filter((v) => v !== value);
    p.delete(name);
    values.forEach((v) => p.append(name, v));
  });
}

export function clearFilters(params: URLSearchParams) {
  const next = new URLSearchParams();
  for (const key of ["view", "sort", "dir"]) {
    const v = params.get(key);
    if (v) next.set(key, v);
  }
  return next;
}

/** Query string for exports/feeds: filters + sort, without view & page. */
export function exportQuery(params: URLSearchParams) {
  const next = new URLSearchParams(params);
  next.delete("view");
  next.delete("page");
  return next.toString();
}
