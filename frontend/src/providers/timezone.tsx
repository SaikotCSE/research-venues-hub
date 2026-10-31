import * as React from "react";

import { api } from "@/lib/api";
import { browserTimeZone } from "@/lib/time";
import { storage } from "@/lib/utils";

import { useSession, useUpdateSession } from "./session";

interface TimezoneContextValue {
  timeZone: string;
  setTimeZone: (zone: string) => void;
}

const TimezoneContext = React.createContext<TimezoneContextValue | null>(null);

function valid(zone: string | null | undefined) {
  if (!zone) return false;
  try {
    new Intl.DateTimeFormat("en-US", { timeZone: zone });
    return true;
  } catch {
    return false;
  }
}

/** Display timezone: the signed-in user's profile setting, else the last choice on this device, else the browser's. */
export function TimezoneProvider({ children }: { children: React.ReactNode }) {
  const session = useSession();
  const updateSession = useUpdateSession();
  const [local, setLocal] = React.useState(() => storage.raw("vp-tz"));
  const profileZone = session.user?.timezone;
  const timeZone =
    session.authenticated && valid(profileZone) && profileZone !== "UTC"
      ? profileZone!
      : valid(local)
        ? local!
        : session.authenticated && valid(profileZone)
          ? profileZone!
          : browserTimeZone;

  const setTimeZone = React.useCallback(
    (zone: string) => {
      if (!valid(zone)) return;
      storage.setRaw("vp-tz", zone);
      setLocal(zone);
      if (session.authenticated && session.user) {
        updateSession({ user: { ...session.user, timezone: zone } });
        api.post("/me/timezone/", { timezone: zone }).catch(() => undefined);
      }
    },
    [session.authenticated, session.user, updateSession],
  );

  const value = React.useMemo(() => ({ timeZone, setTimeZone }), [timeZone, setTimeZone]);
  return <TimezoneContext.Provider value={value}>{children}</TimezoneContext.Provider>;
}

export function useTimeZone() {
  const ctx = React.useContext(TimezoneContext);
  if (!ctx) throw new Error("useTimeZone must be used inside TimezoneProvider");
  return ctx;
}
