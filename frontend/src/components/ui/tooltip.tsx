import { Slot } from "@radix-ui/react-slot";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import * as React from "react";

import { cn } from "@/lib/utils";

export const TooltipProvider = TooltipPrimitive.Provider;
export const TooltipRoot = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-[60] max-w-xs rounded-md bg-zinc-900 px-2.5 py-1.5 text-xs font-medium text-zinc-50 shadow-md animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 dark:bg-zinc-100 dark:text-zinc-900",
        className,
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
));
TooltipContent.displayName = "TooltipContent";

/**
 * <Tooltip content="…"><button/></Tooltip>
 *
 * The Radix tooltip is mounted lazily, on the first hover or focus, so long lists (dozens of cards with
 * icon buttons) don't pay for tooltip machinery they may never use.
 */
export function Tooltip({
  content,
  children,
  side,
  delay,
}: {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: "top" | "bottom" | "left" | "right";
  delay?: number;
}) {
  const [armed, setArmed] = React.useState<false | "hover" | "focus">(false);
  const ref = React.useRef<HTMLButtonElement>(null);
  // Arming swaps the wrapper, which remounts the trigger: give keyboard focus back to it.
  React.useEffect(() => {
    if (armed === "focus") ref.current?.focus({ preventScroll: true });
  }, [armed]);
  if (!content) return children;
  if (!armed)
    return (
      <Slot
        onPointerEnter={() => setArmed("hover")}
        onFocus={(e: React.FocusEvent<HTMLElement>) => e.currentTarget.matches(":focus-visible") && setArmed("focus")}
      >
        {children}
      </Slot>
    );
  return (
    <TooltipRoot delayDuration={delay} defaultOpen={armed === "focus"}>
      <TooltipTrigger asChild ref={ref}>
        {children}
      </TooltipTrigger>
      <TooltipContent side={side}>{content}</TooltipContent>
    </TooltipRoot>
  );
}
