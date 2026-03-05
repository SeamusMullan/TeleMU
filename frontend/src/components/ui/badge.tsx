import type { HTMLAttributes } from "react";
import { cn } from "../../lib/cn";

const variants = {
  default: "bg-[var(--color-surface-3)] text-[var(--color-text-secondary)]",
  accent: "bg-[var(--color-accent)]/15 text-[var(--color-accent)]",
  success: "bg-[var(--color-green)]/15 text-[var(--color-green)]",
  warning: "bg-[var(--color-amber)]/15 text-[var(--color-amber)]",
  danger: "bg-[var(--color-red)]/15 text-[var(--color-red)]",
  info: "bg-[var(--color-blue)]/15 text-[var(--color-blue)]",
} as const;

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof variants;
}

export function Badge({
  variant = "default",
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-[var(--radius-full)] px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
