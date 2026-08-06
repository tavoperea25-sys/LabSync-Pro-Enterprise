import { forwardRef, useId, type TextareaHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, id, className, ...props }, ref) => {
    // Ver el mismo comentario en `Input` — sin este respaldo, cualquier
    // <Textarea> sin `id`/`name` explícitos pierde la asociación label/control.
    const idGenerado = useId();
    const inputId = id ?? props.name ?? idGenerado;
    const errorId = error ? `${inputId}-error` : undefined;
    return (
      <div className="mb-4">
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ink-soft">
          {label}
        </label>
        <textarea
          ref={ref}
          id={inputId}
          rows={3}
          aria-invalid={!!error}
          aria-describedby={errorId}
          className={cn(
            "w-full rounded-sm border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none",
            "transition-colors duration-base placeholder:text-ink-soft",
            "hover:border-primary-100 focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15",
            error && "border-danger focus:border-danger focus:ring-danger/15",
            className,
          )}
          {...props}
        />
        {error && (
          <p id={errorId} aria-live="polite" className="mt-1.5 text-xs font-medium text-danger">
            {error}
          </p>
        )}
      </div>
    );
  },
);
Textarea.displayName = "Textarea";
