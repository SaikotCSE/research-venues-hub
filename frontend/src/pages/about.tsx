import { BellRing, CalendarCheck2, Code2, Globe2, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { PageContainer } from "@/components/common/page";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useDocumentTitle } from "@/hooks/use-document-title";

const FEATURES = [
  {
    icon: Globe2,
    title: "Every deadline in your timezone",
    text: "Exact instants, shown in your zone and in Anywhere-on-Earth time — no more mental arithmetic at 3 a.m.",
  },
  {
    icon: ShieldCheck,
    title: "Projected vs. verified",
    text: "Dates extrapolated from earlier editions are clearly labelled until an editor checks them against the official call.",
  },
  {
    icon: BellRing,
    title: "Reminders that respect you",
    text: "Email reminders before abstract and paper deadlines, a weekly digest, and alerts when a tracked deadline moves.",
  },
  {
    icon: CalendarCheck2,
    title: "Calendar-native",
    text: "Subscribe to a private iCal feed of your targets, a public feed for any filter, or add single deadlines to Google and Outlook.",
  },
  { icon: Sparkles, title: "Recommendations", text: "Paste an abstract and get venues ranked by topical fit, rank and how soon they close." },
  { icon: Code2, title: "Open data", text: "A documented JSON API, OpenAPI schema, CSV/JSON exports and Atom feeds — build on it freely." },
];

const FAQS: { q: string; a: React.ReactNode }[] = [
  {
    q: "What does “AoE” mean?",
    a: (
      <>
        <em>Anywhere on Earth</em> (UTC−12) is the latest time zone on the planet. A deadline of “23:59 AoE” has not passed as long as it is still that date{" "}
        <em>somewhere</em> — that is already the next day in Europe and Asia. VenuePulse stores every deadline as an exact instant and shows it in AoE{" "}
        <em>and</em> in your chosen timezone, so you never have to convert by hand.
      </>
    ),
  },
  {
    q: "Why are some dates marked “Projected”?",
    a: (
      <>
        Many venues announce their next call only a few months ahead. To help you plan, VenuePulse projects the next edition from the pattern of previous ones
        and labels those dates <strong>Projected</strong>. Once an editor checks the official call the cycle is marked <strong>Verified</strong>, with a link to
        the source. Always confirm on the official website before you submit.
      </>
    ),
  },
  {
    q: "How reliable are the ranks and metrics?",
    a: "They are compiled from public sources (the CORE portal, the CCF recommendation list, Google Scholar Metrics, Journal Citation Reports and Scopus) and are approximate — lists are revised every few years and metrics change annually. Use them as a guide, not a verdict on a venue’s quality.",
  },
  {
    q: "How do reminders work?",
    a: "Star a venue (or track a submission) and, once your email is confirmed, VenuePulse reminds you before each abstract and paper deadline — by default 14, 7 and 1 days before. You can change the offsets, switch emails off, or subscribe to a private calendar feed instead from your profile. If a tracked deadline moves, you get a notification too.",
  },
  {
    q: "Can I use VenuePulse without an account?",
    a: "Yes. Searching, filtering, comparing, exports, feeds and the API are open to everyone, and you can star venues and keep notes anonymously in your browser. Create a free account to sync them across devices and get reminders — your anonymous stars are kept.",
  },
  {
    q: "A date is wrong — how do I fix it?",
    a: (
      <>
        Open the venue page and choose <em>Correct</em> next to the edition (requires an account), with a link to the official call. Editors review suggestions;
        approved changes are logged on the public{" "}
        <Link className="link" to="/community/changes/">
          deadline radar
        </Link>
        .
      </>
    ),
  },
  {
    q: "Can I build on the data?",
    a: (
      <>
        Yes — see the{" "}
        <Link className="link" to="/api/docs/">
          API documentation
        </Link>{" "}
        for the JSON API, OpenAPI schema, CSV/JSON exports and iCal/Atom feeds. Public endpoints allow cross-origin requests, so you can embed live deadlines in
        your lab’s website.
      </>
    ),
  },
];

