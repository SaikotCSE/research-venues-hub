import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  BookOpen,
  CalendarRange,
  Clock,
  Code2,
  Compass,
  GitCompareArrows,
  KanbanSquare,
  LayoutDashboard,
  LogIn,
  Moon,
  Radar,
  Sparkles,
  Star,
  Sun,
  UserPlus,
} from "lucide-react";
import * as React from "react";
import { useNavigate } from "react-router-dom";

import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator } from "@/components/ui/command";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { VenueMark } from "@/components/venue/venue-mark";
import { useDebounced } from "@/hooks/use-debounce";
import { api } from "@/lib/api";
import { recentVenues } from "@/lib/recent";
import { useCompare } from "@/providers/compare";
import { usePalette } from "@/providers/palette";
import { useSession } from "@/providers/session";
import { useTheme } from "@/providers/theme";

interface Suggestion {
  acronym: string;
  name: string;
  type: string;
  url: string;
  flag: string;
}

const PAGES = [
  { to: "/", label: "Explore venues", icon: Compass, keywords: ["search", "browse", "home"] },
  { to: "/recommend/", label: "Recommend venues for my paper", icon: Sparkles, keywords: ["abstract", "match"] },
  { to: "/plan/", label: "Plan around a ready date", icon: CalendarRange, keywords: ["planner", "deadline"] },
  { to: "/insights/", label: "Insights & charts", icon: BarChart3, keywords: ["statistics"] },
  { to: "/targets/", label: "My target venues", icon: Star, keywords: ["starred", "bookmarks"] },
  { to: "/community/changes/", label: "Deadline radar", icon: Radar, keywords: ["extensions", "changes"] },
  { to: "/api/docs/", label: "API documentation", icon: Code2, keywords: ["developer", "json"] },
  { to: "/about/", label: "About & FAQ", icon: BookOpen, keywords: ["help", "aoe"] },
];

export function CommandPalette() {
  const { open, setOpen } = usePalette();
  const [query, setQuery] = React.useState("");
  const debounced = useDebounced(query.trim(), 150);
  const navigate = useNavigate();
  const session = useSession();
  const { resolved, setTheme } = useTheme();
  const compare = useCompare();

  const { data, isFetching } = useQuery({
    queryKey: ["suggest", debounced],
    queryFn: () => api.get<{ results: Suggestion[] }>("/api/suggest/", { q: debounced }),
    enabled: open && debounced.length > 0,
    staleTime: 5 * 60_000,
    placeholderData: (prev) => prev,
  });

  React.useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const go = (to: string) => {
    setOpen(false);
    navigate(to);
  };
  const recent = open && !debounced ? recentVenues() : [];
  const venues = debounced ? (data?.results ?? []) : [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="top-[12%] max-w-xl translate-y-0 gap-0 overflow-hidden p-0 sm:top-[15%]" hideClose>
        <DialogTitle className="sr-only">Search VenuePulse</DialogTitle>
        <DialogDescription className="sr-only">Search venues by acronym or name, jump to a page or run an action.</DialogDescription>
        <Command loop>
          <CommandInput value={query} onValueChange={setQuery} placeholder="Search venues, pages and actions…" aria-label="Search venues, pages and actions" />
          <CommandList>
            <CommandEmpty>{isFetching ? "Searching…" : "No results. Try an acronym like “NeurIPS” or a topic on the Explore page."}</CommandEmpty>
            {venues.length > 0 && (
              <CommandGroup heading="Venues">
                {venues.map((v) => (
                  <CommandItem key={v.url} value={`venue ${v.acronym} ${v.name}`} keywords={[v.acronym, v.name]} onSelect={() => go(v.url)}>
                    <VenueMark acronym={v.acronym} size="sm" />
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium">{v.acronym}</span>
                      <span className="block truncate text-xs text-muted-foreground">{v.name}</span>
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {v.flag} {v.type === "Workshop/Symposium" ? "Symposium" : v.type}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {debounced && (
              <CommandGroup heading="Search">
                <CommandItem value={`search catalogue for ${debounced}`} onSelect={() => go(`/?q=${encodeURIComponent(debounced)}`)}>
                  <Compass aria-hidden="true" />
                  Search the catalogue for “{debounced}”
                </CommandItem>
                <CommandItem value={`recommend venues for ${debounced}`} onSelect={() => go(`/recommend/?text=${encodeURIComponent(debounced)}`)}>
                  <Sparkles aria-hidden="true" />
                  Recommend venues for “{debounced}”
                </CommandItem>
              </CommandGroup>
            )}
            {recent.length > 0 && (
              <CommandGroup heading="Recently viewed">
                {recent.map((v) => (
                  <CommandItem key={v.slug} value={`recent ${v.acronym} ${v.name}`} onSelect={() => go(`/venue/${v.slug}/`)}>
                    <Clock aria-hidden="true" />
                    <span className="font-medium">{v.acronym}</span>
                    <span className="truncate text-muted-foreground">{v.name}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            <CommandGroup heading="Pages">
              {PAGES.map((p) => (
                <CommandItem key={p.to} value={p.label} keywords={p.keywords} onSelect={() => go(p.to)}>
                  <p.icon aria-hidden="true" />
                  {p.label}
                </CommandItem>
              ))}
              {session.authenticated && (
                <>
                  <CommandItem value="Dashboard" onSelect={() => go("/accounts/")}>
                    <LayoutDashboard aria-hidden="true" />
                    Dashboard
                  </CommandItem>
                  <CommandItem value="Submission tracker" keywords={["kanban", "papers"]} onSelect={() => go("/tracker/")}>
                    <KanbanSquare aria-hidden="true" />
                    Submission tracker
                  </CommandItem>
                </>
              )}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Actions">
              <CommandItem
                value="Toggle dark mode theme"
                onSelect={() => {
                  setTheme(resolved === "dark" ? "light" : "dark");
                  setOpen(false);
                }}
              >
                {resolved === "dark" ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
                Switch to {resolved === "dark" ? "light" : "dark"} mode
              </CommandItem>
              {compare.items.length > 1 && (
                <CommandItem value="Compare selected venues" onSelect={() => go(`/compare/?${compare.items.map((i) => `s=${i.slug}`).join("&")}`)}>
                  <GitCompareArrows aria-hidden="true" />
                  Compare {compare.items.map((i) => i.acronym).join(", ")}
                </CommandItem>
              )}
              {!session.authenticated && (
                <>
                  <CommandItem value="Log in" onSelect={() => go("/accounts/login/")}>
                    <LogIn aria-hidden="true" />
                    Log in
                  </CommandItem>
                  <CommandItem value="Create account sign up" onSelect={() => go("/accounts/signup/")}>
                    <UserPlus aria-hidden="true" />
                    Create a free account
                  </CommandItem>
                </>
              )}
            </CommandGroup>
          </CommandList>
          <div className="flex items-center gap-3 border-t px-3 py-2 text-[11px] text-muted-foreground">
            <span>
              <kbd className="font-sans">↑↓</kbd> to navigate
            </span>
            <span>
              <kbd className="font-sans">↵</kbd> to select
            </span>
            <span>
              <kbd className="font-sans">esc</kbd> to close
            </span>
          </div>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
