import { useQuery } from "@tanstack/react-query";
import { Sparkles, Wand2 } from "lucide-react";
import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { useFacets } from "@/components/explore/filter-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { VenueCard, VenueCardSkeleton } from "@/components/venue/venue-card";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import type { Recommendation } from "@/lib/types";
import { useSession } from "@/providers/session";

const EXAMPLES = [
  "Self-supervised learning for medical image segmentation with limited labels",
  "Formal verification of smart contracts and blockchain consensus protocols",
  "Large language models for code generation and program repair",
];

export function Component() {
  useDocumentTitle("Venue recommender");
  const session = useSession();
  const [params, setParams] = useSearchParams();
  const text = params.get("text") ?? "";
  const [draft, setDraft] = React.useState(text);
  const { data: facets } = useFacets();
  React.useEffect(() => setDraft(text), [text]);

  const { data, error, isFetching, refetch } = useQuery({
    queryKey: keys.recommend(params.toString()),
    queryFn: () => api.get<{ results: Recommendation[]; interests: string }>("/recommend/", params),
    enabled: !!text,
  });
  const { data: me } = useQuery({
    queryKey: keys.recommend("interests"),
    queryFn: () => api.get<{ interests: string }>("/recommend/"),
    enabled: session.authenticated && !text,
    staleTime: 5 * 60_000,
  });
  const interests = data?.interests || me?.interests;

  const submit = (value = draft) => {
    const next = new URLSearchParams(params);
    if (value.trim()) next.set("text", value.trim());
    else next.delete("text");
    setParams(next);
  };
  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === "any") next.delete(key);
    else next.set(key, value);
    setParams(next);
  };

  return (
    <PageContainer size="default">
      <PageHeader
        icon={Sparkles}
        title="Find the right venue"
        description="Paste your abstract, title or keywords. We rank venues by topical fit, then prefer stronger venues and ones with a deadline in the next four months."
      />
      <Card className="mb-8">
        <CardContent className="p-5">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <Label htmlFor="rec-text" className="sr-only">
              Abstract or keywords
            </Label>
            <Textarea
              id="rec-text"
              rows={5}
              maxLength={2000}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="e.g. We propose a diffusion-based method for 3D scene reconstruction from sparse views…"
              className="text-[15px]"
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
              }}
            />
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <Select value={params.get("domain") ?? "any"} onValueChange={(v) => setFilter("domain", v)}>
                <SelectTrigger className="h-8 w-auto min-w-[11rem] text-[13px]" aria-label="Research domain">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any domain</SelectItem>
                  {facets?.domains.map((d) => (
                    <SelectItem key={d} value={d}>
                      {d}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={params.get("type") ?? "any"} onValueChange={(v) => setFilter("type", v)}>
                <SelectTrigger className="h-8 w-auto min-w-[9rem] text-[13px]" aria-label="Venue type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="any">Any type</SelectItem>
                  {facets?.types.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="ml-auto text-xs text-muted-foreground max-sm:hidden">⌘/Ctrl + Enter</span>
              <Button type="submit" loading={isFetching} disabled={!draft.trim()}>
                <Wand2 aria-hidden="true" /> Recommend
              </Button>
            </div>
          </form>
          {!text && (
            <div className="mt-4 border-t pt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Try an example</p>
              <div className="flex flex-wrap gap-2">
                {interests && (
                  <button
                    type="button"
                    className="rounded-full border border-primary/30 bg-brand-soft px-3 py-1 text-xs font-medium text-brand-text hover:bg-brand-soft/70"
                    onClick={() => submit(interests)}
                  >
                    Use my research interests
                  </button>
                )}
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-foreground/20 hover:text-foreground"
                    onClick={() => submit(ex)}
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {text &&
        (error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : !data ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <VenueCardSkeleton key={i} />
            ))}
          </div>
        ) : data.results.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title="No strong matches"
            description="Try more specific technical terms (methods, tasks, application areas), or remove the domain filter."
          />
        ) : (
          <section aria-labelledby="rec-results">
            <h2 id="rec-results" className="mb-4 text-lg font-semibold tracking-tight">
              {data.results.length} recommended venues
            </h2>
            <ol className="grid gap-4 sm:grid-cols-2">
              {data.results.map((r, i) => (
                <li key={r.venue.slug} className="flex flex-col gap-2">
                  <div className="flex items-center gap-3 px-1">
                    <span className="tnum text-xs font-semibold text-muted-foreground">#{i + 1}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                      <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500" style={{ width: `${r.percent}%` }} />
                    </div>
                    <span className="tnum text-xs font-semibold text-brand-text">{r.percent}% match</span>
                  </div>
                  <VenueCard venue={r.venue} />
                  {r.reasons.length > 0 && <p className="px-1 text-xs text-muted-foreground">Matched on {r.reasons.join(", ")}</p>}
                </li>
              ))}
            </ol>
          </section>
        ))}
    </PageContainer>
  );
}