const METRICS = [
  ["CORE rank", "Australian CORE conference ranking, widely used in computer science hiring and funding.", "A* (flagship) · A · B · C"],
  ["CCF rank", "China Computer Federation recommended venues list.", "A · B · C"],
  ["h5-index", "Google Scholar: the largest h such that h papers from the last five years have at least h citations each.", "Higher is better"],
  ["h5-median", "Median citations of the papers that make up the h5-index.", "Higher is better"],
  ["Impact factor", "Journal Citation Reports: citations in a year to items published in the previous two years, per item.", "Field-dependent"],
  ["Quartile", "Where a journal’s impact sits within its subject category.", "Q1 (top 25%) – Q4"],
  ["CiteScore / SJR", "Scopus-based citation metrics; SJR weights citations by the prestige of the citing journal.", "Higher is better"],
  ["Acceptance rate", "Share of submitted papers accepted in recent editions.", "Lower = more selective"],
];

export function Component() {
  useDocumentTitle("About & FAQ");
  return (
    <>
      <section className="relative overflow-hidden border-b">
        <div className="bg-grid mask-fade pointer-events-none absolute inset-0 opacity-50" aria-hidden="true" />
        <div className="relative mx-auto max-w-4xl px-4 py-16 text-center sm:px-6">
          <p className="eyebrow">About VenuePulse</p>
          <h1 className="mt-3 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">Spend your time on the research, not on the deadlines.</h1>
          <p className="mx-auto mt-5 max-w-2xl text-pretty text-lg leading-8 text-muted-foreground">
            VenuePulse brings the calls for papers of leading conferences and journals into one fast, searchable place — with live countdowns, honest data
            provenance and the tools to plan a submission end to end.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button size="lg" asChild>
              <Link to="/">Explore venues</Link>
            </Button>
            <Button size="lg" variant="secondary" asChild>
              <Link to="/accounts/signup/">Create a free account</Link>
            </Button>
          </div>
        </div>
      </section>
      <PageContainer size="default">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title}>
              <CardContent className="p-5">
                <span className="grid size-9 place-items-center rounded-lg bg-brand-soft">
                  <f.icon className="size-[18px] text-brand-text" aria-hidden="true" />
                </span>
                <h2 className="mt-4 font-semibold">{f.title}</h2>
                <p className="mt-1.5 text-sm leading-6 text-muted-foreground">{f.text}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-16 grid gap-12 lg:grid-cols-[1fr_1.4fr]">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">Frequently asked questions</h2>
            <p className="mt-2 text-muted-foreground">
              Something else? The{" "}
              <Link to="/api/docs/" className="link">
                API docs
              </Link>{" "}
              cover the data model in detail.
            </p>
          </div>
          <Accordion type="single" collapsible className="rounded-xl border bg-card px-5 shadow-card">
            {FAQS.map((f, i) => (
              <AccordionItem key={f.q} value={`faq-${i}`}>
                <AccordionTrigger>{f.q}</AccordionTrigger>
                <AccordionContent>{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>

        <section className="mt-16" aria-labelledby="metrics-h">
          <h2 id="metrics-h" className="text-2xl font-semibold tracking-tight">
            Metrics glossary
          </h2>
          <div className="mt-6 overflow-hidden rounded-xl border bg-card shadow-card">
            <dl className="divide-y">
              {METRICS.map(([name, desc, scale]) => (
                <div key={name} className="grid gap-1 px-5 py-4 sm:grid-cols-[10rem_1fr_12rem] sm:gap-6">
                  <dt className="font-semibold">{name}</dt>
                  <dd className="text-sm leading-6 text-muted-foreground">{desc}</dd>
                  <dd className="text-sm font-medium sm:text-right">{scale}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>
      </PageContainer>
    </>
  );
}
