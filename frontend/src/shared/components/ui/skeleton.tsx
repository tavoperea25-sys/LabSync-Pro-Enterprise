import { cn } from "@/shared/lib/cn";

/** Ver docs/12-component-library.md — Skeleton Loader. Estado de carga
 * >300ms en tablas, cards y detalle (docs/04-requerimientos-no-funcionales.md
 * RNF-PERF). */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-md bg-surface-alt", className)} />;
}
