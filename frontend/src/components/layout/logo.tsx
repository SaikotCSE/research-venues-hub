import { Activity } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "grid size-8 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm shadow-indigo-500/30",
        className,
      )}
    >
      <Activity className="size-[18px]" strokeWidth={2.25} aria-hidden="true" />
    </span>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <Link to="/" className={cn("flex items-center gap-2.5 rounded-lg font-semibold tracking-tight", className)} aria-label="VenuePulse home">
      <LogoMark />
      <span className="text-[15px]">VenuePulse</span>
    </Link>
  );
}
