import type { InputHTMLAttributes, Ref } from "react";
import { cn } from "../../lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  ref?: Ref<HTMLInputElement>;
  label?: string;
  error?: string;
  helperText?: string;
  wrapperClassName?: string;
}

export function Input({
  label,
  error,
  helperText,
  wrapperClassName,
  className,
  id,
  ref,
  ...props
}: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className={cn("flex flex-col gap-1.5", wrapperClassName)}>
      {label && (
        <label
          htmlFor={inputId}
          className="text-sm font-medium text-[var(--color-text-secondary)]"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={cn(
          "h-9 rounded-[var(--radius-md)] border bg-[var(--color-surface-1)] px-3 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-muted)]",
          "transition-colors duration-[var(--duration-fast)]",
          "focus:outline-none focus:border-[var(--color-border-focus)] focus:ring-1 focus:ring-[var(--color-border-focus)]",
          "disabled:cursor-not-allowed disabled:opacity-50",
          error
            ? "border-[var(--color-red)] focus:border-[var(--color-red)] focus:ring-[var(--color-red)]"
            : "border-[var(--color-border)]",
          className,
        )}
        {...props}
      />
      {error && (
        <p className="text-xs text-[var(--color-red)]">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-xs text-[var(--color-text-muted)]">{helperText}</p>
      )}
    </div>
  );
}
