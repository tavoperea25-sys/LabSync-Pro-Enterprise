import { Check } from "lucide-react";
import { forwardRef, useId, type InputHTMLAttributes } from "react";

import { cn } from "@/shared/lib/cn";

/** Ver docs/12-component-library.md — componente Checkbox. Input real
 * (accesible, focus/keyboard nativos) visualmente oculto detrás de un
 * indicador custom — patrón ya auditado en el login original. */
export interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, className, id, ...props }, ref) => {
    // Ver el mismo comentario en `Input` — sin este respaldo, cualquier
    // <Checkbox> sin `id`/`name` explícitos pierde la asociación label/control.
    const idGenerado = useId();
    const inputId = id ?? props.name ?? idGenerado;
    return (
      <label
        htmlFor={inputId}
        className="group inline-flex cursor-pointer select-none items-center gap-2.5 text-sm text-ink-soft"
      >
        {/* input, caja visual e ícono son hermanos directos (no anidados)
            para que las variantes `peer-checked:` de Tailwind, que solo
            siguen hermanos subsecuentes, se apliquen a ambos. */}
        <span className="relative inline-flex h-[18px] w-[18px] flex-shrink-0">
          <input
            ref={ref}
            id={inputId}
            type="checkbox"
            className="peer absolute inset-0 z-10 h-[18px] w-[18px] cursor-pointer opacity-0"
            {...props}
          />
          <span
            className={cn(
              "absolute inset-0 rounded-[5px] border-[1.5px] border-border bg-surface transition-colors duration-fast",
              "peer-checked:border-primary-900 peer-checked:bg-primary-900",
              "peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary-900",
              "group-hover:border-primary-600",
              className,
            )}
          />
          <Check
            className="pointer-events-none absolute inset-0 m-auto h-3 w-3 scale-50 text-white opacity-0 transition-all duration-fast peer-checked:scale-100 peer-checked:opacity-100"
            strokeWidth={3}
            aria-hidden="true"
          />
        </span>
        {label}
      </label>
    );
  },
);
Checkbox.displayName = "Checkbox";
