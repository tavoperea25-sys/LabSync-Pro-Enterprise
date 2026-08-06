import { AlertTriangle, Bell } from "lucide-react";
import { useState } from "react";

import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Select } from "@/shared/components/ui/select";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useAlertas, useMarcarLeida, useResolverManual } from "../hooks/useAlertas";
import type { EstadoAlerta } from "../types";
import { AlertaItem } from "./AlertaItem";

export function AlertasPage() {
  const [filtroEstado, setFiltroEstado] = useState<EstadoAlerta | "todas">("activa");
  const [pagina, setPagina] = useState(1);
  const { data, isLoading, isError } = useAlertas(filtroEstado === "todas" ? undefined : filtroEstado, pagina);
  const marcarLeida = useMarcarLeida();
  const resolver = useResolverManual();

  const alertas = data?.items ?? [];
  const totalPaginas = data ? Math.max(1, Math.ceil(data.total / data.tamano_pagina)) : 1;

  function cambiarFiltro(valor: EstadoAlerta | "todas") {
    setFiltroEstado(valor);
    setPagina(1);
  }

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Centro de alertas</h1>
          <p className="text-sm text-ink-soft">
            Vencimientos de calibración, documentos y mantenimientos, más cambios de estado de equipos.
          </p>
        </div>
        <div className="w-48">
          <Select
            label="Estado"
            value={filtroEstado}
            onChange={(e) => cambiarFiltro(e.target.value as EstadoAlerta | "todas")}
          >
            <option value="activa">Activas</option>
            <option value="resuelta">Resueltas</option>
            <option value="todas">Todas</option>
          </Select>
        </div>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
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

      {!isLoading && !isError && alertas.length === 0 && (
        <EmptyState icon={Bell} title="Sin alertas" description="No hay alertas para este filtro." />
      )}

      {!isError && !!alertas.length && (
        <>
          <div className="space-y-2">
            {alertas.map((alerta) => (
              <AlertaItem
                key={alerta.id}
                alerta={alerta}
                onMarcarLeida={(id) => marcarLeida.mutate(id)}
                onResolver={(id) => resolver.mutate(id)}
              />
            ))}
          </div>

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
