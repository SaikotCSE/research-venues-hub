import { useQuery } from "@tanstack/react-query";
import { BarChart3, CalendarClock, Layers, Timer } from "lucide-react";
import * as React from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";

import { ErrorState, PageContainer, PageHeader, Stat } from "@/components/common/page";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { cn } from "@/lib/utils";

interface Insights {
  deadlines_by_month: { labels: string[]; values: number[] };
  by_domain: [string, number][];
  by_type: [string, number][];
  core_distribution: [string, number][];
  quartile_distribution: [string, number][];
  by_continent: [string, number][];
  top_impact: [string, number][];
  scatter: { x: number; y: number; label: string }[];
  open_access_share: { open: number; closed: number };
  totals: { venues: number; cycles: number; upcoming: number; closing_30d: number };
}

const AXIS = { stroke: "var(--chart-axis)", fontSize: 11, tickLine: false, axisLine: { stroke: "var(--chart-grid)" } } as const;

function ChartTooltip({
  active,
  payload,
  label,
  unit,
  labelKey,
}: {
  active?: boolean;
  payload?: { value: number; payload: Record<string, unknown> }[];
  label?: string;
  unit?: string;
  labelKey?: string;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  const title = labelKey ? String(item.payload[labelKey]) : label;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-lift">
      <p className="font-semibold text-foreground">{title}</p>
      <p className="tnum mt-0.5 text-muted-foreground">
        {item.value.toLocaleString()} {unit}
      </p>
    </div>
  );
}

/** Mount a chart only when it nears the viewport, inside a transition, so the page never blocks on rendering SVG. */
function LazyChart({ children, height }: { children: React.ReactNode; height: number }) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [visible, setVisible] = React.useState(false);
  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!("IntersectionObserver" in window)) {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          React.startTransition(() => setVisible(true));
          io.disconnect();
        }
      },
      { rootMargin: "200px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} style={{ height }}>
      {visible ? children : <div className="animate-pulse rounded-lg bg-muted/60" style={{ height }} />}
    </div>
  );
}

