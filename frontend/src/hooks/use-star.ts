import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, errorMessage } from "@/lib/api";
import { keys } from "@/lib/query";
import type { Session, VenueCard, VenueDetail } from "@/lib/types";

type Starrable = { starred?: boolean; slug: string };

function patchStar<T>(data: T, slug: string, starred: boolean): T {
  if (!data || typeof data !== "object") return data;
  if (Array.isArray(data)) return data.map((d) => patchStar(d, slug, starred)) as T;
  const obj = data as Record<string, unknown>;
  let changed = false;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj)) {
    const next = v && typeof v === "object" ? patchStar(v, slug, starred) : v;
    if (next !== v) changed = true;
    out[k] = next;
  }
  if ((obj as Starrable).slug === slug && "starred" in obj && obj.starred !== starred) {
    out.starred = starred;
    changed = true;
  }
  return (changed ? out : data) as T;
}

/** Star / unstar a venue with an optimistic update across every cached list and detail. */
export function useStar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, starred }: { slug: string; starred: boolean; acronym: string }) =>
      api.post<{ starred: boolean; target_count: number; message: string }>(`/venues/${slug}/star/`, { starred }),
    onMutate: async ({ slug, starred }) => {
      const touched = ["explore", "venue", "recommend", "plan", "compare", "list", "dashboard"];
      const snapshots = qc.getQueriesData({ predicate: (q) => touched.includes(String(q.queryKey[0])) });
      for (const [key, data] of snapshots) qc.setQueryData<unknown>(key, patchStar(data, slug, starred));
      qc.setQueryData<VenueDetail>(keys.venue(slug), (old) => (old ? { ...old, starred, me: { ...old.me, starred } } : old));
      return { snapshots };
    },
    onError: (error, _vars, ctx) => {
      ctx?.snapshots.forEach(([key, data]) => qc.setQueryData<unknown>(key, data));
      toast.error(errorMessage(error));
    },
    onSuccess: (data, { slug, acronym }) => {
      qc.setQueryData<Session>(keys.session, (old) => (old ? { ...old, target_count: data.target_count } : old));
      qc.setQueryData<VenueDetail>(keys.venue(slug), (old) =>
        old ? { ...old, tracking_count: Math.max(0, old.tracking_count + (data.starred ? 1 : -1)) } : old,
      );
      qc.invalidateQueries({ queryKey: keys.targets });
      qc.invalidateQueries({ queryKey: keys.dashboard });
      toast.success(data.starred ? `Saved ${acronym} to My Targets` : `Removed ${acronym} from My Targets`, {
        description: data.starred ? "You'll see its deadlines on your targets page." : undefined,
      });
    },
  });
}

export type { VenueCard };
