import { storage } from "./utils";

export interface RecentVenue {
  slug: string;
  acronym: string;
  name: string;
}

const KEY = "vp-recent";

export function recentVenues(): RecentVenue[] {
  return storage.get<RecentVenue[]>(KEY, []);
}

export function rememberVenue(v: RecentVenue) {
  const next = [v, ...recentVenues().filter((r) => r.slug !== v.slug)].slice(0, 8);
  storage.set(KEY, next);
}
