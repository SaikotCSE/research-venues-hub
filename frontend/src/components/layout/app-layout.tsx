import { useMutation } from "@tanstack/react-query";
import { MailWarning } from "lucide-react";
import * as React from "react";
import { Outlet, ScrollRestoration, useLocation } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { api, errorMessage } from "@/lib/api";
import { boot } from "@/lib/boot";
import { NotFoundPage } from "@/pages/not-found";
import { usePalette } from "@/providers/palette";
import { useSession } from "@/providers/session";

const CommandPalette = React.lazy(() => import("./command-palette").then((m) => ({ default: m.CommandPalette })));

/** The palette (cmdk + dialog) is only downloaded the first time someone opens it. */
function LazyPalette() {
  const { open } = usePalette();
  const [wanted, setWanted] = React.useState(false);
  React.useEffect(() => {
    if (open) setWanted(true);
  }, [open]);
  if (!wanted) return null;
  return (
    <React.Suspense fallback={null}>
      <CommandPalette />
    </React.Suspense>
  );
}

import { CompareTray } from "./compare-tray";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";

function VerifyEmailBanner() {
  const resend = useMutation({
    mutationFn: () => api.post<{ message: string }>("/auth/verify-email/resend/"),
    onSuccess: (r) => toast.success(r.message),
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <div className="border-b border-amber-200/70 bg-amber-50 text-amber-900 dark:border-amber-400/15 dark:bg-amber-400/[0.07] dark:text-amber-200">
      <div className="mx-auto flex max-w-screen-2xl flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2 text-sm sm:px-6 lg:px-8">
        <MailWarning className="size-4 shrink-0" aria-hidden="true" />
        <p className="flex-1">Confirm your email address to receive deadline reminders and weekly digests.</p>
        <Button
          size="xs"
          variant="ghost"
          className="text-current hover:bg-amber-100 dark:hover:bg-amber-400/10"
          onClick={() => resend.mutate()}
          loading={resend.isPending}
        >
          Resend link
        </Button>
      </div>
    </div>
  );
}

/** Announce route changes to screen readers and move focus to the new page's main region. */
function useRouteFocus() {
  const location = useLocation();
  const first = React.useRef(true);
  React.useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const main = document.getElementById("main");
    main?.focus({ preventScroll: true });
  }, [location.pathname]);
}

export function AppLayout() {
  const session = useSession();
  const location = useLocation();
  useRouteFocus();

  React.useEffect(() => {
    // Flash messages set by server-side redirects (e.g. the email verification link).
    for (const m of boot.session.messages) {
      if (m.level === "error") toast.error(m.text);
      else toast.success(m.text);
    }
  }, []);

  // The server answered 404 for the URL the app booted on (unknown venue, private list…).
  const serverNotFound = boot.status === 404 && location.key === "default";

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only z-[80] rounded-lg bg-primary px-4 py-2 text-primary-foreground focus:not-sr-only focus:fixed focus:left-4 focus:top-3">
        Skip to content
      </a>
      <SiteHeader />
      {session.authenticated && session.user && session.user.email && !session.user.email_verified && <VerifyEmailBanner />}
      <main id="main" tabIndex={-1} className="flex-1 outline-none">
        {serverNotFound ? <NotFoundPage what={boot.extra.not_found} /> : <Outlet />}
      </main>
      <SiteFooter />
      <CompareTray />
      <LazyPalette />
      <ScrollRestoration getKey={(loc) => loc.pathname} />
    </div>
  );
}
