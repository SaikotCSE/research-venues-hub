import { Menu, Search } from "lucide-react";
import * as React from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Kbd } from "@/components/ui/kbd";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { usePalette } from "@/providers/palette";
import { useSession } from "@/providers/session";

import { Logo } from "./logo";
import { NAV } from "./nav-links";
import { NotificationsBell } from "./notifications-bell";
import { ThemeToggle } from "./theme-toggle";
import { TimezonePicker } from "./timezone-picker";
import { UserMenu } from "./user-menu";

const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform);

export function SiteHeader() {
  const session = useSession();
  const palette = usePalette();
  const [menuOpen, setMenuOpen] = React.useState(false);
  const location = useLocation();
  React.useEffect(() => setMenuOpen(false), [location.pathname]);
  const links = NAV.filter((n) => !n.auth || session.authenticated);

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 max-w-screen-2xl items-center gap-2 px-4 sm:px-6 lg:px-8">
        <Button variant="ghost" size="icon-sm" className="-ml-1.5 lg:hidden" onClick={() => setMenuOpen(true)} aria-label="Open menu">
          <Menu aria-hidden="true" />
        </Button>
        <Logo className="mr-2 max-[380px]:[&>span:last-child]:hidden" />
        <nav aria-label="Primary" className="hidden items-center gap-0.5 lg:flex">
          {links.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground",
                  isActive && "text-foreground after:absolute after:inset-x-2.5 after:-bottom-[11px] after:h-0.5 after:rounded-full after:bg-primary",
                )
              }
            >
              {item.label}
              {item.to === "/targets/" && session.target_count > 0 && (
                <span className="tnum rounded-full bg-muted px-1.5 text-[10px] font-semibold leading-4 text-muted-foreground">{session.target_count}</span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <button
            type="button"
            onClick={() => palette.setOpen(true)}
            className="hidden h-8 w-56 items-center gap-2 rounded-lg border border-input bg-background px-2.5 text-[13px] text-muted-foreground shadow-sm shadow-black/[0.02] transition-colors hover:border-foreground/20 hover:text-foreground md:flex xl:w-64"
            aria-keyshortcuts="Control+K Meta+K"
          >
            <Search className="size-3.5" aria-hidden="true" />
            <span className="flex-1 text-left">Search venues…</span>
            <Kbd>{isMac ? "⌘" : "Ctrl"} K</Kbd>
          </button>
          <Button variant="ghost" size="icon-sm" className="md:hidden" onClick={() => palette.setOpen(true)} aria-label="Search">
            <Search aria-hidden="true" />
          </Button>
          <TimezonePicker className="max-sm:hidden" />
          <ThemeToggle />
          {session.authenticated ? (
            <>
              <NotificationsBell unread={session.unread_count} />
              <UserMenu session={session} />
            </>
          ) : (
            <div className="ml-1 flex items-center gap-1.5">
              <Button variant="ghost" size="sm" asChild className="max-sm:hidden">
                <Link to="/accounts/login/">Log in</Link>
              </Button>
              <Button size="sm" asChild>
                <Link to="/accounts/signup/">Sign up</Link>
              </Button>
            </div>
          )}
        </div>
      </div>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent side="left" className="gap-0 p-0">
          <SheetHeader className="border-b">
            <SheetTitle asChild>
              <div>
                <Logo />
              </div>
            </SheetTitle>
            <SheetDescription className="sr-only">Site navigation</SheetDescription>
          </SheetHeader>
          <nav aria-label="Mobile" className="flex flex-col gap-0.5 p-3">
            {links.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
                    isActive && "bg-accent text-foreground",
                  )
                }
              >
                <item.icon className="size-4" aria-hidden="true" />
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-auto border-t p-4">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Display timezone</p>
            <TimezonePicker className="w-full justify-start border" />
            {!session.authenticated && (
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Button variant="secondary" asChild>
                  <Link to="/accounts/login/">Log in</Link>
                </Button>
                <Button asChild>
                  <Link to="/accounts/signup/">Sign up</Link>
                </Button>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </header>
  );
}
