import { cn } from "@/shared/lib/cn";

/** Fallback de `<Suspense>` mientras se descarga el chunk de una página
 * cargada con `React.lazy` (code-splitting por ruta, RNF-PERF). Mismo
 * patrón visual que el "Cargando…" de `ProtectedRoute` para la sesión
 * inicial — mantiene un solo lenguaje de "esperando algo" en toda la app. */
export function RouteFallback({ className }: { className?: string }) {
  return (
    <div
      className={cn("flex items-center justify-center text-ink-soft", className ?? "min-h-screen")}
      aria-busy="true"
    >
      Cargando…
    </div>
  );
}
