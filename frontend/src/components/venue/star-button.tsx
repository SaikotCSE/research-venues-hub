import { Star } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/tooltip";
import { useStar } from "@/hooks/use-star";
import { cn } from "@/lib/utils";

interface Props {
  slug: string;
  acronym: string;
  starred: boolean;
  variant?: "icon" | "full";
  className?: string;
}

export function StarButton({ slug, acronym, starred, variant = "icon", className }: Props) {
  const star = useStar();
  const label = starred ? `Remove ${acronym} from My Targets` : `Save ${acronym} to My Targets`;
  const onClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    star.mutate({ slug, acronym, starred: !starred });
  };
  if (variant === "full")
    return (
      <Button variant={starred ? "soft" : "secondary"} onClick={onClick} aria-pressed={starred} className={className}>
        <Star className={cn(starred && "fill-amber-400 text-amber-500")} aria-hidden="true" />
        {starred ? "Saved to targets" : "Save to targets"}
      </Button>
    );
  return (
    <Tooltip content={starred ? "Saved to My Targets" : "Save to My Targets"}>
      <Button variant="ghost" size="icon-sm" onClick={onClick} aria-pressed={starred} aria-label={label} className={cn("text-muted-foreground", className)}>
        <Star className={cn("transition-transform", starred && "scale-110 fill-amber-400 text-amber-500")} aria-hidden="true" />
      </Button>
    </Tooltip>
  );
}
