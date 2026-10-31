import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import type { VenueRef } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface VenueOption extends VenueRef {
  cycles: { id: number; year: number; label: string; submission_deadline: string }[];
}

export function useVenueOptions() {
  return useQuery({ queryKey: keys.venueOptions, queryFn: () => api.get<{ results: VenueOption[] }>("/venue-options/"), staleTime: 10 * 60_000 });
}

export function VenueCombobox({ value, onChange, id, invalid }: { value: string; onChange: (slug: string) => void; id?: string; invalid?: boolean }) {
  const [open, setOpen] = React.useState(false);
  const { data } = useVenueOptions();
  const selected = data?.results.find((v) => v.slug === value);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-invalid={invalid || undefined}
          className={cn("w-full justify-between bg-background font-normal", !selected && "text-muted-foreground", invalid && "border-destructive")}
        >
          <span className="truncate">{selected ? `${selected.acronym} — ${selected.name}` : "Choose a venue…"}</span>
          <ChevronsUpDown className="opacity-50" aria-hidden="true" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] min-w-80 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search by acronym or name…" aria-label="Search venues" />
          <CommandList>
            <CommandEmpty>{data ? "No venue found." : "Loading…"}</CommandEmpty>
            <CommandGroup>
              {(data?.results ?? []).map((v) => (
                <CommandItem
                  key={v.slug}
                  value={`${v.acronym} ${v.name}`}
                  onSelect={() => {
                    onChange(v.slug);
                    setOpen(false);
                  }}
                >
                  <Check className={cn("!text-foreground", v.slug === value ? "opacity-100" : "opacity-0")} aria-hidden="true" />
                  <span className="w-20 shrink-0 font-semibold">{v.acronym}</span>
                  <span className="truncate text-muted-foreground">{v.name}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
