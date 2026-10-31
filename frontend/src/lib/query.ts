import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./api";
import { boot, bootLocation } from "./boot";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      gcTime: 10 * 60_000,
      refetchOnWindowFocus: false,
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
    },
    mutations: { retry: false },
  },
});

/** Query keys in one place so mutations can invalidate precisely. */
export const keys = {
  session: ["session"] as const,
  facets: ["facets"] as const,
  home: ["home"] as const,
  explore: (view: string, qs: string) => ["explore", view, qs] as const,
  venue: (slug: string) => ["venue", slug] as const,
  targets: ["targets"] as const,
  compare: (slugs: string[]) => ["compare", ...slugs] as const,
  recommend: (qs: string) => ["recommend", qs] as const,
  plan: (qs: string) => ["plan", qs] as const,
  insights: ["insights"] as const,
  radar: ["radar"] as const,
  dashboard: ["dashboard"] as const,
  profile: ["profile"] as const,
  notifications: ["notifications"] as const,
  lists: ["lists"] as const,
  list: (slug: string) => ["list", slug] as const,
  searches: ["searches"] as const,
  board: ["board"] as const,
  submission: (id: number) => ["submission", id] as const,
  papers: ["papers"] as const,
  venueOptions: ["venue-options"] as const,
  apiMeta: ["api-meta"] as const,
  timezones: ["timezones"] as const,
};

/** Canonical query string for explore keys: sorted, without empty values. */
export function canonicalQuery(search: URLSearchParams | string) {
  const params = new URLSearchParams(search);
  const entries = [...params.entries()].filter(([, v]) => v !== "");
  entries.sort(([a, av], [b, bv]) => (a === b ? av.localeCompare(bv) : a.localeCompare(b)));
  return new URLSearchParams(entries).toString();
}

export function exploreKey(search: URLSearchParams | string) {
  const params = new URLSearchParams(search);
  const view = params.get("view") || "grid";
  params.delete("view");
  return keys.explore(view === "table" || view === "timeline" || view === "calendar" ? view : "grid", canonicalQuery(params));
}

/** Seed the cache with the data the Django shell rendered for this URL, so the first paint needs no fetch. */
export function seedInitialData() {
  const { initial, session } = boot;
  queryClient.setQueryData(keys.session, session);
  if (initial.facets) queryClient.setQueryData(keys.facets, initial.facets);
  if (initial.home) queryClient.setQueryData(keys.home, initial.home);
  if (initial.explore) {
    const url = new URL(bootLocation, window.location.origin);
    queryClient.setQueryData(exploreKey(url.searchParams), initial.explore);
  }
  if (initial.venue) queryClient.setQueryData(keys.venue(initial.venue.slug), initial.venue);
  if (initial.list) {
    const list = initial.list as { list: { slug: string } };
    queryClient.setQueryData(keys.list(list.list.slug), initial.list);
  }
}
