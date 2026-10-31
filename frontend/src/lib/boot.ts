import type { Boot } from "./types";

const fallback: Boot = {
  page: "explore",
  status: 200,
  session: { authenticated: false, csrf_token: "", user: null, unread_count: 0, target_count: 0, messages: [], admin_url: null },
  initial: {},
  extra: {},
  site: { name: "VenuePulse", url: "" },
};

function read(): Boot {
  if (typeof document === "undefined") return fallback;
  const el = document.getElementById("vp-boot");
  if (!el?.textContent) return fallback;
  try {
    return { ...fallback, ...(JSON.parse(el.textContent) as Boot) };
  } catch {
    return fallback;
  }
}

/** Data the Django shell embedded for the first screen (session, page status, initial query data). */
export const boot: Boot = read();

/** Path + query the shell was rendered for; initial data only applies to this exact URL. */
export const bootLocation = typeof window === "undefined" ? "" : window.location.pathname + window.location.search;
