import { useQuery } from "@tanstack/react-query";
import { Braces, ChevronRight, KeyRound, Loader2, Play } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { CodeBlock } from "@/components/common/code-block";
import { PageContainer, PageHeader } from "@/components/common/page";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { cn } from "@/lib/utils";
import { useSession } from "@/providers/session";

interface ApiMeta {
  host: string;
  groups: { title: string; endpoints: { method: string; path: string; description: string }[] }[];
  filters: { name: string; type: string; description: string }[];
  limits: Record<string, string>;
  examples: string[];
}

const TOC = [
  ["quickstart", "Quick start"],
  ["try", "Try it"],
  ["conventions", "Conventions"],
  ["endpoints", "Endpoints"],
  ["filters", "Filter parameters"],
  ["auth", "Authentication"],
];

function TryIt({ examples }: { examples: string[] }) {
  const [path, setPath] = React.useState("/api/venues/?core=A*&page_size=3");
  const [result, setResult] = React.useState<{ status: string; body: string } | null>(null);
  const [busy, setBusy] = React.useState(false);
  const run = async (p = path) => {
    setBusy(true);
    try {
      const res = await fetch(p.startsWith("/api/") ? p : `/api/${p.replace(/^\/+/, "")}`, { headers: { Accept: "application/json" } });
      setResult({ status: `${res.status} ${res.statusText}`, body: JSON.stringify(await res.json(), null, 2) });
    } catch {
      setResult({ status: "Network error", body: "" });
    }
    setBusy(false);
  };
  return (
    <Card>
      <CardContent className="space-y-3 p-5">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            run();
          }}
        >
          <div className="relative flex-1">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 font-mono text-xs font-semibold text-emerald-700 dark:text-emerald-400">
              GET
            </span>
            <Input
              value={path}
              onChange={(e) => setPath(e.target.value)}
              className="pl-12 font-mono text-[13px]"
              aria-label="Request path"
              spellCheck={false}
            />
          </div>
          <Button type="submit" disabled={busy}>
            {busy ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Play aria-hidden="true" />} Send
          </Button>
        </form>
        <div className="flex flex-wrap gap-1.5">
          {examples.map((ex) => (
            <button
              key={ex}
              type="button"
              className="rounded-md border bg-surface px-2 py-1 font-mono text-[11px] text-muted-foreground hover:text-foreground"
              onClick={() => {
                setPath(ex);
                run(ex);
              }}
            >
              {ex}
            </button>
          ))}
        </div>
        {result && (
          <div aria-live="polite">
            <p className={cn("mb-2 text-xs font-semibold", result.status.startsWith("2") ? "text-emerald-700 dark:text-emerald-400" : "text-destructive")}>
              {result.status}
            </p>
            <pre className="scrollbar-thin max-h-96 overflow-auto rounded-xl border bg-zinc-950 p-4 font-mono text-[12px] leading-5 text-zinc-100">
              {result.body}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function Component() {
  useDocumentTitle("API documentation");
  const session = useSession();
  const { data } = useQuery({ queryKey: keys.apiMeta, queryFn: () => api.get<ApiMeta>("/api-meta/"), staleTime: Infinity });
  const host = data?.host ?? window.location.origin;
  const snippets = {
    curl: `# A* conferences with a paper deadline in the next 60 days\ncurl "${host}/api/venues/?core=A*&within=60&sort=deadline"\n\n# Star a venue with your token\ncurl -X POST -H "Authorization: Bearer $VENUEPULSE_TOKEN" \\\n     -H "Content-Type: application/json" \\\n     -d '{"slug": "neurips"}' ${host}/api/v1/me/targets/`,
    python: `import requests\n\nurl = "${host}/api/venues/"\nparams = {"type": "Journal", "quartile": "Q1", "min_if": 10, "page_size": 50}\nwhile url:\n    page = requests.get(url, params=params, timeout=10).json()\n    for venue in page["results"]:\n        print(venue["acronym"], venue["impact_factor"], venue["url"])\n    url, params = page["next"], None  # follow pagination links`,
    js: `// Public endpoints send CORS headers, so this works from any website.\nconst res = await fetch("${host}/api/venues/?status=open&sort=deadline&page_size=5");\nconst { results } = await res.json();\nresults.forEach((v) => console.log(v.acronym, v.next_deadline?.at));`,
  };
  return (
    <PageContainer>
      <div className="grid gap-10 lg:grid-cols-[12rem_1fr]">
        <nav aria-label="On this page" className="hidden lg:block">
          <ul className="sticky top-24 space-y-1 text-sm">
            {TOC.map(([id, label]) => (
              <li key={id}>
                <a
                  href={`#${id}`}
                  className="flex items-center gap-1.5 rounded-md px-2 py-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  <ChevronRight className="size-3" aria-hidden="true" />
                  {label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <div className="min-w-0 space-y-12">
          <PageHeader
            className="mb-0"
            icon={Braces}
            eyebrow="Developers"
            title="VenuePulse API"
            description={
              <>
                A read-only JSON API for the venue catalogue plus token-authenticated endpoints for your own targets and submissions. Machine-readable
                description:{" "}
                <a href="/api/openapi.json" className="link font-mono text-[13px]">
                  /api/openapi.json
                </a>{" "}
                (OpenAPI 3.1).
              </>
            }
            actions={
              <>
                <Button variant="secondary" asChild>
                  <a href="/api/openapi.json">OpenAPI schema</a>
                </Button>
                <Button asChild>
                  <Link to={session.authenticated ? "/accounts/profile/#api" : "/accounts/signup/?next=/accounts/profile/"}>
                    <KeyRound aria-hidden="true" /> {session.authenticated ? "Your API token" : "Get an API token"}
                  </Link>
                </Button>
              </>
            }
          />

          <section id="quickstart" aria-labelledby="qs-h" className="scroll-mt-20">
            <h2 id="qs-h" className="mb-4 text-xl font-semibold tracking-tight">
              Quick start
            </h2>
            <Tabs defaultValue="curl">
              <TabsList>
                <TabsTrigger value="curl">curl</TabsTrigger>
                <TabsTrigger value="python">Python</TabsTrigger>
                <TabsTrigger value="js">JavaScript</TabsTrigger>
              </TabsList>
              {Object.entries(snippets).map(([key, code]) => (
                <TabsContent key={key} value={key}>
                  <CodeBlock code={code} />
                </TabsContent>
              ))}
            </Tabs>
          </section>

          <section id="try" aria-labelledby="try-h" className="scroll-mt-20">
            <h2 id="try-h" className="mb-1 text-xl font-semibold tracking-tight">
              Try it
            </h2>
            <p className="mb-4 text-sm text-muted-foreground">Runs against this server. Public GET endpoints only.</p>
            <TryIt examples={data?.examples ?? []} />
          </section>

          <section id="conventions" aria-labelledby="conv-h" className="scroll-mt-20">
            <h2 id="conv-h" className="mb-4 text-xl font-semibold tracking-tight">
              Conventions
            </h2>
            <dl className="grid gap-3 sm:grid-cols-2">
              {[
                ["Pagination", "Lists return count, page, num_pages, page_size (1–200, default 25) and absolute next/previous links."],
                ["Errors", 'Always JSON: {"error": "…"} with status 400, 401, 404, 405 or 429.'],
                ["Caching", "Public endpoints send a weak ETag and Cache-Control: max-age=300; repeat requests with If-None-Match get 304 Not Modified."],
                [
                  "Rate limits",
                  `${data?.limits.api_public ?? "300/m"} public and ${data?.limits.api_token ?? "120/m"} token requests per client, reported in X-RateLimit-* headers; 429 responses include Retry-After.`,
                ],
                ["CORS", "Public read-only endpoints allow any origin. Token endpoints do not — call them from a server."],
                ["Times", "ISO 8601 in UTC. Each cycle states whether its official cut-off is AoE (UTC−12) or UTC, and whether the dates are projected."],
              ].map(([t, d]) => (
                <div key={t} className="rounded-xl border bg-card p-4 shadow-card">
                  <dt className="font-semibold">{t}</dt>
                  <dd className="mt-1 text-sm leading-6 text-muted-foreground">{d}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section id="endpoints" aria-labelledby="ep-h" className="scroll-mt-20 space-y-6">
            <h2 id="ep-h" className="text-xl font-semibold tracking-tight">
              Endpoints
            </h2>
            {!data ? (
              <Skeleton className="h-64 w-full rounded-xl" />
            ) : (
              data.groups.map((g) => (
                <Card key={g.title}>
                  <CardHeader>
                    <CardTitle as="h3">{g.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="overflow-x-auto">
                    <table className="w-full min-w-[560px] text-sm">
                      <thead className="text-left text-xs text-muted-foreground">
                        <tr className="border-b">
                          <th scope="col" className="w-20 py-2 font-medium">
                            Method
                          </th>
                          <th scope="col" className="py-2 font-medium">
                            Path
                          </th>
                          <th scope="col" className="py-2 font-medium">
                            Description
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {g.endpoints.map((e) => (
                          <tr key={e.method + e.path}>
                            <td className="py-2.5">
                              <Badge tone={e.method === "GET" ? "green" : e.method === "POST" ? "blue" : "red"} className="font-mono">
                                {e.method}
                              </Badge>
                            </td>
                            <td className="py-2.5 pr-4 font-mono text-[13px]">{e.path}</td>
                            <td className="py-2.5 text-muted-foreground">{e.description}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </CardContent>
                </Card>
              ))
            )}
          </section>

          <section id="filters" aria-labelledby="fp-h" className="scroll-mt-20">
            <Card>
              <CardHeader>
                <CardTitle as="h2" className="text-xl" id="fp-h">
                  Filter parameters
                </CardTitle>
                <CardDescription>
                  Accepted by <code className="font-mono">/api/venues/</code>, the CSV/JSON exports and the calendar/Atom feeds. Repeat a parameter to OR
                  values, e.g. <code className="font-mono">?core=A*&amp;core=A</code>.
                </CardDescription>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="text-left text-xs text-muted-foreground">
                    <tr className="border-b">
                      <th scope="col" className="py-2 font-medium">
                        Parameter
                      </th>
                      <th scope="col" className="py-2 font-medium">
                        Type
                      </th>
                      <th scope="col" className="py-2 font-medium">
                        Description
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {(data?.filters ?? []).map((f) => (
                      <tr key={f.name}>
                        <td className="py-2.5 pr-4 font-mono text-[13px] font-semibold">{f.name}</td>
                        <td className="py-2.5 pr-4 text-muted-foreground">{f.type}</td>
                        <td className="py-2.5">{f.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </section>

          <section id="auth" aria-labelledby="auth-h" className="scroll-mt-20">
            <h2 id="auth-h" className="mb-3 text-xl font-semibold tracking-tight">
              Authentication
            </h2>
            <p className="max-w-3xl text-[15px] leading-7 text-muted-foreground">
              Personal endpoints under <code className="font-mono text-foreground">/api/v1/me/</code> require{" "}
              <code className="font-mono text-foreground">Authorization: Bearer &lt;token&gt;</code>. Find or regenerate your token on your{" "}
              <Link to="/accounts/profile/#api" className="link">
                profile
              </Link>
              ; regenerating revokes the old one immediately. Requests without a valid token get 401 with a{" "}
              <code className="font-mono text-foreground">WWW-Authenticate</code> header.
            </p>
          </section>
        </div>
      </div>
    </PageContainer>
  );
}
