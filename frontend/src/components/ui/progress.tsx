import { type HTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

type ProgressVariant = "default" | "success" | "warning" | "violet";

interface ProgressProps extends HTMLAttributes<HTMLDivElement> {
  value?: number;
  max?: number;
  variant?: ProgressVariant;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  label?: string;
}

const trackSizes = { sm: "h-1", md: "h-2", lg: "h-3" };

const fillVariants: Record<ProgressVariant, string> = {
  default: "bg-gradient-to-r from-violet-600 to-indigo-500",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  violet: "bg-gradient-to-r from-purple-500 to-violet-600",
};

export function Progress({
  value = 0,
  max = 100,
  variant = "default",
  size = "md",
  showLabel = false,
  label,
  className,
  ...props
}: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={twMerge("w-full", className)} {...props}>
      {(showLabel || label) && (
        <div className="mb-1.5 flex items-center justify-between">
          {label && <span className="text-xs font-medium text-foreground">{label}</span>}
          {showLabel && (
            <span className="text-xs tabular-nums text-muted-foreground" style={{ fontFamily: "var(--font-mono)" }}>
              {Math.round(pct)}%
            </span>
          )}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
        className={twMerge(
          "w-full overflow-hidden rounded-full bg-secondary",
          trackSizes[size]
        )}
      >
        <div
          className={twMerge(
            "h-full rounded-full transition-all duration-500 ease-out",
            fillVariants[variant]
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
