import { AlertTriangle, Bell, CheckCircle2 } from "lucide-react";
import { Link } from "react-router";

import { useAlertas } from "@/features/alertas/hooks/useAlertas";
import { Skeleton } from "@/shared/components/ui/skeleton";

const LIMITE_VISIBLE = 4;

export function AlertsSummary() {
  // RNF-PERF-03 — se pide una página chica al servidor (antes traía todas
  // las activas del laboratorio solo para mostrar 4).
  const { data, isLoading, isError } = useAlertas("activa", 1, 20);
  const alertas = data?.items ?? [];
  const criticas = alertas.filter((a) => a.tipo === "critica");
  const preventivas = alertas.filter((a) => a.tipo === "preventiva");
  const visibles = [...criticas, ...preventivas].slice(0, LIMITE_VISIBLE);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="h-4 w-4 text-ink-soft" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-ink">Centro de alertas</h2>
        </div>
        <Link to="/alertas" className="text-xs font-semibold text-primary-600 hover:text-primary-900">
          Ver todas →
        </Link>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <div className="flex items-center gap-3 rounded-md border-l-[3px] border-danger bg-danger/10 px-3 py-3">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 text-danger" aria-hidden="true" />
          <p className="text-sm text-ink">No se pudo cargar el centro de alertas. Intenta de nuevo en unos segundos.</p>
        </div>
      )}

      {!isLoading && !isError && visibles.length === 0 && (
        <div className="flex items-center gap-3 rounded-md border-l-[3px] border-success bg-success/10 px-3 py-3">
          <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-success" aria-hidden="true" />
          <p className="text-sm text-ink">Todos los equipos y procesos están dentro de parámetro.</p>
        </div>
      )}

      {!isLoading && !isError && visibles.length > 0 && (
        <ul className="space-y-2">
          {visibles.map((alerta) => (
            <li key={alerta.id}>
              <Link
                to="/alertas"
                // Tinte plano del color semántico a baja opacidad en vez de
                // un hex pastel fijo con opacidad — un pastel pensado para
                // fondo claro se ve turbio/apagado al mezclarse sobre una
                // superficie oscura (modo oscuro); el color semántico base
                // (`--danger`/`--warning`) es legible sobre cualquiera de
                // los dos fondos.
                className={`flex items-start gap-2.5 rounded-md border-l-[3px] px-3 py-2.5 transition-colors duration-fast hover:brightness-95 ${
                  alerta.tipo === "critica" ? "border-danger bg-danger/10" : "border-warning bg-warning/10"
                }`}
              >
                <AlertTriangle
                  className={`mt-0.5 h-3.5 w-3.5 flex-shrink-0 ${
                    alerta.tipo === "critica" ? "text-danger" : "text-warning"
                  }`}
                  aria-hidden="true"
                />
                <p className="text-xs leading-snug text-ink">
                  <span
                    className={`mb-0.5 block text-[10px] font-bold uppercase tracking-wide ${
                      alerta.tipo === "critica" ? "text-danger" : "text-warning"
                    }`}
                  >
                    {alerta.tipo === "critica" ? "Crítico" : "Atención"}
                  </span>
                  {alerta.mensaje}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
