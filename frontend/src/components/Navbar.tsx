import { useState, useRef, useEffect } from "react";
import {
  BrainCircuit,
  ChevronDown,
  LogOut,
  Settings,
  User,
  Sparkles,
  Menu,
  X,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { useAuth } from "../context/AuthContext";
import type { Screen } from "../types";

interface NavbarProps {
  currentScreen: Screen;
  onNavigate: (screen: Screen) => void;
}

const publicLinks: { label: string; screen: Screen }[] = [
  { label: "Features", screen: "landing" },
];

const appLinks: { label: string; screen: Screen }[] = [
  { label: "Dashboard", screen: "dashboard" },
  { label: "Practice", screen: "create-interview" },
  { label: "Results", screen: "results" },
  { label: "Analytics", screen: "analytics" },
];

function getInitials(name?: string) {
  if (!name) return "U";
  const parts = name.trim().split(" ");
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export default function Navbar({ currentScreen, onNavigate }: NavbarProps) {
  const { isAuthenticated, user, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [currentScreen]);

  const links = isAuthenticated ? appLinks : publicLinks;

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center gap-4 px-4 sm:px-6">
        {/* Logo */}
        <button
          onClick={() => onNavigate(isAuthenticated ? "dashboard" : "landing")}
          className="flex items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          aria-label="PrepAI home"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary shadow-sm">
            <BrainCircuit size={16} className="text-primary-foreground" />
          </div>
          <span
            className="text-base font-bold tracking-tight text-foreground"
            style={{ fontFamily: "var(--font-display)" }}
          >
            PrepAI
          </span>
        </button>

        {/* Desktop nav links */}
        <nav className="ml-4 hidden items-center gap-1 md:flex" aria-label="Primary navigation">
          {links.map(({ label, screen }) => (
            <button
              key={label}
              onClick={() => onNavigate(screen)}
              className={[
                "rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-100",
                currentScreen === screen
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
              ].join(" ")}
            >
              {label}
            </button>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right cluster */}
        <div className="flex items-center gap-2">
          {isAuthenticated ? (
            <>
              {/* Start Practice CTA */}
              <Button
                size="sm"
                onClick={() => onNavigate("create-interview")}
                className="hidden sm:inline-flex"
              >
                <Sparkles size={13} /> Start Practice
              </Button>

              {/* Profile avatar menu */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setProfileOpen((o) => !o)}
                  aria-expanded={profileOpen}
                  aria-haspopup="true"
                  className="flex items-center gap-1.5 rounded-lg border border-border bg-card/80 px-2 py-1.5 text-sm font-medium text-foreground shadow-sm backdrop-blur-sm transition-colors hover:bg-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[11px] font-bold text-primary-foreground">
                    {getInitials(user?.name)}
                  </span>
                  <span className="hidden sm:block">{user?.name || "User"}</span>
                  <ChevronDown
                    size={13}
                    className={`text-muted-foreground transition-transform duration-150 ${profileOpen ? "rotate-180" : ""}`}
                  />
                </button>

                {profileOpen && (
                  <div className="absolute right-0 top-full z-50 mt-2 w-52 rounded-xl border border-border bg-popover shadow-xl ring-1 ring-black/5 dark:ring-white/[0.06]">
                    <div className="border-b border-border px-4 py-3">
                      <p className="text-sm font-semibold text-foreground">{user?.name || "User"}</p>
                      <p className="text-xs text-muted-foreground truncate">{user?.email || "user@example.com"}</p>
                    </div>
                    <div className="p-1">
                      <button
                        onClick={() => { logout(); setProfileOpen(false); }}
                        className="flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-sm text-destructive transition-colors hover:bg-destructive/10"
                      >
                        <LogOut size={14} />
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" onClick={() => onNavigate("dashboard")}>
                Sign in
              </Button>
              <Button size="sm" onClick={() => onNavigate("create-interview")}>
                <Sparkles size={13} /> Start Practice
              </Button>
            </>
          )}

          {/* Mobile menu toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X size={16} /> : <Menu size={16} />}
          </Button>
        </div>
      </div>

      {/* Mobile nav drawer */}
      {mobileOpen && (
        <div className="border-t border-border/50 bg-background/80 px-4 pb-4 pt-2 backdrop-blur-xl md:hidden">
          <nav className="flex flex-col gap-1">
            {links.map(({ label, screen }) => (
              <button
                key={label}
                onClick={() => onNavigate(screen)}
                className={[
                  "rounded-md px-3 py-2 text-left text-sm font-medium transition-colors",
                  currentScreen === screen
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
            {isAuthenticated && (
              <div className="mt-2 border-t border-border pt-2">
                <Button size="sm" onClick={() => onNavigate("create-interview")} className="w-full">
                  <Sparkles size={13} /> Start Practice
                </Button>
              </div>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
