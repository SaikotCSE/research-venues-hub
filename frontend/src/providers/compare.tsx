import * as React from "react";
import { toast } from "sonner";

import { storage } from "@/lib/utils";

export const MAX_COMPARE = 4;

export interface CompareItem {
  slug: string;
  acronym: string;
}

interface CompareContextValue {
  items: CompareItem[];
  has: (slug: string) => boolean;
  toggle: (item: CompareItem) => void;
  remove: (slug: string) => void;
  clear: () => void;
  open: boolean;
  setOpen: (open: boolean) => void;
}

const CompareContext = React.createContext<CompareContextValue | null>(null);

/** Venues picked for side-by-side comparison (up to four), remembered on this device. */
export function CompareProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<CompareItem[]>(() => storage.get<CompareItem[]>("vp-compare", []).slice(0, MAX_COMPARE));
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => storage.set("vp-compare", items), [items]);

  const toggle = React.useCallback((item: CompareItem) => {
    setItems((prev) => {
      if (prev.some((p) => p.slug === item.slug)) return prev.filter((p) => p.slug !== item.slug);
      if (prev.length >= MAX_COMPARE) {
        toast.warning(`You can compare up to ${MAX_COMPARE} venues`, { description: "Remove one from the comparison tray first." });
        return prev;
      }
      return [...prev, item];
    });
  }, []);

  const value = React.useMemo<CompareContextValue>(
    () => ({
      items,
      has: (slug) => items.some((i) => i.slug === slug),
      toggle,
      remove: (slug) => setItems((prev) => prev.filter((p) => p.slug !== slug)),
      clear: () => setItems([]),
      open,
      setOpen,
    }),
    [items, toggle, open],
  );
  return <CompareContext.Provider value={value}>{children}</CompareContext.Provider>;
}

export function useCompare() {
  const ctx = React.useContext(CompareContext);
  if (!ctx) throw new Error("useCompare must be used inside CompareProvider");
  return ctx;
}
