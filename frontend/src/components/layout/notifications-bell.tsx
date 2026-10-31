import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import * as React from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";
import { keys } from "@/lib/query";
import { relativeTime } from "@/lib/time";
import type { Notification, Session } from "@/lib/types";
import { cn } from "@/lib/utils";

export function NotificationsBell({ unread }: { unread: number }) {
  const [open, setOpen] = React.useState(false);
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: keys.notifications,
    queryFn: () => api.get<{ results: Notification[]; unread_count: number }>("/me/notifications/"),
    enabled: open,
  });
  const markRead = useMutation({
    mutationFn: () => api.post<{ unread_count: number }>("/me/notifications/read/"),
    onSuccess: (res) => {
      qc.setQueryData<Session>(keys.session, (old) => (old ? { ...old, unread_count: res.unread_count } : old));
      qc.invalidateQueries({ queryKey: keys.notifications });
      qc.invalidateQueries({ queryKey: keys.dashboard });
    },
  });
  const items = data?.results.slice(0, 6) ?? [];
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon-sm" className="relative" aria-label={unread ? `Notifications, ${unread} unread` : "Notifications"}>
          <Bell aria-hidden="true" />
          {unread > 0 && (
            <span className="tnum absolute -right-0.5 -top-0.5 grid h-4 min-w-4 place-items-center rounded-full bg-rose-500 px-1 text-[10px] font-bold leading-none text-white ring-2 ring-background">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[22rem] p-0">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <p className="text-sm font-semibold">Notifications</p>
          <Button variant="ghost" size="xs" onClick={() => markRead.mutate()} disabled={!unread || markRead.isPending}>
            <CheckCheck aria-hidden="true" /> Mark all read
          </Button>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {isLoading ? (
            <p className="px-4 py-8 text-center text-sm text-muted-foreground">Loading…</p>
          ) : items.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <Bell className="mx-auto size-6 text-muted-foreground/60" aria-hidden="true" />
              <p className="mt-2 text-sm font-medium">You're all caught up</p>
              <p className="text-xs text-muted-foreground">Reminders and deadline changes for your targets show up here.</p>
            </div>
          ) : (
            <ul className="divide-y">
              {items.map((n) => (
                <li key={n.id}>
                  <Link
                    to={n.url || "/accounts/notifications/"}
                    onClick={() => setOpen(false)}
                    className="flex gap-3 px-4 py-3 text-sm transition-colors hover:bg-accent"
                  >
                    <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", n.read ? "bg-transparent" : "bg-primary")} aria-hidden="true" />
                    <span className="min-w-0 flex-1">
                      <span className={cn("block leading-5", !n.read && "font-medium")}>{n.message}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {n.kind_label} · {relativeTime(n.created_at)}
                      </span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="border-t p-2">
          <Button variant="ghost" size="sm" className="w-full" asChild>
            <Link to="/accounts/notifications/" onClick={() => setOpen(false)}>
              View all notifications
            </Link>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
