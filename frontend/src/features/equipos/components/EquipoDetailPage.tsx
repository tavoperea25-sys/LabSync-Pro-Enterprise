import { ArrowLeft, Check, Copy, FileText, Files, Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { CalibracionesSection } from "@/features/calibraciones/components/CalibracionesSection";
import { MantenimientosSection } from "@/features/mantenimientos/components/MantenimientosSection";
import { Button } from "@/shared/components/ui/button";
import { LinkButton } from "@/shared/components/ui/link-button";

import { EquipoEstadoBadge } from "./EquipoEstadoBadge";
import {
  useAreas,
  useCategorias,
  useDuplicarEquipo,
  useEliminarEquipo,
  useEquipo,
  useHistorialEquipo,
  useQrImagenUrl,
  useQrInfo,
} from "../hooks/useEquipos";
import { ETIQUETAS_ACCION } from "../types";

function Campo({ etiqueta, valor }: { etiqueta: string; valor: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-ink-soft">{etiqueta}</dt>
      <dd className="mt-0.5 text-sm text-ink">{valor || "—"}</dd>
    </div>
  );
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

function camposCambiados(
  anterior: Record<string, unknown> | null,
  nuevo: Record<string, unknown> | null,
): string[] {
  if (!anterior || !nuevo) return [];
  return Object.keys(nuevo).filter((clave) => JSON.stringify(anterior[clave]) !== JSON.stringify(nuevo[clave]));
}

function SeccionQr({ equipoId }: { equipoId: string }) {
  const { data: qrInfo } = useQrInfo(equipoId);
  const imagenUrl = useQrImagenUrl(equipoId);
  const [copiado, setCopiado] = useState(false);

  async function copiarEnlace() {
    if (!qrInfo) return;
    await navigator.clipboard.writeText(qrInfo.url_publica);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2000);
  }

  return (
    <div className="mt-4 rounded-lg border border-border p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-soft">Código QR</h2>
      <div className="flex flex-wrap items-center gap-4">
        {imagenUrl ? (
          <img
            src={imagenUrl}
            alt={`Código QR de consulta pública para este equipo`}
            className="h-28 w-28 rounded-md border border-border bg-white p-1.5"
          />
        ) : (
          <div className="h-28 w-28 animate-pulse rounded-md bg-surface-alt" aria-hidden="true" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-sm text-ink-soft">
            Cualquier persona con este enlace puede ver la ficha pública del equipo y reportar una
            incidencia, sin necesidad de iniciar sesión.
          </p>
          {qrInfo && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <a
                href={qrInfo.url_publica}
                target="_blank"
                rel="noreferrer"
                className="truncate text-sm font-medium text-primary-900 underline underline-offset-2"
              >
                {qrInfo.url_publica}
              </a>
              <Button variant="secondary" size="sm" onClick={copiarEnlace}>
                {copiado ? (
                  <Check className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Copy className="h-4 w-4" aria-hidden="true" />
                )}
                {copiado ? "Copiado" : "Copiar enlace"}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SeccionHistorial({ equipoId }: { equipoId: string }) {
  const { data: historial, isLoading } = useHistorialEquipo(equipoId);

  return (
    <div className="mt-4 rounded-lg border border-border p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink-soft">Historial de cambios</h2>
      {isLoading && <p className="text-sm text-ink-soft">Cargando historial…</p>}
      {!isLoading && historial && historial.length === 0 && (
        <p className="text-sm text-ink-soft">Aún no hay movimientos registrados.</p>
      )}
      {!isLoading && historial && historial.length > 0 && (
        <ol className="space-y-3">
          {historial.map((entrada) => {
            const cambios = camposCambiados(entrada.valor_anterior, entrada.valor_nuevo);
            return (
              <li key={entrada.id} className="border-l-2 border-primary-tint pl-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium text-ink">
                    {ETIQUETAS_ACCION[entrada.accion] ?? entrada.accion}
                  </span>
                  <span className="text-xs text-ink-soft">{formatearFecha(entrada.creado_en)}</span>
                </div>
                {cambios.length > 0 && (
                  <p className="mt-0.5 text-xs text-ink-soft">Campos modificados: {cambios.join(", ")}</p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

export function EquipoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: equipo, isLoading } = useEquipo(id);
  const { data: categorias } = useCategorias();
  const { data: areas } = useAreas();
  const eliminar = useEliminarEquipo();
  const duplicar = useDuplicarEquipo();
  const [confirmandoEliminar, setConfirmandoEliminar] = useState(false);

  if (isLoading) {
    return <div className="p-8 text-sm text-ink-soft">Cargando equipo…</div>;
  }

  if (!equipo) {
    return <div className="p-8 text-sm text-ink-soft">Este equipo no existe o fue eliminado.</div>;
  }

  const categoria = categorias?.find((c) => c.id === equipo.categoria_id)?.nombre;
  const area = areas?.find((a) => a.id === equipo.area_id)?.nombre;

  async function confirmarEliminacion() {
    if (!id) return;
    await eliminar.mutateAsync(id);
    navigate("/equipos");
  }

  async function duplicarEquipo() {
    if (!id) return;
    const copia = await duplicar.mutateAsync(id);
    navigate(`/equipos/${copia.id}`);
  }

  return (
    <div className="mx-auto max-w-2xl p-6 sm:p-8">
      <button
        type="button"
        onClick={() => navigate("/equipos")}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-ink-soft hover:text-ink"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Volver a Equipos
      </button>

      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-4">
          {equipo.foto_url && (
            <img
              src={equipo.foto_url}
              alt={`Fotografía de ${equipo.nombre}`}
              className="h-16 w-16 flex-shrink-0 rounded-md border border-border object-cover"
            />
          )}
          <div>
            <p className="text-xs font-semibold text-ink-soft">{equipo.codigo_interno}</p>
            <h1 className="font-display text-2xl font-semibold text-ink">{equipo.nombre}</h1>
            <div className="mt-2">
              <EquipoEstadoBadge estado={equipo.estado_operativo} />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" cargando={duplicar.isPending} onClick={duplicarEquipo}>
            <Files className="h-4 w-4" aria-hidden="true" />
            Duplicar
          </Button>
          <LinkButton to={`/equipos/${equipo.id}/editar`} variant="secondary" size="sm">
            <Pencil className="h-4 w-4" aria-hidden="true" />
            Editar
          </LinkButton>
          <Button variant="destructive" size="sm" onClick={() => setConfirmandoEliminar(true)}>
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Eliminar
          </Button>
        </div>
      </div>

      {confirmandoEliminar && (
        <div role="alertdialog" aria-labelledby="titulo-confirmar-eliminar" className="mb-6 rounded-md border border-danger/30 bg-[#FEF2F2] p-4">
          <p id="titulo-confirmar-eliminar" className="mb-1 text-sm font-semibold text-[#991B1B]">
            ¿Eliminar este equipo?
          </p>
          <p className="mb-3 text-sm text-[#7F1D1D]">
            El equipo se archivará y dejará de aparecer en los listados. Su historial se conserva.
          </p>
          <div className="flex gap-2">
            <Button variant="destructive" size="sm" cargando={eliminar.isPending} onClick={confirmarEliminacion}>
              Sí, eliminar
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setConfirmandoEliminar(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      <dl className="grid grid-cols-1 gap-x-4 gap-y-4 rounded-lg border border-border p-5 sm:grid-cols-2">
        <Campo etiqueta="Categoría" valor={categoria} />
        <Campo etiqueta="Área" valor={area} />
        <Campo etiqueta="Marca" valor={equipo.marca} />
        <Campo etiqueta="Modelo" valor={equipo.modelo} />
        <Campo etiqueta="Número de serie" valor={equipo.numero_serie} />
        <Campo etiqueta="Fabricante" valor={equipo.fabricante} />
        <Campo etiqueta="Proveedor" valor={equipo.proveedor} />
        <Campo etiqueta="Fecha de adquisición" valor={equipo.fecha_adquisicion} />
      </dl>

      {equipo.manual_url && (
        <a
          href={equipo.manual_url}
          target="_blank"
          rel="noreferrer"
          className="mt-4 flex items-center gap-2 rounded-lg border border-border p-4 text-sm font-medium text-primary-900 underline-offset-2 hover:underline"
        >
          <FileText className="h-4 w-4" aria-hidden="true" />
          Descargar manual de usuario
        </a>
      )}

      {equipo.observaciones && (
        <div className="mt-4 rounded-lg border border-border p-5">
          <h2 className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-soft">Observaciones</h2>
          <p className="text-sm text-ink">{equipo.observaciones}</p>
        </div>
      )}

      <div className="mt-4">
        <CalibracionesSection equipoId={equipo.id} />
      </div>

      <div className="mt-4">
        <MantenimientosSection equipoId={equipo.id} />
      </div>

      <SeccionQr equipoId={equipo.id} />
      <SeccionHistorial equipoId={equipo.id} />
    </div>
  );
}
