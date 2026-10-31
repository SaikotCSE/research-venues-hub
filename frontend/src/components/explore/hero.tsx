import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Search, Sparkles } from "lucide-react";
import * as React from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { CountdownText } from "@/components/venue/countdown";
import { VenueMark } from "@/components/venue/venue-mark";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { formatDate } from "@/lib/time";
import type { HomeData } from "@/lib/types";
import { useTimeZone } from "@/providers/timezone";

export function Hero() {
  const navigate = useNavigate();
  const { timeZone } = useTimeZone();
  const [q, setQ] = React.useState("");
  const { data } = useQuery({ queryKey: keys.home, queryFn: () => api.get<HomeData>("/home/") });
  const stats = data?.stats;
  return (
    <section className="relative overflow-hidden border-b">
      <div className="bg-grid mask-fade pointer-events-none absolute inset-0 opacity-60" aria-hidden="true" />
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-[480px] w-[960px] -translate-x-1/2 rounded-full bg-gradient-to-br from-indigo-500/20 via-violet-500/10 to-sky-400/10 blur-3xl dark:from-indigo-500/25 dark:via-violet-500/10"
        aria-hidden="true"
      />
      <div className="relative mx-auto max-w-screen-2xl px-4 pb-10 pt-12 sm:px-6 sm:pt-16 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <Link
            to="/recommend/"
            className="inline-flex items-center gap-2 rounded-full border bg-background/70 px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm backdrop-blur transition-colors hover:text-foreground"
          >
            <Sparkles className="size-3.5 text-brand-text" aria-hidden="true" />
            New: paste an abstract, get matching venues
            <ArrowRight className="size-3" aria-hidden="true" />
          </Link>
          <h1 className="mt-5 text-balance text-4xl font-semibold tracking-tight sm:text-5xl sm:leading-[1.08]">
            Every research deadline,{" "}
            <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-sky-500 bg-clip-text text-transparent dark:from-indigo-300 dark:via-violet-300 dark:to-sky-300">
              one place.
            </span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-base leading-7 text-muted-foreground sm:text-lg">
            Live countdowns in your timezone and AoE, ranks and acceptance rates, submission rules and calendar feeds for{" "}
            {stats ? <span className="tnum font-medium text-foreground">{stats.venues}</span> : "dozens of"} conferences and journals.
          </p>
          <form
            role="search"
            className="mx-auto mt-7 flex max-w-xl items-center gap-2 rounded-2xl border bg-background/90 p-1.5 shadow-lift backdrop-blur"
            onSubmit={(e) => {
              e.preventDefault();
              navigate(q.trim() ? `/?q=${encodeURIComponent(q.trim())}` : "/?status=open");
              document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
            }}
          >
            <Search className="ml-2.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Try “NeurIPS”, “computer vision” or “security”"
              aria-label="Search conferences and journals"
              className="h-10 min-w-0 flex-1 bg-transparent text-[15px] outline-none placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0"
            />
            <Button type="submit" className="h-10 rounded-xl px-5">
              Search
            </Button>
          </form>
          {stats && (
            <dl className="mx-auto mt-8 grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                ["Venues tracked", stats.venues],
                ["Open for submissions", stats.open],
                ["Deadlines in 30 days", stats.closing_30],
                ["Host countries", stats.countries],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl border bg-background/70 px-3 py-2.5 backdrop-blur">
                  <dt className="text-[11px] font-medium text-muted-foreground">{label}</dt>
                  <dd className="tnum text-xl font-semibold tracking-tight">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>

        {data && data.closing_soon.length > 0 && (
          <div className="mt-10">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Closing soon</h2>
              <Link to="/?within=30" className="link text-xs">
                All deadlines in the next 30 days
              </Link>
            </div>
            <ul className="scrollbar-thin -mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-3 sm:overflow-visible sm:px-0 xl:grid-cols-6">
              {data.closing_soon.map(({ venue, cycle }) => (
                <li key={cycle.id} className="w-56 shrink-0 snap-start sm:w-auto">
                  <Link
                    to={`/venue/${venue.slug}/`}
                    className="group flex h-full flex-col rounded-xl border bg-card/90 p-3 shadow-card backdrop-blur transition-[box-shadow,transform] hover:-translate-y-0.5 hover:shadow-lift"
                  >
                    <span className="flex items-center gap-2">
                      <VenueMark acronym={venue.acronym} size="sm" />
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold group-hover:text-brand-text">{cycle.label}</span>
                        <span className="block truncate text-[11px] text-muted-foreground">{venue.rank_label}</span>
                      </span>
                    </span>
                    <span className="mt-3 flex items-baseline justify-between gap-2">
                      <CountdownText at={cycle.submission_deadline} className="text-sm" />
                      <span className="tnum text-[11px] text-muted-foreground">{formatDate(cycle.submission_deadline, timeZone, true)}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
