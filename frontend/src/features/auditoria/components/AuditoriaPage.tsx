import { AlertTriangle, Download, History } from "lucide-react";
import { useState } from "react";

import { useUsuarios } from "@/features/usuarios/hooks/useUsuarios";
import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Select } from "@/shared/components/ui/select";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useAuditoria, useExportarAuditoria, useValoresFiltro } from "../hooks/useAuditoria";
import type { FiltrosAuditoria, FormatoExportacion } from "../types";

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

export function AuditoriaPage() {
  const [filtros, setFiltros] = useState<FiltrosAuditoria>({});
  const { data: valoresFiltro } = useValoresFiltro();
  // Máximo permitido (ver TAMANO_PAGINA_MAXIMO en el backend) para poblar
  // el selector con todos los usuarios del laboratorio — un límite
  // razonable para el tamaño real de un laboratorio (RNF-ESC), no una
  // paginación propia de este selector.
  const { data: usuariosPagina } = useUsuarios(1, 100);
  const usuarios = usuariosPagina?.items;
  const { data, isLoading, isError } = useAuditoria(filtros);
  const logs = data?.items;
  const totalPaginas = data ? Math.max(1, Math.ceil(data.total / data.tamano_pagina)) : 1;
  const exportar = useExportarAuditoria();

  function actualizarFiltro<K extends keyof FiltrosAuditoria>(clave: K, valor: string) {
    setFiltros((actuales) => ({ ...actuales, [clave]: valor || undefined, pagina: 1 }));
  }

  function exportarComo(formato: FormatoExportacion) {
    exportar.mutate({ formato, filtros });
  }

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Auditoría</h1>
          <p className="text-sm text-ink-soft">
            Bitácora completa de creación, edición y eliminación — filtra e investiga una acción específica.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="secondary"
            cargando={exportar.isPending}
            onClick={() => exportarComo("csv")}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            CSV
          </Button>
          <Button
            size="sm"
            variant="secondary"
            cargando={exportar.isPending}
            onClick={() => exportarComo("xlsx")}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Excel
          </Button>
          <Button
            size="sm"
            variant="secondary"
            cargando={exportar.isPending}
            onClick={() => exportarComo("pdf")}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            PDF
          </Button>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <Select label="Usuario" value={filtros.usuario_id ?? ""} onChange={(e) => actualizarFiltro("usuario_id", e.target.value)}>
          <option value="">Todos</option>
          {usuarios?.map((u) => (
            <option key={u.id} value={u.id}>
              {u.nombre_completo}
            </option>
          ))}
        </Select>
        <Select label="Módulo" value={filtros.modulo ?? ""} onChange={(e) => actualizarFiltro("modulo", e.target.value)}>
          <option value="">Todos</option>
          {valoresFiltro?.modulos.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </Select>
        <Select label="Acción" value={filtros.accion ?? ""} onChange={(e) => actualizarFiltro("accion", e.target.value)}>
          <option value="">Todas</option>
          {valoresFiltro?.acciones.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </Select>
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-ink-soft" htmlFor="auditoria-desde">
            Desde
          </label>
          <input
            id="auditoria-desde"
            type="date"
            className="h-11 w-full rounded-sm border border-border bg-surface px-4 text-sm text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
            value={filtros.desde?.slice(0, 10) ?? ""}
            onChange={(e) => actualizarFiltro("desde", e.target.value ? `${e.target.value}T00:00:00Z` : "")}
          />
        </div>
        <div className="mb-4">
          <label className="mb-1.5 block text-sm font-semibold text-ink-soft" htmlFor="auditoria-hasta">
            Hasta
          </label>
          <input
            id="auditoria-hasta"
            type="date"
            className="h-11 w-full rounded-sm border border-border bg-surface px-4 text-sm text-ink outline-none focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
            value={filtros.hasta?.slice(0, 10) ?? ""}
            onChange={(e) => actualizarFiltro("hasta", e.target.value ? `${e.target.value}T23:59:59Z` : "")}
          />
        </div>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
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

      {!isLoading && !isError && logs?.length === 0 && (
        <EmptyState icon={History} title="Sin registros" description="No hay eventos para estos filtros." />
      )}

      {!isError && !!logs?.length && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-alt text-xs font-semibold uppercase tracking-wide text-ink-soft">
              <tr>
                <th className="px-3 py-2">Fecha</th>
                <th className="px-3 py-2">Módulo</th>
                <th className="px-3 py-2">Acción</th>
                <th className="px-3 py-2">Entidad</th>
                <th className="px-3 py-2">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {logs.map((log) => (
                <tr key={log.id} className="bg-surface">
                  <td className="whitespace-nowrap px-3 py-2 text-ink-soft">{formatearFecha(log.creado_en)}</td>
                  <td className="px-3 py-2 text-ink">{log.modulo}</td>
                  <td className="px-3 py-2 text-ink">{log.accion}</td>
                  <td className="px-3 py-2 text-ink-soft">{log.entidad_tipo}</td>
                  <td className="px-3 py-2 text-ink-soft">{log.ip_origen ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!isError && totalPaginas > 1 && (
        <div className="mt-5 flex items-center justify-center gap-3 text-sm text-ink-soft">
          <Button
            variant="secondary"
            size="sm"
            disabled={(filtros.pagina ?? 1) <= 1}
            onClick={() => setFiltros((actuales) => ({ ...actuales, pagina: (actuales.pagina ?? 1) - 1 }))}
          >
            Anterior
          </Button>
          <span>
            Página {filtros.pagina ?? 1} de {totalPaginas}
          </span>
          <Button
            variant="secondary"
            size="sm"
            disabled={(filtros.pagina ?? 1) >= totalPaginas}
            onClick={() => setFiltros((actuales) => ({ ...actuales, pagina: (actuales.pagina ?? 1) + 1 }))}
          >
            Siguiente
          </Button>
        </div>
      )}
    </div>
  );
}
