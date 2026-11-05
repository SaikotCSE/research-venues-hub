import { BellRing, CalendarClock, Globe2, KanbanSquare } from "lucide-react";
import * as React from "react";

import { LogoMark } from "@/components/layout/logo";
import { useDocumentTitle } from "@/hooks/use-document-title";

const POINTS = [
  { icon: Globe2, text: "Deadlines in your timezone and AoE, ticking live" },
  { icon: BellRing, text: "Email reminders before abstract and paper deadlines" },
  { icon: CalendarClock, text: "Add any deadline to your calendar in one click" },
  { icon: KanbanSquare, text: "A submission board with venue-specific checklists" },
];

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  useDocumentTitle(title);
  return (
    <div className="mx-auto grid max-w-6xl gap-10 px-4 py-10 sm:px-6 lg:grid-cols-2 lg:gap-16 lg:py-16">
      <div className="relative hidden overflow-hidden rounded-3xl border bg-gradient-to-br from-indigo-600 via-violet-600 to-indigo-800 p-10 text-white shadow-lift lg:flex lg:flex-col">
        <div className="bg-grid pointer-events-none absolute inset-0 opacity-[0.12] [--border:0_0%_100%]" aria-hidden="true" />
        <div className="relative flex items-center gap-2.5 font-semibold">
          <LogoMark className="bg-white/15 from-white/20 to-white/5 shadow-none ring-1 ring-white/25" />
          VenuePulse
        </div>
        <h2 className="relative mt-auto text-3xl font-semibold leading-tight tracking-tight">Never miss a call for papers again.</h2>
        <ul className="relative mt-6 space-y-3">
          {POINTS.map((p) => (
            <li key={p.text} className="flex items-center gap-3 text-[15px] text-white/90">
              <span className="grid size-8 place-items-center rounded-lg bg-white/10 ring-1 ring-white/20">
                <p.icon className="size-4" aria-hidden="true" />
              </span>
              {p.text}
            </li>
          ))}
        </ul>
        <p className="relative mt-10 text-sm text-white/70">Free for researchers. Your stars and notes from this browser carry over when you sign up.</p>
      </div>
      <div className="flex flex-col justify-center">
        <div className="mx-auto w-full max-w-sm">
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-8 border-t pt-6 text-center text-sm text-muted-foreground">{footer}</div>}
        </div>
      </div>
    </div>
  );
}

export function useNextParam(fallback: string) {
  const params = new URLSearchParams(window.location.search);
  const next = params.get("next");
  return next && next.startsWith("/") && !next.startsWith("//") ? next : fallback;
}

export function goTo(navigate: (to: string) => void, url: string) {
  if (url.startsWith("/") && !url.startsWith("//")) navigate(url);
  else window.location.assign(url);
}
