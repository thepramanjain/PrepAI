import { type HTMLAttributes } from "react";
import { twMerge } from "tailwind-merge";

type BadgeVariant = "default" | "secondary" | "outline" | "success" | "warning" | "destructive" | "violet";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variants: Record<BadgeVariant, string> = {
  default:
    "bg-primary/10 text-primary border-primary/20",
  secondary:
    "bg-secondary text-secondary-foreground border-border",
  outline:
    "bg-transparent text-foreground border-border",
  success:
    "bg-emerald-500/10 text-emerald-600 border-emerald-500/20 dark:text-emerald-400",
  warning:
    "bg-amber-500/10 text-amber-600 border-amber-500/20 dark:text-amber-400",
  destructive:
    "bg-destructive/10 text-destructive border-destructive/20",
  violet:
    "bg-purple-600/10 text-purple-700 border-purple-500/20 dark:text-purple-400 dark:border-purple-400/20",
};

export function Badge({ variant = "default", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={twMerge(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium leading-none",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
