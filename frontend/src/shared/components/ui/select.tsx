import { ChevronDown } from "lucide-react";
import { forwardRef, useId, type ReactNode, type SelectHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  children: ReactNode;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, id, className, children, ...props }, ref) => {
    // Ver el mismo comentario en `Input` — sin este respaldo, cualquier
    // <Select> sin `id`/`name` explícitos pierde la asociación label/control.
    const idGenerado = useId();
    const inputId = id ?? props.name ?? idGenerado;
    const errorId = error ? `${inputId}-error` : undefined;
    return (
      <div className="mb-4">
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ink-soft">
          {label}
        </label>
        <div className="relative">
          <select
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            aria-describedby={errorId}
            className={cn(
              "h-11 w-full appearance-none rounded-sm border border-border bg-surface px-4 pr-10 text-sm text-ink outline-none",
              "transition-colors duration-base hover:border-primary-100 focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15",
              error && "border-danger focus:border-danger focus:ring-danger/15",
              className,
            )}
            {...props}
          >
            {children}
          </select>
          <ChevronDown
            className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft"
            aria-hidden="true"
          />
        </div>
        {error && (
          <p id={errorId} aria-live="polite" className="mt-1.5 text-xs font-medium text-danger">
            {error}
          </p>
        )}
      </div>
    );
  },
);
Select.displayName = "Select";
