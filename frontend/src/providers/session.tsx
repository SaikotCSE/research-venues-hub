import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { api, setCsrfToken } from "@/lib/api";
import { boot } from "@/lib/boot";
import { keys } from "@/lib/query";
import type { Session } from "@/lib/types";

/** Current visitor (anonymous or signed in). Seeded from the shell, refreshed after auth changes. */
export function useSession() {
  const { data } = useQuery({
    queryKey: keys.session,
    queryFn: () => api.get<Session>("/session/"),
    initialData: boot.session,
    staleTime: 5 * 60_000,
  });
  React.useEffect(() => setCsrfToken(data.csrf_token), [data.csrf_token]);
  return data;
}

export function useUpdateSession() {
  const qc = useQueryClient();
  return React.useCallback(
    (session: Partial<Session> & { csrf_token?: string }) => {
      if (session.csrf_token) setCsrfToken(session.csrf_token);
      qc.setQueryData<Session>(keys.session, (old) => ({ ...(old ?? boot.session), ...session, messages: [] }) as Session);
    },
    [qc],
  );
}

/** After login/logout/signup: replace the session and drop every cached per-user query. */
export function useResetAfterAuth() {
  const qc = useQueryClient();
  return React.useCallback(
    (session: Session) => {
      setCsrfToken(session.csrf_token);
      qc.setQueryData(keys.session, { ...session, messages: [] });
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "session" && q.queryKey[0] !== "facets" && q.queryKey[0] !== "home" });
    },
    [qc],
  );
}
