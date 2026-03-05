import type { ComponentProps } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../../lib/cn";

// eslint-disable-next-line react-refresh/only-export-components
export const Tabs = TabsPrimitive.Root;

export function TabsList({
  className,
  ref,
  ...props
}: ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn(
        "flex items-center gap-1 border-b border-[var(--color-border-subtle)]",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ref,
  ...props
}: ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center px-3 py-2 text-sm font-medium text-[var(--color-text-secondary)] transition-colors",
        "border-b-2 border-transparent",
        "hover:text-[var(--color-text)]",
        "data-[state=active]:border-[var(--color-accent)] data-[state=active]:text-[var(--color-text)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-surface-0)]",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ref,
  ...props
}: ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      ref={ref}
      className={cn(
        "mt-3 focus-visible:outline-none",
        className,
      )}
      {...props}
    />
  );
}
