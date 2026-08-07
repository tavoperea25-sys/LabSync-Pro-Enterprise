import { ClipboardList, Download, Plus, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";

import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { LinkButton } from "@/shared/components/ui/link-button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";

import { EquipoEstadoBadge } from "./EquipoEstadoBadge";
import { useAreas, useCategorias, useEquipos, useExportarEquipos } from "../hooks/useEquipos";
import { ESTADOS_OPERATIVOS, ETIQUETAS_ESTADO } from "../types";

const CLASE_SELECT =
  "h-10 rounded-md border border-border bg-surface px-3 text-sm text-ink outline-none transition-colors " +
  "duration-fast focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15";

export function EquiposListPage() {
  const navigate = useNavigate();
  const [busqueda, setBusqueda] = useState("");
  const [categoriaId, setCategoriaId] = useState("");
  const [areaId, setAreaId] = useState("");
  const [estado, setEstado] = useState("");
  const [pagina, setPagina] = useState(1);

  const qDebounced = useDebouncedValue(busqueda);
  const { data: categorias } = useCategorias();
  const { data: areas } = useAreas();
  const filtrosActuales = {
    q: qDebounced || undefined,
    categoria_id: categoriaId || undefined,
    area_id: areaId || undefined,
    estado_operativo: estado || undefined,
    pagina,
  };
  const { data, isLoading, isError } = useEquipos(filtrosActuales);
  const exportar = useExportarEquipos();

  const totalPaginas = data ? Math.max(1, Math.ceil(data.total / data.tamano_pagina)) : 1;

  function limpiarFiltrosYRecargarPagina() {
    setPagina(1);
  }

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-2xl font-semibold text-ink">Equipos</h1>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            cargando={exportar.isPending}
            onClick={() => exportar.mutate(filtrosActuales)}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            Exportar
          </Button>
          <LinkButton to="/equipos/nuevo">
            <Plus className="h-4 w-4" aria-hidden="true" />
            Nuevo equipo
          </LinkButton>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap gap-2.5">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-soft" aria-hidden="true" />
          <input
            type="search"
            value={busqueda}
            onChange={(e) => {
              setBusqueda(e.target.value);
              limpiarFiltrosYRecargarPagina();
            }}
            placeholder="Buscar por código, nombre o número de serie…"
            aria-label="Buscar equipos"
            className="h-10 w-full rounded-md border border-border bg-surface pl-9 pr-3 text-sm text-ink outline-none transition-colors duration-fast placeholder:text-ink-soft focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
          />
        </div>

        <select
          value={categoriaId}
          onChange={(e) => {
            setCategoriaId(e.target.value);
            limpiarFiltrosYRecargarPagina();
          }}
          aria-label="Filtrar por categoría"
          className={CLASE_SELECT}
        >
          <option value="">Toda categoría</option>
          {categorias?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.nombre}
            </option>
          ))}
        </select>

        <select
          value={areaId}
          onChange={(e) => {
            setAreaId(e.target.value);
            limpiarFiltrosYRecargarPagina();
          }}
          aria-label="Filtrar por área"
          className={CLASE_SELECT}
        >
          <option value="">Toda área</option>
          {areas?.map((a) => (
            <option key={a.id} value={a.id}>
              {a.nombre}
            </option>
          ))}
        </select>

        <select
          value={estado}
          onChange={(e) => {
            setEstado(e.target.value);
            limpiarFiltrosYRecargarPagina();
          }}
          aria-label="Filtrar por estado operativo"
          className={CLASE_SELECT}
        >
          <option value="">Todo estado</option>
          {ESTADOS_OPERATIVOS.map((e) => (
            <option key={e} value={e}>
              {ETIQUETAS_ESTADO[e]}
            </option>
          ))}
        </select>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}

      {isError && (
        <EmptyState
          icon={ClipboardList}
          title="No se pudo cargar el listado"
          description="Intenta de nuevo en unos segundos."
        />
      )}

      {!isLoading && !isError && data && data.items.length === 0 && (
        <EmptyState
          icon={ClipboardList}
          title="Sin equipos todavía"
          description="Registra el primer equipo del laboratorio para empezar a llevar su trazabilidad."
          action={
            <LinkButton to="/equipos/nuevo" size="sm" className="mt-1">
              <Plus className="h-4 w-4" aria-hidden="true" />
              Nuevo equipo
            </LinkButton>
          }
        />
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <>
          {/* Tabla — desktop/tablet */}
          <div className="hidden overflow-hidden rounded-lg border border-border md:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface-alt text-left text-xs font-semibold uppercase tracking-wide text-ink-soft">
                  <th scope="col" className="px-4 py-3">Código</th>
                  <th scope="col" className="px-4 py-3">Nombre</th>
                  <th scope="col" className="px-4 py-3">Marca / Modelo</th>
                  <th scope="col" className="px-4 py-3">Estado</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((equipo) => (
                  <tr
                    key={equipo.id}
                    tabIndex={0}
                    role="button"
                    onClick={() => navigate(`/equipos/${equipo.id}`)}
                    onKeyDown={(e) => e.key === "Enter" && navigate(`/equipos/${equipo.id}`)}
                    className="cursor-pointer border-b border-border last:border-0 hover:bg-surface-alt focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary-900"
                  >
                    <td className="px-4 py-3 font-medium text-ink">{equipo.codigo_interno}</td>
                    <td className="px-4 py-3 text-ink">{equipo.nombre}</td>
                    <td className="px-4 py-3 text-ink-soft">
                      {[equipo.marca, equipo.modelo].filter(Boolean).join(" / ") || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <EquipoEstadoBadge estado={equipo.estado_operativo} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Tarjetas — mobile */}
          <ul className="space-y-2.5 md:hidden">
            {data.items.map((equipo) => (
              <li key={equipo.id}>
                <button
                  type="button"
                  onClick={() => navigate(`/equipos/${equipo.id}`)}
                  className="w-full rounded-lg border border-border bg-surface p-4 text-left transition-colors duration-fast hover:bg-surface-alt"
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-ink-soft">{equipo.codigo_interno}</span>
                    <EquipoEstadoBadge estado={equipo.estado_operativo} />
                  </div>
                  <p className="font-medium text-ink">{equipo.nombre}</p>
                  {(equipo.marca || equipo.modelo) && (
                    <p className="text-sm text-ink-soft">{[equipo.marca, equipo.modelo].filter(Boolean).join(" / ")}</p>
                  )}
                </button>
              </li>
            ))}
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
