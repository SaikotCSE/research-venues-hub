import { BarChart3, CalendarRange, Compass, KanbanSquare, Sparkles, Star, type LucideIcon } from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
  auth?: boolean;
}

export const NAV: NavItem[] = [
  { to: "/", label: "Explore", icon: Compass, end: true },
  { to: "/recommend/", label: "Recommend", icon: Sparkles },
  { to: "/plan/", label: "Planner", icon: CalendarRange },
  { to: "/insights/", label: "Insights", icon: BarChart3 },
  { to: "/targets/", label: "Targets", icon: Star },
  { to: "/tracker/", label: "Tracker", icon: KanbanSquare, auth: true },
];
