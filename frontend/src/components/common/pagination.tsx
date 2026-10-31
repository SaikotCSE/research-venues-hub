import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function pages(current: number, total: number): (number | "…")[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const out: (number | "…")[] = [1];
  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  if (start > 2) out.push("…");
  for (let i = start; i <= end; i++) out.push(i);
  if (end < total - 1) out.push("…");
  out.push(total);
  return out;
}

export function Pagination({ page, numPages, onPage, className }: { page: number; numPages: number; onPage: (page: number) => void; className?: string }) {
  if (numPages <= 1) return null;
  return (
    <nav aria-label="Pagination" className={cn("mt-8 flex items-center justify-center gap-1", className)}>
      <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page">
        <ChevronLeft aria-hidden="true" />
        <span className="max-sm:sr-only">Previous</span>
      </Button>
      {pages(page, numPages).map((p, i) =>
        p === "…" ? (
          <span key={`gap-${i}`} className="px-2 text-sm text-muted-foreground" aria-hidden="true">
            …
          </span>
        ) : (
          <Button
            key={p}
            variant={p === page ? "secondary" : "ghost"}
            size="icon-sm"
            className={cn("tnum", p === page && "pointer-events-none font-semibold")}
            aria-current={p === page ? "page" : undefined}
            aria-label={`Page ${p}`}
            onClick={() => onPage(p)}
          >
            {p}
          </Button>
        ),
      )}
      <Button variant="ghost" size="sm" disabled={page >= numPages} onClick={() => onPage(page + 1)} aria-label="Next page">
        <span className="max-sm:sr-only">Next</span>
        <ChevronRight aria-hidden="true" />
      </Button>
    </nav>
  );
}
