import { Check, Globe } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { browserTimeZone, zoneLabel } from "@/lib/time";
import { cn } from "@/lib/utils";
import { useTimeZone } from "@/providers/timezone";

function allZones(): string[] {
  try {
    const intl = Intl as unknown as { supportedValuesOf?: (key: string) => string[] };
    return intl.supportedValuesOf?.("timeZone") ?? [];
  } catch {
    return [];
  }
}

export function TimezonePicker({ className }: { className?: string }) {
  const { timeZone, setTimeZone } = useTimeZone();
  const [open, setOpen] = React.useState(false);
  const zones = React.useMemo(() => (open ? allZones() : []), [open]);
  const suggested = [...new Set([timeZone, browserTimeZone, "UTC"])];

  const choose = (zone: string) => {
    setTimeZone(zone);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn("gap-1.5 px-2 text-muted-foreground", className)}
          aria-label={`Display timezone: ${timeZone}. Change timezone`}
        >
          <Globe aria-hidden="true" />
          <span className="tnum text-xs font-medium">{zoneLabel(timeZone)}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <Command>
          <CommandInput placeholder="Search timezones…" aria-label="Search timezones" />
          <CommandList>
            <CommandEmpty>No timezone found.</CommandEmpty>
            <CommandGroup heading="Suggested">
              {suggested.map((z) => (
                <CommandItem key={`s-${z}`} value={`suggested ${z}`} onSelect={() => choose(z)}>
                  <Check className={cn("!text-foreground", z === timeZone ? "opacity-100" : "opacity-0")} aria-hidden="true" />
                  <span className="flex-1 truncate">{z === browserTimeZone ? `${z} (this device)` : z}</span>
                  <span className="text-xs text-muted-foreground">{zoneLabel(z)}</span>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandGroup heading="All timezones">
              {zones.map((z) => (
                <CommandItem key={z} value={z} onSelect={() => choose(z)}>
                  <Check className={cn("!text-foreground", z === timeZone ? "opacity-100" : "opacity-0")} aria-hidden="true" />
                  <span className="flex-1 truncate">{z.replace(/_/g, " ")}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
        <p className="border-t px-3 py-2 text-[11px] leading-4 text-muted-foreground">
          Deadlines are shown in this timezone. Hover any date for its Anywhere-on-Earth time.
        </p>
      </PopoverContent>
    </Popover>
  );
}
