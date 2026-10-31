import { useQuery } from "@tanstack/react-query";
import { Crown, GitCompareArrows, Plus, X } from "lucide-react";
import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/skeleton";
import { RankBadge } from "@/components/venue/badges";
import { CountdownText } from "@/components/venue/countdown";
import { StarButton } from "@/components/venue/star-button";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { formatDateRange, formatDateTime } from "@/lib/time";
import type { CompareCell, CompareData, VenueRef } from "@/lib/types";
import { cn } from "@/lib/utils";
import { MAX_COMPARE, useCompare } from "@/providers/compare";
import { useTimeZone } from "@/providers/timezone";

function Cell({ cell, type }: { cell: CompareCell; type: CompareData["rows"][number]["type"] }) {
  const { timeZone } = useTimeZone();
  const v = cell.value;
  if (v === null || v === "") return <span className="text-muted-foreground">—</span>;
  if (type === "datetime" && typeof v === "string") return <span className="tnum">{formatDateTime(v, timeZone)}</span>;
  if (type === "daterange" && typeof v === "object") return <span className="tnum">{formatDateRange(v.start, v.end)}</span>;
  if (type === "percent" && typeof v === "number") return <span className="tnum">{v.toFixed(1)}%</span>;
  if (type === "number" && typeof v === "number") return <span className="tnum">{Number.isInteger(v) ? v : v.toFixed(2)}</span>;
  return <span>{String(v)}</span>;
}

function AddVenue({ exclude, onAdd }: { exclude: string[]; onAdd: (v: VenueRef) => void }) {
  const [open, setOpen] = React.useState(false);
  const { data } = useQuery({
    queryKey: keys.venueOptions,
    queryFn: () => api.get<{ results: (VenueRef & { cycles: unknown[] })[] }>("/venue-options/"),
    enabled: open,
    staleTime: 10 * 60_000,
  });
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="secondary">
          <Plus aria-hidden="true" /> Add venue
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search venues…" aria-label="Search venues to compare" />
          <CommandList>
            <CommandEmpty>{data ? "No venue found." : "Loading…"}</CommandEmpty>
            <CommandGroup>
              {(data?.results ?? [])
                .filter((v) => !exclude.includes(v.slug))
                .map((v) => (
                  <CommandItem
                    key={v.slug}
                    value={`${v.acronym} ${v.name}`}
                    onSelect={() => {
                      onAdd(v);
                      setOpen(false);
                    }}
                  >
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

export function Component() {
  useDocumentTitle("Compare venues");
  const [params, setParams] = useSearchParams();
  const compare = useCompare();
  const urlSlugs = params.getAll("s").filter(Boolean);
  const slugs = urlSlugs.length ? urlSlugs.slice(0, MAX_COMPARE) : compare.items.map((i) => i.slug);
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: keys.compare(slugs),
    queryFn: () => api.get<CompareData>("/compare/", { s: slugs }),
    enabled: slugs.length > 0,
    placeholderData: (prev) => prev,
  });

  // Keep the tray and the URL in sync so the page is shareable.
  React.useEffect(() => {
    if (!urlSlugs.length && slugs.length) setParams(new URLSearchParams(slugs.map((s) => ["s", s])), { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  React.useEffect(() => {
    if (!data) return;
    const tray = compare.items.map((i) => i.slug).join(",");
    const now = data.venues.map((v) => v.slug).join(",");
    if (tray !== now) {
      compare.clear();
      data.venues.forEach((v) => compare.toggle({ slug: v.slug, acronym: v.acronym }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const setSlugs = (next: string[]) => setParams(new URLSearchParams(next.map((s) => ["s", s])));
  const venues = data?.venues ?? [];

  return (
    <PageContainer>
      <PageHeader
        icon={GitCompareArrows}
        title="Compare venues"
        description={`Ranks, metrics, deadlines and submission rules side by side — up to ${MAX_COMPARE} venues. The best value in each row is highlighted.`}
        actions={slugs.length < MAX_COMPARE && <AddVenue exclude={slugs} onAdd={(v) => setSlugs([...slugs, v.slug])} />}
      />
      {slugs.length === 0 ? (
        <EmptyState
          icon={GitCompareArrows}
          title="Nothing to compare yet"
          description="Use the compare button on any venue card, or add venues here to see them side by side."
        >
          <Button asChild>
            <Link to="/">Browse venues</Link>
          </Button>
        </EmptyState>
      ) : error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <Skeleton className="h-[480px] w-full rounded-xl" />
      ) : (
        <div className="overflow-x-auto rounded-xl border bg-card shadow-card">
          <table className="w-full min-w-[720px] table-fixed text-sm">
            <caption className="sr-only">Comparison of {venues.map((v) => v.acronym).join(", ")}</caption>
            <colgroup>
              <col className="w-40" />
              {venues.map((v) => (
                <col key={v.slug} />
              ))}
            </colgroup>
            <thead>
              <tr className="border-b">
                <th scope="col" className="p-4 text-left align-bottom text-xs font-medium text-muted-foreground">
                  {venues.length} of {MAX_COMPARE} venues
                </th>
                {venues.map((v) => (
                  <th key={v.slug} scope="col" className="p-4 text-left align-top font-normal">
                    <div className="flex items-start gap-3">
                      <VenueMark acronym={v.acronym} />
                      <div className="min-w-0 flex-1">
                        <Link to={`/venue/${v.slug}/`} className="text-base font-semibold hover:text-brand-text">
                          {v.acronym}
                        </Link>
                        <p className="line-clamp-2 text-xs text-muted-foreground">{v.name}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="-mr-2 -mt-1 shrink-0"
                        onClick={() => setSlugs(slugs.filter((s) => s !== v.slug))}
                        aria-label={`Remove ${v.acronym}`}
                      >
                        <X aria-hidden="true" />
                      </Button>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <RankBadge label={v.rank_label} core={v.core_rank} quartile={v.quartile} ccf={v.ccf_rank} />
                      {v.next_deadline && <CountdownText at={v.next_deadline.at} className="text-xs" />}
                      <StarButton slug={v.slug} acronym={v.acronym} starred={v.starred} className="ml-auto" />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.rows.map((row) => (
                <tr key={row.key} className="hover:bg-accent/30">
                  <th scope="row" className="px-4 py-3 text-left text-[13px] font-medium text-muted-foreground">
                    {row.label}
                  </th>
                  {row.cells.map((cell, i) => (
                    <td
                      key={i}
                      className={cn(
                        "px-4 py-3 align-top",
                        cell.best && "bg-emerald-50/70 font-semibold text-emerald-900 dark:bg-emerald-400/[0.06] dark:text-emerald-200",
                      )}
                    >
                      <span className="inline-flex items-center gap-1.5">
                        <Cell cell={cell} type={row.type} />
                        {cell.best && (
                          <>
                            <Crown className="size-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                            <span className="sr-only">(best)</span>
                          </>
                        )}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageContainer>
  );
}
