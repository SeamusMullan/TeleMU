import type { ReactNode, ComponentProps } from "react";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { cn } from "../../lib/cn";

// eslint-disable-next-line react-refresh/only-export-components
export const DropdownMenu = DropdownMenuPrimitive.Root;
// eslint-disable-next-line react-refresh/only-export-components
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;

export function DropdownMenuContent({
  className,
  sideOffset = 4,
  ref,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        ref={ref}
        sideOffset={sideOffset}
        className={cn(
          "z-50 min-w-[180px] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-1)] p-1 shadow-[var(--shadow-lg)]",
          "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
          "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95",
          className,
        )}
        {...props}
      />
    </DropdownMenuPrimitive.Portal>
  );
}

interface DropdownMenuItemProps
  extends ComponentProps<typeof DropdownMenuPrimitive.Item> {
  icon?: ReactNode;
  shortcut?: string;
}

export function DropdownMenuItem({
  className,
  icon,
  shortcut,
  children,
  ref,
  ...props
}: DropdownMenuItemProps) {
  return (
    <DropdownMenuPrimitive.Item
      ref={ref}
      className={cn(
        "relative flex cursor-default select-none items-center gap-2 rounded-[var(--radius-md)] px-2 py-1.5 text-sm text-[var(--color-text)] outline-none",
        "data-[highlighted]:bg-[var(--color-surface-2)] data-[highlighted]:text-[var(--color-text)]",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        className,
      )}
      {...props}
    >
      {icon && <span className="h-4 w-4 shrink-0">{icon}</span>}
      <span className="flex-1">{children}</span>
      {shortcut && (
        <span className="ml-auto text-xs text-[var(--color-text-muted)]">
          {shortcut}
        </span>
      )}
    </DropdownMenuPrimitive.Item>
  );
}

export function DropdownMenuSeparator({
  className,
  ref,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Separator>) {
  return (
    <DropdownMenuPrimitive.Separator
      ref={ref}
      className={cn("-mx-1 my-1 h-px bg-[var(--color-border-subtle)]", className)}
      {...props}
    />
  );
}

export function DropdownMenuLabel({
  className,
  ref,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Label>) {
  return (
    <DropdownMenuPrimitive.Label
      ref={ref}
      className={cn(
        "px-2 py-1.5 text-xs font-semibold text-[var(--color-text-muted)]",
        className,
      )}
      {...props}
    />
  );
}
