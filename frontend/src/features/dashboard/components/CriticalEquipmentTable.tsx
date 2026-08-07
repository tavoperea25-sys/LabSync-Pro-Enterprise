import { AlertTriangle, ShieldCheck } from "lucide-react";
import { Link } from "react-router";

import { EquipoEstadoBadge } from "@/features/equipos/components/EquipoEstadoBadge";
import type { EstadoOperativo } from "@/features/equipos/types";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useEquiposCriticos } from "../hooks/useDashboard";

function formatearFecha(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("es-CO", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function CriticalEquipmentTable() {
  const { data: equipos, isLoading, isError } = useEquiposCriticos(10);

  return (
    <section>
      <h2 className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-ink">
        <AlertTriangle className="h-4 w-4 text-ink-soft" aria-hidden="true" />
        Equipos que requieren atención
      </h2>

      <div className="overflow-hidden rounded-lg border border-border bg-surface">
        {isLoading && (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        )}

        {isError && (
          <p className="p-6 text-center text-sm text-ink-soft">
            No se pudo cargar la tabla de equipos críticos.
          </p>
        )}

        {!isLoading && !isError && (!equipos || equipos.length === 0) && (
          <EmptyState
            icon={ShieldCheck}
            title="Ningún equipo requiere atención"
            description="Todos los equipos del laboratorio están operativos, calibrados y al día."
          />
        )}

        {!isLoading && !isError && equipos && equipos.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-alt text-left text-xs font-semibold uppercase tracking-wide text-ink-soft">
                  <th scope="col" className="px-4 py-2.5">Equipo</th>
                  <th scope="col" className="px-4 py-2.5">Código</th>
                  <th scope="col" className="px-4 py-2.5">Área</th>
                  <th scope="col" className="px-4 py-2.5">Estado</th>
                  <th scope="col" className="px-4 py-2.5">Última calibración</th>
                  <th scope="col" className="px-4 py-2.5">Próxima calibración</th>
                  <th scope="col" className="px-4 py-2.5">Responsable</th>
                </tr>
              </thead>
              <tbody>
                {equipos.map((equipo) => (
                  <tr key={equipo.equipo_id} className="border-b border-border last:border-0 hover:bg-surface-alt">
                    <td className="px-4 py-2.5">
                      <Link to={`/equipos/${equipo.equipo_id}`} className="font-semibold text-ink hover:text-primary-900">
                        {equipo.equipo_nombre}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-ink-soft">{equipo.equipo_codigo_interno}</td>
                    <td className="px-4 py-2.5 text-ink-soft">{equipo.area_nombre ?? "—"}</td>
                    <td className="px-4 py-2.5">
                      <EquipoEstadoBadge estado={equipo.estado_operativo as EstadoOperativo} />
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-ink-soft">
                      {formatearFecha(equipo.ultima_calibracion_fecha)}
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-ink-soft">
                      {formatearFecha(equipo.proxima_calibracion_fecha)}
                    </td>
                    <td className="px-4 py-2.5 text-ink-soft">{equipo.responsable_nombre ?? "Sin asignar"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
