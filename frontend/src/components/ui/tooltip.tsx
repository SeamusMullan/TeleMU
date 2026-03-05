import type { ReactNode, ComponentProps } from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "../../lib/cn";

// eslint-disable-next-line react-refresh/only-export-components
export const TooltipProvider = TooltipPrimitive.Provider;

interface TooltipProps {
  children: ReactNode;
  content: ReactNode;
  side?: ComponentProps<typeof TooltipPrimitive.Content>["side"];
  delayDuration?: number;
}

export function Tooltip({
  children,
  content,
  side = "top",
  delayDuration,
}: TooltipProps) {
  return (
    <TooltipPrimitive.Root delayDuration={delayDuration}>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipPrimitive.Portal>
        <TooltipPrimitive.Content
          side={side}
          sideOffset={6}
          className={cn(
            "z-50 max-w-xs rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-3)] px-3 py-1.5 text-xs text-[var(--color-text)] shadow-[var(--shadow-md)]",
            "animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
          )}
        >
          {content}
          <TooltipPrimitive.Arrow className="fill-[var(--color-surface-3)]" />
        </TooltipPrimitive.Content>
      </TooltipPrimitive.Portal>
    </TooltipPrimitive.Root>
  );
}
