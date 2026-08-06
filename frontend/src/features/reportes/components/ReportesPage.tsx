import { AlertCircle, CheckCircle2, Clock3, Download, FileBarChart, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { useAreas, useCategorias, useEquipos } from "@/features/equipos/hooks/useEquipos";
import { ESTADOS_OPERATIVOS, ETIQUETAS_ESTADO } from "@/features/equipos/types";
import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Input } from "@/shared/components/ui/input";
import { Select } from "@/shared/components/ui/select";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useDescargarReporte, useGenerarReporte, useHistorialReportes, useTiposReporte } from "../hooks/useReportes";
import type { EstadoReporte, FiltrosReporte, FormatoReporte, ReporteGenerado, TipoReporte } from "../types";
import { ETIQUETAS_ESTADO_REPORTE, ETIQUETAS_FORMATO } from "../types";

const VARIANTE_BADGE_ESTADO: Record<EstadoReporte, "neutral" | "warning" | "success" | "danger"> = {
  pendiente: "neutral",
  procesando: "warning",
  listo: "success",
  fallido: "danger",
};

const ICONO_ESTADO: Record<EstadoReporte, typeof Clock3> = {
  pendiente: Clock3,
  procesando: Loader2,
  listo: CheckCircle2,
  fallido: AlertCircle,
};

