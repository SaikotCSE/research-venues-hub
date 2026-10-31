import { Navigate, useLocation } from "react-router-dom";

import { useSession } from "@/providers/session";

/** Client-side guard mirroring the server's login_required redirect. */
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const location = useLocation();
  if (!session.authenticated) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/accounts/login/?next=${next}`} replace />;
  }
  return <>{children}</>;
}
