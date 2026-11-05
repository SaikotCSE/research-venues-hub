import { useMutation } from "@tanstack/react-query";
import { FileText, KanbanSquare, LayoutDashboard, List, LogOut, Settings, Shield, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api";
import type { Session } from "@/lib/types";
import { useResetAfterAuth } from "@/providers/session";

export function UserMenu({ session }: { session: Session }) {
  const navigate = useNavigate();
  const reset = useResetAfterAuth();
  const logout = useMutation({
    mutationFn: () => api.post<Session>("/auth/logout/"),
    onSuccess: (s) => {
      reset(s);
      toast.success("You're signed out");
      navigate("/");
    },
  });
  const user = session.user!;
  const links = [
    { to: "/accounts/", label: "Dashboard", icon: LayoutDashboard },
    { to: "/tracker/", label: "Submission tracker", icon: KanbanSquare },
    { to: "/tracker/papers/", label: "My papers", icon: FileText },
    { to: "/accounts/lists/", label: "My lists", icon: List },
    { to: "/accounts/profile/", label: "Profile", icon: User },
    { to: "/accounts/settings/", label: "Account settings", icon: Settings },
  ];
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" className="rounded-full" aria-label={`Account menu for ${user.name}`}>
          <Avatar initials={user.initials} className="size-7" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="flex items-center gap-3 py-2">
          <Avatar initials={user.initials} />
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-foreground">{user.name}</span>
            <span className="block truncate text-xs font-normal">{user.email || user.username}</span>
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {links.map((l) => (
          <DropdownMenuItem key={l.to} asChild>
            <Link to={l.to}>
              <l.icon aria-hidden="true" />
              {l.label}
            </Link>
          </DropdownMenuItem>
        ))}
        {session.admin_url && (
          <DropdownMenuItem asChild>
            <a href={session.admin_url}>
              <Shield aria-hidden="true" />
              Admin
            </a>
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => logout.mutate()}>
          <LogOut aria-hidden="true" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
