import type { SelectHTMLAttributes, Ref } from "react";
import { cn } from "../../lib/cn";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  ref?: Ref<HTMLSelectElement>;
  label?: string;
  error?: string;
  helperText?: string;
  options: SelectOption[];
  placeholder?: string;
}

export function Select({
  label,
  error,
  helperText,
  options,
  placeholder,
  className,
  id,
  ref,
  ...props
}: SelectProps) {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, "-");

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={selectId}
          className="text-sm font-medium text-[var(--color-text-secondary)]"
        >
          {label}
        </label>
      )}
      <div className="relative">
        <select
          ref={ref}
          id={selectId}
          className={cn(
            "h-9 w-full appearance-none rounded-[var(--radius-md)] border bg-[var(--color-surface-1)] px-3 pr-8 text-sm text-[var(--color-text)]",
            "transition-colors duration-[var(--duration-fast)]",
            "focus:outline-none focus:border-[var(--color-border-focus)] focus:ring-1 focus:ring-[var(--color-border-focus)]",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error
              ? "border-[var(--color-red)] focus:border-[var(--color-red)] focus:ring-[var(--color-red)]"
              : "border-[var(--color-border)]",
            className,
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <svg
          className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-muted)]"
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M4.427 6.427l3.396 3.396a.25.25 0 00.354 0l3.396-3.396A.25.25 0 0011.396 6H4.604a.25.25 0 00-.177.427z" />
        </svg>
      </div>
      {error && (
        <p className="text-xs text-[var(--color-red)]">{error}</p>
      )}
      {helperText && !error && (
        <p className="text-xs text-[var(--color-text-muted)]">{helperText}</p>
      )}
    </div>
  );
}