function formatearFecha(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

export function ReportesPage() {
  const { data: tipos, isLoading: cargandoTipos } = useTiposReporte();
  const { data: historial, isLoading: cargandoHistorial } = useHistorialReportes();
  const { data: categorias } = useCategorias();
  const { data: areas } = useAreas();
  const { data: paginaEquipos } = useEquipos({});
  const generar = useGenerarReporte();
  const descargar = useDescargarReporte();

  const [tipo, setTipo] = useState<TipoReporte | "">("");
  const [formato, setFormato] = useState<FormatoReporte | "">("");
  const [filtros, setFiltros] = useState<FiltrosReporte>({});
  const [mensaje, setMensaje] = useState<{ tono: "exito" | "error" | "info"; texto: string } | null>(null);
  const [descargandoId, setDescargandoId] = useState<string | null>(null);

  const tipoInfo = useMemo(() => tipos?.find((t) => t.tipo === tipo), [tipos, tipo]);
  const equipos = paginaEquipos?.items ?? [];

  useEffect(() => {
    if (tipo || !tipos || tipos.length === 0) return;
    setTipo(tipos[0]!.tipo);
  }, [tipos, tipo]);

  useEffect(() => {
    if (!tipoInfo) return;
    const primerFormato = tipoInfo.formatos_disponibles[0];
    if (primerFormato && (!formato || !tipoInfo.formatos_disponibles.includes(formato as FormatoReporte))) {
      setFormato(primerFormato);
    }
  }, [tipoInfo, formato]);

  useEffect(() => {
    setFiltros({});
  }, [tipo]);

  function actualizarFiltro<K extends keyof FiltrosReporte>(clave: K, valor: string) {
    setFiltros((actuales) => ({ ...actuales, [clave]: valor || undefined }));
  }

  async function generarReporte() {
    if (!tipo || !formato) return;
    if (tipo === "paquete_auditoria" && !filtros.equipo_id) {
      setMensaje({ tono: "error", texto: "Selecciona un equipo para el paquete de auditoría." });
      return;
    }
    setMensaje(null);
    try {
      const resultado = await generar.mutateAsync({ tipo, formato, filtros });
      if (resultado.estado === "listo" && resultado.nombre_archivo) {
        setMensaje({ tono: "exito", texto: "Reporte generado — descarga en curso." });
        await descargar.mutateAsync({ id: resultado.id, nombreArchivo: resultado.nombre_archivo });
      } else {
        setMensaje({
          tono: "info",
          texto: "El reporte es grande y se está generando en segundo plano. Te avisaremos cuando esté listo.",
        });
      }
    } catch (error) {
      setMensaje({
        tono: "error",
        texto: error instanceof ApiError ? error.message : "No se pudo generar el reporte.",
      });
    }
  }

  async function descargarDeHistorial(reporte: ReporteGenerado) {
    if (!reporte.nombre_archivo) return;
    setDescargandoId(reporte.id);
    try {
      await descargar.mutateAsync({ id: reporte.id, nombreArchivo: reporte.nombre_archivo });
    } finally {
      setDescargandoId(null);
    }
  }

  return (
    <div className="p-6 sm:p-8">
      <div className="mb-6">
        <h1 className="mb-1 font-display text-2xl font-semibold text-ink">Reportes</h1>
        <p className="text-sm text-ink-soft">
          Genera y descarga reportes de inventario, calibraciones, mantenimiento y trazabilidad documental.
        </p>
      </div>

      <div className="mb-8 rounded-lg border border-border bg-surface p-5">
        <h2 className="mb-4 font-display text-base font-semibold text-ink">Generar nuevo reporte</h2>

        {cargandoTipos ? (
          <Skeleton className="h-11 w-full" />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Select label="Tipo de reporte" value={tipo} onChange={(e) => setTipo(e.target.value as TipoReporte)}>
              {tipos?.map((t) => (
                <option key={t.tipo} value={t.tipo}>
                  {t.etiqueta}
                </option>
              ))}
            </Select>

            <Select label="Formato" value={formato} onChange={(e) => setFormato(e.target.value as FormatoReporte)}>
              {tipoInfo?.formatos_disponibles.map((f) => (
                <option key={f} value={f}>
                  {ETIQUETAS_FORMATO[f]}
                </option>
              ))}
            </Select>

            {tipo === "inventario" && (
              <>
                <Select
                  label="Categoría"
                  value={filtros.categoria_id ?? ""}
                  onChange={(e) => actualizarFiltro("categoria_id", e.target.value)}
                >
                  <option value="">Todas</option>
                  {categorias?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </Select>
                <Select
                  label="Área"
                  value={filtros.area_id ?? ""}
                  onChange={(e) => actualizarFiltro("area_id", e.target.value)}
                >
                  <option value="">Todas</option>
                  {areas?.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.nombre}
                    </option>
                  ))}
                </Select>
                <Select
                  label="Estado operativo"
                  value={filtros.estado_operativo ?? ""}
                  onChange={(e) => actualizarFiltro("estado_operativo", e.target.value)}
                >
                  <option value="">Todos</option>
                  {ESTADOS_OPERATIVOS.map((e) => (
                    <option key={e} value={e}>
                      {ETIQUETAS_ESTADO[e]}
                    </option>
                  ))}
                </Select>
              </>
            )}

            {tipo === "mantenimiento" && (
              <>
                <Select
                  label="Equipo"
                  value={filtros.equipo_id ?? ""}
                  onChange={(e) => actualizarFiltro("equipo_id", e.target.value)}
                >
                  <option value="">Todos</option>
                  {equipos.map((eq) => (
                    <option key={eq.id} value={eq.id}>
                      {eq.codigo_interno} · {eq.nombre}
                    </option>
                  ))}
                </Select>
                <Input
                  label="Desde"
                  type="date"
                  value={filtros.desde?.slice(0, 10) ?? ""}
                  onChange={(e) => actualizarFiltro("desde", e.target.value)}
                />
                <Input
                  label="Hasta"
                  type="date"
                  value={filtros.hasta?.slice(0, 10) ?? ""}
                  onChange={(e) => actualizarFiltro("hasta", e.target.value)}
                />
              </>
            )}

            {tipo === "paquete_auditoria" && (
              <Select
                label="Equipo (obligatorio)"
                value={filtros.equipo_id ?? ""}
                onChange={(e) => actualizarFiltro("equipo_id", e.target.value)}
              >
                <option value="">Selecciona un equipo</option>
                {equipos.map((eq) => (
                  <option key={eq.id} value={eq.id}>
                    {eq.codigo_interno} · {eq.nombre}
                  </option>
                ))}
              </Select>
            )}

            {tipo === "cumplimiento" && (
              <Input
                label="Meses de historial"
                type="number"
                min={1}
                max={36}
                placeholder="12"
                value={filtros.meses ?? ""}
                onChange={(e) =>
                  setFiltros((actuales) => ({
                    ...actuales,
                    meses: e.target.value ? Number(e.target.value) : undefined,
                  }))
                }
              />
            )}
          </div>
        )}

        <div className="mt-2 flex flex-wrap items-center gap-3">
          <Button cargando={generar.isPending || descargar.isPending} onClick={generarReporte}>
            <FileBarChart className="h-4 w-4" aria-hidden="true" />
            Generar reporte
          </Button>
          {mensaje && (
            <p
              role="status"
              aria-live="polite"
              className={
                mensaje.tono === "error"
                  ? "text-sm font-medium text-danger"
                  : mensaje.tono === "exito"
                    ? "text-sm font-medium text-[#065F46]"
                    : "text-sm font-medium text-ink-soft"
              }
            >
              {mensaje.texto}
            </p>
          )}
        </div>
      </div>

      <h2 className="mb-4 font-display text-base font-semibold text-ink">Historial</h2>

      {cargandoHistorial && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {!cargandoHistorial && historial?.length === 0 && (
        <EmptyState
          icon={FileBarChart}
          title="Sin reportes todavía"
          description="Genera tu primer reporte con el panel de arriba."
        />
      )}

      {!!historial?.length && (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-alt text-xs font-semibold uppercase tracking-wide text-ink-soft">
              <tr>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Formato</th>
                <th className="px-3 py-2">Estado</th>
                <th className="px-3 py-2">Solicitado</th>
                <th className="px-3 py-2">Completado</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {historial.map((reporte) => {
                const Icono = ICONO_ESTADO[reporte.estado];
                const etiquetaTipo = tipos?.find((t) => t.tipo === reporte.tipo)?.etiqueta ?? reporte.tipo;
                return (
                  <tr key={reporte.id} className="bg-surface">
                    <td className="px-3 py-2 text-ink">{etiquetaTipo}</td>
                    <td className="px-3 py-2 text-ink-soft">{ETIQUETAS_FORMATO[reporte.formato]}</td>
                    <td className="px-3 py-2">
                      <Badge variant={VARIANTE_BADGE_ESTADO[reporte.estado]} title={reporte.error ?? undefined}>
                        <Icono
                          className={`h-3 w-3 ${reporte.estado === "procesando" ? "animate-spin" : ""}`}
                          aria-hidden="true"
                        />
                        {ETIQUETAS_ESTADO_REPORTE[reporte.estado]}
                      </Badge>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-ink-soft">{formatearFecha(reporte.creado_en)}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-ink-soft">{formatearFecha(reporte.completado_en)}</td>
                    <td className="px-3 py-2 text-right">
                      {reporte.estado === "listo" && (
                        <Button
                          size="sm"
                          variant="secondary"
                          cargando={descargandoId === reporte.id}
                          onClick={() => descargarDeHistorial(reporte)}
                        >
                          <Download className="h-4 w-4" aria-hidden="true" />
                          Descargar
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
