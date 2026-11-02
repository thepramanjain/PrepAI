import React from "react";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "../context/ThemeContext";

interface ThemeToggleProps {
  showLabel?: boolean;
  className?: string;
}

export default function ThemeToggle({ showLabel = false, className = "" }: ThemeToggleProps) {
  const { isDark, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className={[
        "relative inline-flex items-center justify-center rounded-lg border border-border bg-card/80 text-foreground shadow-sm backdrop-blur-sm transition-all duration-200 hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer select-none",
        showLabel ? "gap-2.5 px-3 py-2 text-sm font-medium w-full" : "h-9 w-9 p-0",
        className,
      ].filter(Boolean).join(" ")}
    >
      <div className="relative flex h-4 w-4 items-center justify-center">
        <Sun
          size={16}
          className={[
            "absolute transition-all duration-300 text-amber-500 dark:text-amber-400",
            isDark
              ? "rotate-0 scale-100 opacity-100"
              : "-rotate-90 scale-0 opacity-0 pointer-events-none",
          ].join(" ")}
        />
        <Moon
          size={16}
          className={[
            "absolute transition-all duration-300 text-slate-700 dark:text-slate-200",
            isDark
              ? "rotate-90 scale-0 opacity-0 pointer-events-none"
              : "rotate-0 scale-100 opacity-100",
          ].join(" ")}
        />
      </div>

      {showLabel && (
        <span className="flex-1 text-left">
          {isDark ? "Light Mode" : "Dark Mode"}
        </span>
      )}
    </button>
  );
}
