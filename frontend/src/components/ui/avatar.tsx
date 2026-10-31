import * as AvatarPrimitive from "@radix-ui/react-avatar";

import { cn } from "@/lib/utils";

export function Avatar({ initials, className }: { initials: string; className?: string }) {
  return (
    <AvatarPrimitive.Root className={cn("relative grid size-8 shrink-0 place-items-center overflow-hidden rounded-full", className)}>
      <AvatarPrimitive.Fallback className="grid size-full place-items-center bg-gradient-to-br from-indigo-500 to-violet-600 text-[11px] font-semibold text-white">
        {initials}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
}
