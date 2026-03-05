import type { HTMLAttributes, ComponentProps } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cn } from "../../lib/cn";

// eslint-disable-next-line react-refresh/only-export-components
export const Dialog = DialogPrimitive.Root;
// eslint-disable-next-line react-refresh/only-export-components
export const DialogTrigger = DialogPrimitive.Trigger;
// eslint-disable-next-line react-refresh/only-export-components
export const DialogClose = DialogPrimitive.Close;

export function DialogOverlay({
  className,
  ref,
  ...props
}: ComponentProps<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Overlay
      ref={ref}
      className={cn(
        "fixed inset-0 z-50 bg-black/60",
        "data-[state=open]:animate-[overlay-show_var(--duration-normal)_ease-out]",
        "data-[state=closed]:animate-[overlay-hide_var(--duration-normal)_ease-in]",
        className,
      )}
      {...props}
    />
  );
}

export function DialogContent({
  className,
  children,
  ref,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2",
          "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-1)] p-6 shadow-[var(--shadow-lg)]",
          "data-[state=open]:animate-[content-show_var(--duration-normal)_ease-out]",
          "data-[state=closed]:animate-[content-hide_var(--duration-normal)_ease-in]",
          "focus:outline-none",
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function DialogHeader({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mb-4 flex flex-col gap-1.5", className)}
      {...props}
    />
  );
}

export function DialogTitle({
  className,
  ref,
  ...props
}: ComponentProps<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      ref={ref}
      className={cn("text-lg font-semibold text-[var(--color-text)]", className)}
      {...props}
    />
  );
}

export function DialogDescription({
  className,
  ref,
  ...props
}: ComponentProps<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      ref={ref}
      className={cn("text-sm text-[var(--color-text-secondary)]", className)}
      {...props}
    />
  );
}

export function DialogFooter({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mt-6 flex justify-end gap-2", className)}
      {...props}
    />
  );
}
