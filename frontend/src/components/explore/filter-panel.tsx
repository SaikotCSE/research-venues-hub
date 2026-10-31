import { useQuery } from "@tanstack/react-query";
import { Search, X } from "lucide-react";
import * as React from "react";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useDebounced } from "@/hooks/use-debounce";
import { api } from "@/lib/api";
import { activeFilterCount, clearFilters, setValue, toggleValue } from "@/lib/filters";
import { keys } from "@/lib/query";
import type { Facets } from "@/lib/types";
import { cn } from "@/lib/utils";

interface PanelProps {
  params: URLSearchParams;
  onChange: (next: URLSearchParams, opts?: { replace?: boolean }) => void;
  className?: string;
}

export function useFacets() {
  return useQuery({ queryKey: keys.facets, queryFn: () => api.get<Facets>("/facets/"), staleTime: 30 * 60_000 });
}

function ChipToggle({ active, onClick, children, label }: { active: boolean; onClick: () => void; children: React.ReactNode; label?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      aria-label={label}
      className={cn(
        "rounded-md border px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active
          ? "border-primary/40 bg-brand-soft text-brand-text"
          : "border-border bg-background text-muted-foreground hover:border-foreground/20 hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function CheckList({
  name,
  options,
  params,
  onChange,
  limit = 6,
}: {
  name: string;
  options: { value: string; label?: string; count?: number }[];
  params: URLSearchParams;
  onChange: PanelProps["onChange"];
  limit?: number;
}) {
  const [expanded, setExpanded] = React.useState(false);
  const selected = params.getAll(name);
  const shown = expanded ? options : options.slice(0, limit);
  return (
    <div className="space-y-1">
      {shown.map((o) => {
        const id = `f-${name}-${o.value}`.replace(/[^a-zA-Z0-9-_]/g, "_");
        return (
          <div key={o.value} className="flex items-center gap-2.5 rounded-md px-1 py-1 hover:bg-accent/60">
            <Checkbox id={id} checked={selected.includes(o.value)} onCheckedChange={() => onChange(toggleValue(params, name, o.value))} />
            <Label htmlFor={id} className="flex-1 cursor-pointer truncate text-[13px] font-normal text-foreground/90">
              {o.label ?? o.value}
            </Label>
            {o.count != null && <span className="tnum text-[11px] text-muted-foreground">{o.count}</span>}
          </div>
        );
      })}
      {options.length > limit && (
        <button type="button" className="link px-1 text-xs" onClick={() => setExpanded((e) => !e)}>
          {expanded ? "Show fewer" : `Show all ${options.length}`}
        </button>
      )}
    </div>
  );
}

function SearchBox({ params, onChange }: PanelProps) {
  const [value, setValue_] = React.useState(params.get("q") ?? "");
  const debounced = useDebounced(value, 300);
  const urlValue = params.get("q") ?? "";
  React.useEffect(() => setValue_(urlValue), [urlValue]);
  React.useEffect(() => {
    if (debounced.trim() !== urlValue) onChange(setValue(params, "q", debounced.trim() || null), { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
      <Input
        value={value}
        onChange={(e) => setValue_(e.target.value)}
        placeholder="Name, acronym, topic…"
        className="pl-8 pr-8"
        aria-label="Search venues"
        type="search"
      />
      {value && (
        <button
          type="button"
          onClick={() => setValue_("")}
          className="absolute right-2 top-1/2 grid size-5 -translate-y-1/2 place-items-center rounded text-muted-foreground hover:text-foreground"
          aria-label="Clear search"
        >
          <X className="size-3.5" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

export function FilterPanel({ params, onChange, className }: PanelProps) {
  const { data: facets } = useFacets();
  const [tagQuery, setTagQuery] = React.useState("");
  const count = activeFilterCount(params);
  const minIf = Number(params.get("min_if") || 0);
  const [ifDraft, setIfDraft] = React.useState(minIf);
  React.useEffect(() => setIfDraft(minIf), [minIf]);

  if (!facets)
    return (
      <div className={cn("space-y-3", className)} aria-busy="true">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    );

  const tags = facets.tags.filter((t) => t.name.toLowerCase().includes(tagQuery.toLowerCase()));
  const status = params.get("status") ?? "";

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">
          Filters
          {count > 0 && <span className="tnum ml-1.5 rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-bold text-primary-foreground">{count}</span>}
        </h2>
        {count > 0 && (
          <Button variant="ghost" size="xs" onClick={() => onChange(clearFilters(params))}>
            Reset all
          </Button>
        )}
      </div>
      <SearchBox params={params} onChange={onChange} />

      <Accordion type="multiple" defaultValue={["deadline", "type", "rank", "domain"]} className="rounded-xl border bg-card px-3 shadow-card">
        <AccordionItem value="deadline">
          <AccordionTrigger className="py-3 text-[13px] font-semibold">Deadline</AccordionTrigger>
          <AccordionContent className="space-y-3 pb-3 pt-0">
            <ToggleGroup
              type="single"
              value={status || "any"}
              onValueChange={(v) => onChange(setValue(params, "status", v === "any" || !v ? null : v))}
              className="grid w-full grid-cols-3 gap-0.5"
              aria-label="Deadline status"
            >
              <ToggleGroupItem value="any">Any</ToggleGroupItem>
              {facets.status.map((s) => (
                <ToggleGroupItem key={s.value} value={s.value} className="px-1.5">
                  {s.value === "open" ? "Open" : s.value === "upcoming" ? "Soon" : s.label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            <div className="grid gap-1.5">
              <Label htmlFor="f-within" className="text-xs text-muted-foreground">
                Paper deadline within
              </Label>
              <Select value={params.get("within") || "any"} onValueChange={(v) => onChange(setValue(params, "within", v === "any" ? null : v))}>
                <SelectTrigger id="f-within" className="h-8 text-[13px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any time</SelectItem>
                  {facets.within.map((w) => (
                    <SelectItem key={w.value} value={w.value}>
                      {w.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="type">
          <AccordionTrigger className="py-3 text-[13px] font-semibold">Venue type</AccordionTrigger>
          <AccordionContent className="pb-3 pt-0">
            <CheckList
              name="type"
              params={params}
              onChange={onChange}
              options={facets.types.map((t) => ({ value: t, label: t === "Workshop/Symposium" ? "Workshop / Symposium" : t }))}
            />
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="rank">
          <AccordionTrigger className="py-3 text-[13px] font-semibold">Rank & metrics</AccordionTrigger>
          <AccordionContent className="space-y-3 pb-3 pt-0">
            {(
              [
                ["core", "CORE", facets.core.filter((c) => c !== "Unranked")],
                ["ccf", "CCF", facets.ccf.filter((c) => c !== "Unranked")],
                ["quartile", "Journal quartile", facets.quartiles],
              ] as const
            ).map(([key, title, values]) => (
              <fieldset key={key}>
                <legend className="mb-1.5 text-xs text-muted-foreground">{title}</legend>
                <div className="flex flex-wrap gap-1">
                  {values.map((v) => (
                    <ChipToggle key={v} active={params.getAll(key).includes(v)} onClick={() => onChange(toggleValue(params, key, v))} label={`${title} ${v}`}>
                      {v}
                    </ChipToggle>
                  ))}
                </div>
              </fieldset>
            ))}
            <div>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-muted-foreground" id="f-minif-label">
                  Min. impact factor
                </span>
                <span className="tnum font-medium">{ifDraft > 0 ? `≥ ${ifDraft}` : "Any"}</span>
              </div>
              <Slider
                min={0}
                max={40}
                step={1}
                value={[ifDraft]}
                onValueChange={([v]) => setIfDraft(v)}
                onValueCommit={([v]) => onChange(setValue(params, "min_if", v > 0 ? String(v) : null))}
                aria-labelledby="f-minif-label"
                thumbLabel="Minimum impact factor"
              />
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="domain">
          <AccordionTrigger className="py-3 text-[13px] font-semibold">Research domain</AccordionTrigger>
          <AccordionContent className="pb-3 pt-0">
            <CheckList name="domain" params={params} onChange={onChange} options={facets.domains.map((d) => ({ value: d }))} />
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="tags">
          <AccordionTrigger className="py-3 text-[13px] font-semibold">Topics</AccordionTrigger>
          <AccordionContent className="space-y-2 pb-3 pt-0">
            <Input
              value={tagQuery}
              onChange={(e) => setTagQuery(e.target.value)}
              placeholder="Filter topics…"
              className="h-8 text-[13px]"
              aria-label="Filter topics"
            />
            <div className="scrollbar-thin flex max-h-56 flex-wrap gap-1 overflow-y-auto pr-1">
              {tags.map((t) => (
                <ChipToggle key={t.slug} active={params.getAll("tag").includes(t.slug)} onClick={() => onChange(toggleValue(params, "tag", t.slug))}>
                  {t.name} <span className="tnum text-muted-foreground/80">{t.n}</span>
                </ChipToggle>
              ))}
              {tags.length === 0 && <p className="text-xs text-muted-foreground">No matching topics.</p>}
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="location">
          <AccordionTrigger className="py-3 text-[13px] font-semibold">Location</AccordionTrigger>
          <AccordionContent className="space-y-3 pb-3 pt-0">
            <CheckList name="continent" params={params} onChange={onChange} options={facets.continents.map((c) => ({ value: c }))} />
            <div className="grid gap-1.5">
              <Label htmlFor="f-country" className="text-xs text-muted-foreground">
                Country
              </Label>
              <Select value={params.get("country") || "any"} onValueChange={(v) => onChange(setValue(params, "country", v === "any" ? null : v))}>
                <SelectTrigger id="f-country" className="h-8 text-[13px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any country</SelectItem>
                  {facets.countries.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="review">
          <AccordionTrigger className="py-3 text-[13px] font-semibold">Review & access</AccordionTrigger>
          <AccordionContent className="space-y-3 pb-3 pt-0">
            <CheckList name="review" params={params} onChange={onChange} options={facets.review.map((r) => ({ value: r }))} />
            <div className="flex items-center justify-between gap-2 rounded-md px-1">
              <Label htmlFor="f-oa" className="text-[13px] font-normal">
                Open access only
              </Label>
              <Switch id="f-oa" checked={params.get("oa") === "1"} onCheckedChange={(on) => onChange(setValue(params, "oa", on ? "1" : null))} />
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
