import { useState } from "react";
import {
  LayoutDashboard,
  Mic,
  Clock,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  PlusCircle,
  BrainCircuit,
} from "lucide-react";
import { twMerge } from "tailwind-merge";
import { Badge } from "./ui/badge";
import { useAuth } from "../context/AuthContext";
import type { Screen } from "../types";

interface SidebarProps {
  currentScreen: Screen;
  onNavigate: (screen: Screen) => void;
}

interface NavItem {
  icon: React.ElementType;
  label: string;
  screen: Screen;
  badge?: string;
}

const primaryNav: NavItem[] = [
  { icon: LayoutDashboard, label: "Dashboard", screen: "dashboard" },
  { icon: PlusCircle, label: "Practice", screen: "create-interview" },
  { icon: Clock, label: "History", screen: "results" },
  { icon: BarChart3, label: "Analytics", screen: "analytics" },
];



function getInitials(name?: string) {
  if (!name) return "U";
  const parts = name.trim().split(" ");
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

interface NavButtonProps {
  item: NavItem;
  active: boolean;
  collapsed: boolean;
  onClick: () => void;
}

function NavButton({ item, active, collapsed, onClick }: NavButtonProps) {
  const { icon: Icon, label, badge } = item;
  return (
    <button
      onClick={onClick}
      title={collapsed ? label : undefined}
      aria-current={active ? "page" : undefined}
      className={twMerge(
        "group relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
        active
          ? "bg-primary text-primary-foreground shadow-sm"
          : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
        collapsed ? "justify-center px-2" : ""
      )}
    >
      <Icon size={17} className="shrink-0" />
      {!collapsed && (
        <span className="flex-1 text-left leading-none">{label}</span>
      )}
      {!collapsed && badge && (
        <Badge variant={active ? "secondary" : "default"} className="ml-auto text-[10px]">
          {badge}
        </Badge>
      )}
      {/* Tooltip when collapsed */}
      {collapsed && (
        <span className="pointer-events-none absolute left-full ml-3 hidden whitespace-nowrap rounded-md border border-border bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md group-hover:block">
          {label}
          {badge && <span className="ml-1.5 text-muted-foreground">({badge})</span>}
        </span>
      )}
    </button>
  );
}

export default function Sidebar({ currentScreen, onNavigate }: SidebarProps) {
  const { user } = useAuth();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={twMerge(
        "relative flex h-full shrink-0 flex-col border-r border-border bg-card transition-all duration-200 ease-in-out",
        collapsed ? "w-[60px]" : "w-[220px]"
      )}
    >
      {/* Logo area (mirrors Navbar logo for standalone sidebar context) */}
      <div
        className={twMerge(
          "flex h-14 shrink-0 items-center border-b border-border px-3",
          collapsed ? "justify-center" : "gap-2 px-4"
        )}
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary">
          <BrainCircuit size={14} className="text-primary-foreground" />
        </div>
        {!collapsed && (
          <span
            className="text-sm font-bold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            PrepAI
          </span>
        )}
      </div>

      {/* Primary nav */}
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2 pt-3" aria-label="Sidebar navigation">
        {!collapsed && (
          <p
            className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground"
            style={{ fontFamily: "var(--font-mono)" }}
          >
            Menu
          </p>
        )}
        {primaryNav.map((item) => (
          <NavButton
            key={item.screen}
            item={item}
            active={currentScreen === item.screen}
            collapsed={collapsed}
            onClick={() => onNavigate(item.screen)}
          />
        ))}

      </nav>

      {/* User card */}
      {!collapsed && (
        <div className="shrink-0 border-t border-border p-3">
          <div className="flex items-center gap-2.5 rounded-lg p-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">
              {getInitials(user?.name)}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-foreground">{user?.name || "User"}</p>
            </div>
          </div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className="absolute -right-3 top-[72px] flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-sm transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>
    </aside>
  );
}
