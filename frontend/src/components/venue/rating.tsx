import { Star } from "lucide-react";

import { cn } from "@/lib/utils";

export function Stars({ value, className, size = "sm" }: { value: number; className?: string; size?: "sm" | "md" }) {
  const dim = size === "sm" ? "size-3.5" : "size-5";
  return (
    <span className={cn("inline-flex items-center gap-0.5", className)} role="img" aria-label={`${value.toFixed(1)} out of 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className="relative">
          <Star className={cn(dim, "text-muted-foreground/30")} aria-hidden="true" />
          <span className="absolute inset-0 overflow-hidden" style={{ width: `${Math.max(0, Math.min(1, value - i + 1)) * 100}%` }}>
            <Star className={cn(dim, "fill-amber-400 text-amber-400")} aria-hidden="true" />
          </span>
        </span>
      ))}
    </span>
  );
}

export function StarInput({ value, onChange, label, id }: { value: number; onChange: (v: number) => void; label: string; id: string }) {
  return (
    <div role="radiogroup" aria-labelledby={id} className="flex gap-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <button
          key={i}
          type="button"
          role="radio"
          aria-checked={value === i}
          aria-label={`${i} of 5`}
          onClick={() => onChange(i)}
          onKeyDown={(e) => {
            if (e.key === "ArrowRight" || e.key === "ArrowUp") {
              e.preventDefault();
              onChange(Math.min(5, value + 1));
            } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
              e.preventDefault();
              onChange(Math.max(1, value - 1));
            }
          }}
          tabIndex={value === i || (!value && i === 1) ? 0 : -1}
          className="rounded p-0.5 transition-transform hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Star className={cn("size-6", i <= value ? "fill-amber-400 text-amber-400" : "text-muted-foreground/40")} aria-hidden="true" />
        </button>
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}
