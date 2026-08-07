import { AlertTriangle, Wrench } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import { useEquipos } from "@/features/equipos/hooks/useEquipos";
import { IncidenciasQrPendientes } from "@/features/qr/components/IncidenciasQrPendientes";
import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useMantenimientos } from "../hooks/useMantenimientos";
import { ETIQUETAS_TIPO } from "../types";
import { EstadoMantenimientoBadge } from "./EstadoMantenimientoBadge";

/** RF-MANT-01/03 — vista consolidada de todos los mantenimientos del
 * laboratorio; las acciones (iniciar/cerrar/cancelar) viven en la ficha del
 * equipo (`MantenimientosSection`), aquí solo se navega hacia allá — mismo
 * criterio que `CriticosPage` de Calibraciones. Paginado (RNF-PERF-03),
 * mismo patrón que `EquiposListPage`. */
export function MantenimientosListPage() {
  const navigate = useNavigate();
  const [pagina, setPagina] = useState(1);
  const { data, isLoading, isError } = useMantenimientos(pagina);
  const { data: paginaEquipos } = useEquipos({});

  const mantenimientos = data?.items ?? [];
  const totalPaginas = data ? Math.max(1, Math.ceil(data.total / data.tamano_pagina)) : 1;
  const equiposPorId = new Map((paginaEquipos?.items ?? []).map((e) => [e.id, e]));

  return (
    <div className="p-6 sm:p-8">
      <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Mantenimientos</h1>
      <p className="mb-6 text-sm text-ink-soft">
        Todos los mantenimientos registrados, más recientes primero.
      </p>

      <IncidenciasQrPendientes />

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

      {!isLoading && !isError && mantenimientos.length === 0 && (
        <EmptyState
          icon={Wrench}
          title="Sin mantenimientos registrados"
          description="Registra un mantenimiento desde la ficha de un equipo."
        />
      )}

      {!isError && !!mantenimientos.length && (
        <>
          <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
            {mantenimientos.map((mantenimiento) => {
              const equipo = equiposPorId.get(mantenimiento.equipo_id);
              return (
                <li key={mantenimiento.id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/equipos/${mantenimiento.equipo_id}`)}
                    className="flex w-full items-center justify-between gap-3 bg-surface px-4 py-3 text-left hover:bg-surface-alt"
                  >
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-ink-soft">
                        {equipo ? `${equipo.codigo_interno} · ${equipo.nombre}` : mantenimiento.equipo_id}
                      </p>
                      <p className="truncate text-sm font-medium text-ink">
                        {ETIQUETAS_TIPO[mantenimiento.tipo]}
                      </p>
                      <p className="text-xs text-ink-soft">
                        {mantenimiento.fecha_programada && `Programado: ${mantenimiento.fecha_programada}`}
                        {mantenimiento.fecha_ejecutada && ` · Ejecutado: ${mantenimiento.fecha_ejecutada}`}
                      </p>
                    </div>
                    <EstadoMantenimientoBadge estado={mantenimiento.estado} />
                  </button>
                </li>
              );
            })}
          </ul>

          {totalPaginas > 1 && (
            <div className="mt-5 flex items-center justify-center gap-3 text-sm text-ink-soft">
              <Button variant="secondary" size="sm" disabled={pagina <= 1} onClick={() => setPagina((p) => p - 1)}>
                Anterior
              </Button>
              <span>
                Página {pagina} de {totalPaginas}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={pagina >= totalPaginas}
                onClick={() => setPagina((p) => p + 1)}
              >
                Siguiente
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
