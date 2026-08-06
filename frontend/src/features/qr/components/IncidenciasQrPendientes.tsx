import { MessageSquareWarning } from "lucide-react";

import { Badge } from "@/shared/components/ui/badge";
import { Button } from "@/shared/components/ui/button";

import { useActualizarEstadoIncidencia, useIncidenciasQr } from "../hooks/useIncidenciasQr";
import type { EstadoIncidencia, IncidenciaQr } from "../types";

const VARIANTE_POR_ESTADO: Record<EstadoIncidencia, "warning" | "info" | "success"> = {
  pendiente: "warning",
  en_revision: "info",
  resuelta: "success",
};

const ETIQUETA_POR_ESTADO: Record<EstadoIncidencia, string> = {
  pendiente: "Pendiente de triage",
  en_revision: "En revisión",
  resuelta: "Resuelta",
};

const SIGUIENTE_ESTADO: Partial<Record<EstadoIncidencia, EstadoIncidencia>> = {
  pendiente: "en_revision",
  en_revision: "resuelta",
};

const ETIQUETA_ACCION: Partial<Record<EstadoIncidencia, string>> = {
  pendiente: "Marcar en revisión",
  en_revision: "Marcar resuelta",
};

/** RF-QR-03 "Salidas" — una incidencia reportada desde la vista pública de
 * QR (sin autenticación) debe quedar "visible luego en el módulo de
 * Mantenimientos como solicitud pendiente de triage". Solo muestra
 * pendientes/en revisión — las resueltas no necesitan ocupar espacio aquí. */
export function IncidenciasQrPendientes() {
  const { data: incidencias, isLoading } = useIncidenciasQr();
  const actualizarEstado = useActualizarEstadoIncidencia();

  const pendientes = (incidencias ?? []).filter((i) => i.estado !== "resuelta");

  if (isLoading || pendientes.length === 0) return null;

  function avanzarEstado(incidencia: IncidenciaQr) {
    const siguiente = SIGUIENTE_ESTADO[incidencia.estado];
    if (siguiente) actualizarEstado.mutate({ id: incidencia.id, estado: siguiente });
  }

  return (
    <div className="mb-6 overflow-hidden rounded-lg border border-border">
      <div className="flex items-center gap-2 border-b border-border bg-surface-alt px-4 py-3">
        <MessageSquareWarning className="h-4 w-4 text-warning" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-ink">
          Incidencias reportadas por QR ({pendientes.length})
        </h2>
      </div>
      <ul className="divide-y divide-border">
        {pendientes.map((incidencia) => (
          <li key={incidencia.id} className="flex items-start justify-between gap-3 bg-surface px-4 py-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold text-ink-soft">
                {incidencia.equipo_codigo_interno} · {incidencia.equipo_nombre}
              </p>
              <p className="text-sm text-ink">{incidencia.descripcion}</p>
              {incidencia.contacto_nombre && (
                <p className="text-xs text-ink-soft">
                  Reportado por {incidencia.contacto_nombre}
                  {incidencia.contacto_medio && ` · ${incidencia.contacto_medio}`}
                </p>
              )}
            </div>
            <div className="flex shrink-0 flex-col items-end gap-2">
              <Badge variant={VARIANTE_POR_ESTADO[incidencia.estado]}>
                {ETIQUETA_POR_ESTADO[incidencia.estado]}
              </Badge>
              {SIGUIENTE_ESTADO[incidencia.estado] && (
                <Button
                  size="sm"
                  variant="secondary"
                  cargando={
                    actualizarEstado.isPending && actualizarEstado.variables?.id === incidencia.id
                  }
                  onClick={() => avanzarEstado(incidencia)}
                >
                  {ETIQUETA_ACCION[incidencia.estado]}
                </Button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
