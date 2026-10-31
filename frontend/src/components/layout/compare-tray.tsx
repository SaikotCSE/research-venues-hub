import { GitCompareArrows, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { MAX_COMPARE, useCompare } from "@/providers/compare";

/** Floating tray listing the venues picked for comparison. */
export function CompareTray() {
  const compare = useCompare();
  const location = useLocation();
  if (compare.items.length === 0 || location.pathname.startsWith("/compare")) return null;
  const href = `/compare/?${compare.items.map((i) => `s=${encodeURIComponent(i.slug)}`).join("&")}`;
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-4 z-30 flex justify-center px-4" role="region" aria-label="Comparison tray">
      <div className="pointer-events-auto flex max-w-full items-center gap-2 rounded-2xl border bg-popover/95 p-2 pl-3 shadow-lift backdrop-blur-xl animate-in fade-in-0 slide-in-from-bottom-4">
        <GitCompareArrows className="size-4 shrink-0 text-brand-text" aria-hidden="true" />
        <ul className="scrollbar-thin flex min-w-0 items-center gap-1 overflow-x-auto">
          {compare.items.map((i) => (
            <li key={i.slug} className="flex shrink-0 items-center gap-0.5 rounded-lg bg-muted py-0.5 pl-2 pr-0.5 text-xs font-semibold">
              {i.acronym}
              <button
                type="button"
                onClick={() => compare.remove(i.slug)}
                className="grid size-5 place-items-center rounded-md text-muted-foreground hover:bg-background hover:text-foreground"
                aria-label={`Remove ${i.acronym} from comparison`}
              >
                <X className="size-3" aria-hidden="true" />
              </button>
            </li>
          ))}
          {Array.from({ length: MAX_COMPARE - compare.items.length }).map((_, i) => (
            <li key={`empty-${i}`} className="hidden h-6 w-12 shrink-0 rounded-lg border border-dashed sm:block" aria-hidden="true" />
          ))}
        </ul>
        <Button size="sm" asChild disabled={compare.items.length < 2}>
          <Link to={href} aria-disabled={compare.items.length < 2}>
            Compare{compare.items.length > 1 ? ` ${compare.items.length}` : ""}
          </Link>
        </Button>
        <Button size="icon-sm" variant="ghost" onClick={compare.clear} aria-label="Clear comparison">
          <X aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
