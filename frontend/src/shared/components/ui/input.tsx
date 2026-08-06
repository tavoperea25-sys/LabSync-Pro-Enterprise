import { AlertCircle } from "lucide-react";
import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/shared/lib/cn";

/** Ver docs/12-component-library.md — componente Input/TextField. */
export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  icono?: ReactNode;
  error?: string;
  accion?: ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, icono, error, accion, id, className, ...props }, ref) => {
    // `id ?? name` no basta: la mayoría de formularios del proyecto (todo lo
    // que no usa react-hook-form, que provee `name` vía `register()`) no
    // pasa ninguno de los dos, y sin un tercer valor de respaldo el `<label
    // htmlFor>` queda apuntando a `undefined` — visualmente indistinguible,
    // pero rompe la asociación programática label/input para lectores de
    // pantalla (WCAG 1.3.1/4.1.2). `useId()` da un id estable por instancia
    // sin que cada call site tenga que declarar uno.
    const idGenerado = useId();
    const inputId = id ?? props.name ?? idGenerado;
    const errorId = error ? `${inputId}-error` : undefined;

    return (
      <div className="mb-4">
        <label htmlFor={inputId} className="mb-1.5 block text-sm font-semibold text-ink-soft">
          {label}
        </label>
        <div className="relative">
          {icono && (
            <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-primary-900">
              {icono}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            aria-invalid={!!error}
            aria-describedby={errorId}
            className={cn(
              "h-11 w-full rounded-sm border border-border bg-surface px-4 text-sm text-ink outline-none",
              "transition-colors duration-base placeholder:text-ink-soft",
              "hover:border-primary-100 focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15",
              icono && "pl-11",
              accion && "pr-11",
              error && "border-danger focus:border-danger focus:ring-danger/15",
              className,
            )}
            {...props}
          />
          {accion && <span className="absolute right-2 top-1/2 -translate-y-1/2">{accion}</span>}
        </div>
        {error && (
          <p id={errorId} aria-live="polite" className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-danger">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}
      </div>
    );
  },
);
Input.displayName = "Input";
