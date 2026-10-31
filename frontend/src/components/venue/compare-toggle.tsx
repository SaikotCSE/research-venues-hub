import { GitCompareArrows } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { useCompare } from "@/providers/compare";

export function CompareToggle({
  slug,
  acronym,
  variant = "icon",
  className,
}: {
  slug: string;
  acronym: string;
  variant?: "icon" | "full";
  className?: string;
}) {
  const compare = useCompare();
  const active = compare.has(slug);
  const onClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    compare.toggle({ slug, acronym });
  };
  if (variant === "full")
    return (
      <Button variant={active ? "soft" : "secondary"} onClick={onClick} aria-pressed={active} className={className}>
        <GitCompareArrows aria-hidden="true" />
        {active ? "In comparison" : "Compare"}
      </Button>
    );
  return (
    <Tooltip content={active ? "Remove from comparison" : "Add to comparison"}>
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={onClick}
        aria-pressed={active}
        aria-label={active ? `Remove ${acronym} from comparison` : `Compare ${acronym}`}
        className={cn("text-muted-foreground", active && "bg-brand-soft text-brand-text hover:bg-brand-soft", className)}
      >
        <GitCompareArrows aria-hidden="true" />
      </Button>
    </Tooltip>
  );
}
