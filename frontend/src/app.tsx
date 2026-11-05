import { QueryClientProvider } from "@tanstack/react-query";
import { Outlet, RouterProvider, createBrowserRouter, useNavigation } from "react-router-dom";
import { Toaster } from "sonner";

import { AppLayout } from "@/components/layout/app-layout";
import { SiteHeader } from "@/components/layout/site-header";
import { RequireAuth } from "@/components/common/require-auth";
import { TooltipProvider } from "@/components/ui/tooltip";
import { queryClient } from "@/lib/query";
import { NotFoundPage } from "@/pages/not-found";
import { CompareProvider } from "@/providers/compare";
import { PaletteProvider } from "@/providers/palette";
import { TimezoneProvider } from "@/providers/timezone";
import { ThemeProvider, useTheme } from "@/providers/theme";

function NavigationProgress() {
  const navigation = useNavigation();
  if (navigation.state === "idle") return null;
  return (
    <div className="fixed inset-x-0 top-0 z-[70] h-0.5 overflow-hidden" role="progressbar" aria-label="Loading page">
      <div className="h-full w-1/3 animate-[shimmer_1s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-primary to-transparent" />
    </div>
  );
}

function Root() {
  return (
    <>
      <NavigationProgress />
      <AppLayout />
    </>
  );
}

/** Shown while the first page chunk (preloaded by the Django shell) is evaluated: same chrome, empty body. */
function BootFallback() {
  return (
    <div className="flex min-h-screen flex-col" aria-busy="true">
      <SiteHeader />
      <main className="flex-1" />
    </div>
  );
}

function Guarded() {
  return (
    <RequireAuth>
      <Outlet />
    </RequireAuth>
  );
}

const page = (load: () => Promise<{ Component: React.ComponentType }>) => ({ lazy: load });

export const router = createBrowserRouter([
  {
    element: <Root />,
    HydrateFallback: BootFallback,
    children: [
      { index: true, ...page(() => import("@/pages/explore")) },
      { path: "venue/:slug", ...page(() => import("@/pages/venue-detail")) },
      { path: "compare", ...page(() => import("@/pages/compare")) },
      { path: "targets", ...page(() => import("@/pages/targets")) },
      { path: "recommend", ...page(() => import("@/pages/recommend")) },
      { path: "plan", ...page(() => import("@/pages/plan")) },
      { path: "insights", ...page(() => import("@/pages/insights")) },
      { path: "community/changes", ...page(() => import("@/pages/radar")) },
      { path: "about", ...page(() => import("@/pages/about")) },
      { path: "privacy", ...page(() => import("@/pages/privacy")) },
      { path: "api/docs", ...page(() => import("@/pages/api-docs")) },
      { path: "accounts/login", ...page(() => import("@/pages/auth/login")) },
      { path: "accounts/signup", ...page(() => import("@/pages/auth/signup")) },
      { path: "accounts/password/reset", ...page(() => import("@/pages/auth/password-reset")) },
      { path: "accounts/password/reset/complete", ...page(() => import("@/pages/auth/password-reset-complete")) },
      { path: "accounts/lists/:slug", ...page(() => import("@/pages/account/list-detail")) },
      {
        element: <Guarded />,
        children: [
          { path: "accounts", ...page(() => import("@/pages/account/dashboard")) },
          { path: "accounts/profile", ...page(() => import("@/pages/account/profile")) },
          { path: "accounts/settings", ...page(() => import("@/pages/account/settings")) },
          { path: "accounts/password/change", ...page(() => import("@/pages/auth/password-change")) },
          { path: "accounts/notifications", ...page(() => import("@/pages/account/notifications")) },
          { path: "accounts/lists", ...page(() => import("@/pages/account/lists")) },
          { path: "tracker", ...page(() => import("@/pages/tracker/board")) },
          { path: "tracker/new", ...page(() => import("@/pages/tracker/new")) },
          { path: "tracker/s/:id", ...page(() => import("@/pages/tracker/detail")) },
          { path: "tracker/papers", ...page(() => import("@/pages/tracker/papers")) },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

/** Resolves once the first route (and its lazily loaded page chunk) is ready to render. */
export function routerReady() {
  if (router.state.initialized) return Promise.resolve();
  return new Promise<void>((resolve) => {
    const unsubscribe = router.subscribe((state) => {
      if (state.initialized) {
        unsubscribe();
        resolve();
      }
    });
  });
}

function ThemedToaster() {
  const { resolved } = useTheme();
  return <Toaster theme={resolved} position="bottom-right" richColors closeButton toastOptions={{ classNames: { toast: "font-sans" } }} />;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TimezoneProvider>
          <CompareProvider>
            <PaletteProvider>
              <TooltipProvider delayDuration={300}>
                <RouterProvider router={router} />
                <ThemedToaster />
              </TooltipProvider>
            </PaletteProvider>
          </CompareProvider>
        </TimezoneProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
