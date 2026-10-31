import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellRing, CalendarClock, CheckCheck, Search, Send, Shuffle } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, PageContainer, PageHeader } from "@/components/common/page";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useDocumentTitle } from "@/hooks/use-document-title";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { formatDateTime, relativeTime } from "@/lib/time";
import type { Notification, Session } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useTimeZone } from "@/providers/timezone";

const ICONS: Record<string, typeof Bell> = { deadline: CalendarClock, change: Shuffle, search: Search, submission: Send, system: BellRing };

export function Component() {
  useDocumentTitle("Notifications");
  const qc = useQueryClient();
  const { timeZone } = useTimeZone();
  const [filter, setFilter] = React.useState("all");
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: keys.notifications,
    queryFn: () => api.get<{ results: Notification[]; unread_count: number }>("/me/notifications/"),
  });
  const read = useMutation({
    mutationFn: (ids?: number[]) => api.post<{ unread_count: number }>("/me/notifications/read/", ids ? { ids } : {}),
    onSuccess: (r) => {
      qc.setQueryData<Session>(keys.session, (old) => (old ? { ...old, unread_count: r.unread_count } : old));
      qc.invalidateQueries({ queryKey: keys.notifications });
      qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
  const items = (data?.results ?? []).filter((n) => filter === "all" || (filter === "unread" ? !n.read : n.kind === filter));
  return (
    <PageContainer size="narrow">
      <PageHeader
        icon={Bell}
        title="Notifications"
        description="Deadline reminders, date changes for venues you track, and saved-search matches."
        actions={
          <Button variant="secondary" size="sm" onClick={() => read.mutate(undefined)} disabled={!data?.unread_count} loading={read.isPending}>
            <CheckCheck aria-hidden="true" /> Mark all read
          </Button>
        }
      />
      <ToggleGroup type="single" value={filter} onValueChange={(v) => v && setFilter(v)} className="mb-4" aria-label="Filter notifications">
        <ToggleGroupItem value="all">All</ToggleGroupItem>
        <ToggleGroupItem value="unread">Unread{data?.unread_count ? ` (${data.unread_count})` : ""}</ToggleGroupItem>
        <ToggleGroupItem value="deadline">Reminders</ToggleGroupItem>
        <ToggleGroupItem value="change">Changes</ToggleGroupItem>
        <ToggleGroupItem value="search">Searches</ToggleGroupItem>
      </ToggleGroup>
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <Skeleton className="h-72 w-full rounded-xl" />
      ) : items.length === 0 ? (
        <EmptyState
          icon={Bell}
          title={filter === "all" ? "No notifications yet" : "Nothing here"}
          description="Star venues and confirm your email to get reminders before their deadlines."
        />
      ) : (
        <ul className="divide-y rounded-xl border bg-card shadow-card">
          {items.map((n) => {
            const Icon = ICONS[n.kind] ?? Bell;
            return (
              <li key={n.id} className={cn("flex gap-4 p-4", !n.read && "bg-brand-soft/40")}>
                <span className="grid size-9 shrink-0 place-items-center rounded-lg border bg-card">
                  <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  {n.url ? (
                    <Link
                      to={n.url}
                      className={cn("text-sm leading-6 hover:text-brand-text", !n.read && "font-medium")}
                      onClick={() => !n.read && read.mutate([n.id])}
                    >
                      {n.message}
                    </Link>
                  ) : (
                    <p className={cn("text-sm leading-6", !n.read && "font-medium")}>{n.message}</p>
                  )}
                  <p className="mt-0.5 text-xs text-muted-foreground" title={formatDateTime(n.created_at, timeZone)}>
                    {n.kind_label} · {relativeTime(n.created_at)}
                  </p>
                </div>
                {!n.read && (
                  <Button variant="ghost" size="xs" onClick={() => read.mutate([n.id])} aria-label="Mark as read">
                    <CheckCheck aria-hidden="true" />
                  </Button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </PageContainer>
  );
}