function ChartCard({
  title,
  description,
  rows,
  columns,
  children,
  className,
}: {
  title: string;
  description?: string;
  rows: (string | number)[][];
  columns: string[];
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("flex flex-col", className)}>
      <Tabs defaultValue="chart" className="flex flex-1 flex-col">
        <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
          <div>
            <CardTitle>{title}</CardTitle>
            {description && <CardDescription className="mt-1">{description}</CardDescription>}
          </div>
          <TabsList className="h-8 shrink-0">
            <TabsTrigger value="chart" className="px-2 text-xs">
              Chart
            </TabsTrigger>
            <TabsTrigger value="table" className="px-2 text-xs">
              Table
            </TabsTrigger>
          </TabsList>
        </CardHeader>
        <CardContent className="flex-1">
          <TabsContent value="chart" className="mt-0 h-full">
            {/* The SVG is decorative for assistive tech; the Table tab carries the same data. */}
            <div aria-hidden="true">{children}</div>
            <p className="sr-only">Chart of {title.toLowerCase()}. Switch to the Table tab for the underlying numbers.</p>
          </TabsContent>
          <TabsContent value="table" className="mt-0">
            <div className="scrollbar-thin max-h-72 overflow-y-auto rounded-lg border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-surface text-left text-xs text-muted-foreground">
                  <tr>
                    {columns.map((c, i) => (
                      <th key={c} scope="col" className={cn("px-3 py-2 font-medium", i > 0 && "text-right")}>
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {rows.map((r, i) => (
                    <tr key={i}>
                      {r.map((cell, j) => (
                        <td key={j} className={cn("px-3 py-1.5", j > 0 && "tnum text-right")}>
                          {typeof cell === "number" ? cell.toLocaleString() : cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </CardContent>
      </Tabs>
    </Card>
  );
}

function Columns({ data, unit, height = 240 }: { data: { name: string; value: number }[]; unit: string; height?: number }) {
  return (
    <LazyChart height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 18, right: 4, left: -18, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
          <XAxis dataKey="name" {...AXIS} interval="preserveStartEnd" />
          <YAxis {...AXIS} axisLine={false} allowDecimals={false} width={44} />
          <Tooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.6 }} content={<ChartTooltip unit={unit} />} />
          <Bar dataKey="value" fill="var(--chart-1)" radius={[4, 4, 0, 0]} maxBarSize={24} name={unit} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </LazyChart>
  );
}

function HorizontalBars({
  data,
  unit,
  format = (v: number) => v.toLocaleString(),
}: {
  data: { name: string; value: number }[];
  unit: string;
  format?: (v: number) => string;
}) {
  const height = Math.max(160, data.length * 30 + 24);
  return (
    <LazyChart height={height}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 40, left: 0, bottom: 0 }} barCategoryGap={6}>
          <CartesianGrid horizontal={false} stroke="var(--chart-grid)" />
          <XAxis type="number" hide />
          <YAxis type="category" dataKey="name" {...AXIS} axisLine={false} width={150} tick={{ fill: "var(--chart-axis)", fontSize: 12 }} />
          <Tooltip cursor={{ fill: "var(--chart-grid)", opacity: 0.6 }} content={<ChartTooltip unit={unit} />} />
          <Bar dataKey="value" fill="var(--chart-1)" radius={[0, 4, 4, 0]} maxBarSize={20} name={unit} isAnimationActive={false}>
            <LabelList dataKey="value" position="right" formatter={format} className="fill-muted-foreground text-[11px] font-medium" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </LazyChart>
  );
}

function ShareBar({ open, closed }: { open: number; closed: number }) {
  const total = open + closed || 1;
  const pct = Math.round((open / total) * 100);
  return (
    <div>
      <p className="text-4xl font-semibold tracking-tight">{pct}%</p>
      <p className="mt-1 text-sm text-muted-foreground">of venues publish open access</p>
      <div className="mt-5 flex h-3 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={`${open} open access, ${closed} subscription or hybrid`}>
        <span className="h-full rounded-l-full" style={{ width: `${(open / total) * 100}%`, background: "var(--chart-1)" }} />
        <span className="h-full rounded-r-full" style={{ width: `${(closed / total) * 100}%`, background: "var(--chart-2)" }} />
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground">
        <li className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: "var(--chart-1)" }} aria-hidden="true" />
          Open access <span className="tnum font-medium text-foreground">{open}</span>
        </li>
        <li className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: "var(--chart-2)" }} aria-hidden="true" />
          Subscription / hybrid <span className="tnum font-medium text-foreground">{closed}</span>
        </li>
      </ul>
    </div>
  );
}

export function Component() {
  useDocumentTitle("Insights");
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: keys.insights,
    queryFn: () => api.get<Insights>("/api/insights/"),
    staleTime: 10 * 60_000,
  });

  const months = React.useMemo(
    () =>
      data
        ? data.deadlines_by_month.labels.map((l, i) => ({
            name: l.replace(/ (\d{2})(\d{2})$/, " ’$2"),
            full: l,
            value: data.deadlines_by_month.values[i],
          }))
        : [],
    [data],
  );
  const pair = (rows: [string, number][]) => rows.map(([name, value]) => ({ name, value }));

  return (
    <PageContainer>
      <PageHeader
        icon={BarChart3}
        title="Insights"
        description="The research venue landscape at a glance: when deadlines cluster, how venues rank, and how selective and influential they are."
      />
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading || !data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-80 rounded-xl" />
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat
              label="Venues"
              value={data.totals.venues.toLocaleString()}
              icon={Layers}
              hint={data.by_type.map(([t, n]) => `${n} ${t === "Workshop/Symposium" ? "symposia" : t.toLowerCase() + "s"}`).join(" · ")}
            />
            <Stat label="Deadline cycles" value={data.totals.cycles.toLocaleString()} icon={CalendarClock} hint="Past, current and projected editions" />
            <Stat label="Upcoming deadlines" value={data.totals.upcoming.toLocaleString()} icon={Timer} hint="Paper deadlines still ahead" />
            <Stat label="Closing in 30 days" value={data.totals.closing_30d.toLocaleString()} icon={Timer} hint="Start writing!" />
          </div>

          <ChartCard
            title="Paper deadlines per month"
            description="Upcoming submission deadlines over the next twelve months."
            columns={["Month", "Deadlines"]}
            rows={months.map((m) => [m.full, m.value])}
          >
            <Columns data={months} unit="deadlines" height={260} />
          </ChartCard>

          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard title="Venues by research domain" columns={["Domain", "Venues"]} rows={data.by_domain}>
              <HorizontalBars data={pair(data.by_domain).slice(0, 12)} unit="venues" />
            </ChartCard>
            <ChartCard
              title="Selectivity vs. influence"
              description="Conference acceptance rate against Google Scholar h5-index. Up and to the left is selective and highly cited."
              columns={["Venue", "Acceptance %", "h5-index"]}
              rows={data.scatter.map((p) => [p.label, p.x, p.y])}
            >
              <LazyChart height={300}>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 8, right: 12, left: -12, bottom: 8 }}>
                    <CartesianGrid stroke="var(--chart-grid)" />
                    <XAxis type="number" dataKey="x" name="Acceptance rate" unit="%" {...AXIS} domain={[0, "dataMax + 5"]} />
                    <YAxis type="number" dataKey="y" name="h5-index" {...AXIS} width={48} />
                    <ZAxis range={[64, 64]} />
                    <Tooltip
                      cursor={{ stroke: "var(--chart-grid)" }}
                      content={({ active, payload }) => {
                        const p = payload?.[0]?.payload as { x: number; y: number; label: string } | undefined;
                        if (!active || !p) return null;
                        return (
                          <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-lift">
                            <p className="font-semibold">{p.label}</p>
                            <p className="tnum mt-0.5 text-muted-foreground">
                              {p.x.toFixed(1)}% accepted · h5 {p.y}
                            </p>
                          </div>
                        );
                      }}
                    />
                    <Scatter data={data.scatter} fill="var(--chart-1)" stroke="hsl(var(--card))" strokeWidth={2} isAnimationActive={false} />
                  </ScatterChart>
                </ResponsiveContainer>
              </LazyChart>
            </ChartCard>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <ChartCard title="CORE ranks" description="Conferences and symposia" columns={["Rank", "Venues"]} rows={data.core_distribution}>
              <Columns data={pair(data.core_distribution)} unit="venues" />
            </ChartCard>
            <ChartCard
              title="Journal quartiles"
              description="Within each journal’s subject category"
              columns={["Quartile", "Journals"]}
              rows={data.quartile_distribution}
            >
              <Columns data={pair(data.quartile_distribution)} unit="journals" />
            </ChartCard>
            <Card>
              <CardHeader>
                <CardTitle>Open access</CardTitle>
                <CardDescription>Share of venues free to read</CardDescription>
              </CardHeader>
              <CardContent>
                <ShareBar open={data.open_access_share.open} closed={data.open_access_share.closed} />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <ChartCard title="Highest impact factor journals" columns={["Journal", "Impact factor"]} rows={data.top_impact}>
              <HorizontalBars data={pair(data.top_impact)} unit="impact factor" format={(v) => v.toFixed(1)} />
            </ChartCard>
            <ChartCard
              title="Where venues are hosted"
              description="By continent of the next edition (online-only venues excluded)"
              columns={["Continent", "Venues"]}
              rows={data.by_continent}
            >
              <HorizontalBars data={pair(data.by_continent)} unit="venues" />
            </ChartCard>
          </div>
        </div>
      )}
    </PageContainer>
  );
}
