import { Link } from "react-router-dom";

import { LogoMark } from "./logo";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { to: "/", label: "Explore venues" },
      { to: "/recommend/", label: "Recommender" },
      { to: "/plan/", label: "Deadline planner" },
      { to: "/insights/", label: "Insights" },
      { to: "/community/changes/", label: "Deadline radar" },
    ],
  },
  {
    title: "Your research",
    links: [
      { to: "/targets/", label: "My targets" },
      { to: "/tracker/", label: "Submission tracker" },
      { to: "/accounts/lists/", label: "Venue lists" },
      { to: "/accounts/", label: "Dashboard" },
    ],
  },
  {
    title: "Developers",
    links: [
      { to: "/api/docs/", label: "API documentation" },
      { href: "/api/openapi.json", label: "OpenAPI schema" },
      { href: "/feed/deadlines.atom", label: "Atom feed" },
      { href: "/calendar.ics", label: "iCal feed" },
    ],
  },
  {
    title: "VenuePulse",
    links: [
      { to: "/about/", label: "About & FAQ" },
      { to: "/privacy/", label: "Privacy" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t bg-surface">
      <div className="mx-auto grid max-w-screen-2xl gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1.2fr_2fr] lg:px-8">
        <div className="max-w-sm">
          <div className="flex items-center gap-2.5 font-semibold">
            <LogoMark />
            VenuePulse
          </div>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            Deadlines, ranks and submission rules for research conferences and journals worldwide — with live countdowns in your timezone and AoE.
          </p>
          <p className="mt-4 text-xs leading-5 text-muted-foreground">
            Dates marked <em>projected</em> are extrapolated from previous editions. Always confirm on the official call for papers.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground">{col.title}</h2>
              <ul className="mt-3 space-y-2">
                {col.links.map((l) => (
                  <li key={l.label}>
                    {"to" in l && l.to ? (
                      <Link to={l.to} className="text-sm text-muted-foreground transition-colors hover:text-foreground">
                        {l.label}
                      </Link>
                    ) : (
                      <a href={(l as { href: string }).href} className="text-sm text-muted-foreground transition-colors hover:text-foreground">
                        {l.label}
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="border-t">
        <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-muted-foreground sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} VenuePulse. Metrics compiled from CORE, CCF, Google Scholar, JCR and Scopus.</p>
          <p>
            Press <kbd className="rounded border bg-background px-1 font-sans">/</kbd> to search
          </p>
        </div>
      </div>
    </footer>
  );
}
