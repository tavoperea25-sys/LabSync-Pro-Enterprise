import { AlertTriangle, ShieldAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useCriticos } from "../hooks/useCalibraciones";
import { SemaforoBadge } from "./SemaforoBadge";

/** RF-CAL-05 — equipos críticos próximos a vencer u vencidos, ordenados
 * por urgencia (ya viene ordenado desde el backend: rojo > amarillo > gris). */
export function CriticosPage() {
  const navigate = useNavigate();
  const { data: criticos, isLoading, isError } = useCriticos();

  return (
    <div className="p-6 sm:p-8">
      <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Calibraciones críticas</h1>
      <p className="mb-6 text-sm text-ink-soft">
        Equipos vencidos, próximos a vencer o sin calibración registrada — ordenados por urgencia.
      </p>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <EmptyState
          icon={AlertTriangle}
          title="No se pudo cargar el listado"
          description="Intenta de nuevo en unos segundos."
        />
      )}

      {!isLoading && !isError && criticos?.length === 0 && (
        <EmptyState
          icon={ShieldAlert}
          title="Sin equipos críticos"
          description="Todos los equipos con calibración registrada están vigentes."
        />
      )}

      {!isError && !!criticos?.length && (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
          {criticos.map((equipo) => (
            <li key={equipo.equipo_id}>
              <button
                type="button"
                onClick={() => navigate(`/equipos/${equipo.equipo_id}`)}
                className="flex w-full items-center justify-between gap-3 bg-surface px-4 py-3 text-left hover:bg-surface-alt"
              >
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-ink-soft">{equipo.equipo_codigo_interno}</p>
                  <p className="truncate text-sm font-medium text-ink">{equipo.equipo_nombre}</p>
                  {equipo.proxima_fecha && (
                    <p className="text-xs text-ink-soft">
                      Próxima calibración: {equipo.proxima_fecha}
                      {equipo.dias_restantes !== null &&
                        (equipo.dias_restantes < 0
                          ? ` (vencida hace ${Math.abs(equipo.dias_restantes)} días)`
                          : ` (en ${equipo.dias_restantes} días)`)}
                    </p>
                  )}
                  {!equipo.proxima_fecha && <p className="text-xs text-ink-soft">Nunca se ha calibrado.</p>}
                </div>
                <SemaforoBadge semaforo={equipo.semaforo} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
