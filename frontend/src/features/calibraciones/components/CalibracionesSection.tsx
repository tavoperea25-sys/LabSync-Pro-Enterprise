import { AlertTriangle, Download, Pencil, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

import * as api from "../api/calibracionesApi";
import { useCalibracionesPorEquipo, useCorregirCalibracion, useCrearCalibracion } from "../hooks/useCalibraciones";
import { ETIQUETAS_RESULTADO, type Calibracion, type DatosCalibracion } from "../types";
import { CalibracionFormulario } from "./CalibracionFormulario";
import { SemaforoBadge } from "./SemaforoBadge";
import { TendenciaCalibraciones } from "./TendenciaCalibraciones";

export function CalibracionesSection({ equipoId }: { equipoId: string }) {
  const { data: calibraciones, isLoading } = useCalibracionesPorEquipo(equipoId);
  const crear = useCrearCalibracion(equipoId);
  const corregir = useCorregirCalibracion(equipoId);

  const [mostrandoFormulario, setMostrandoFormulario] = useState(false);
  const [corrigiendo, setCorrigiendo] = useState<Calibracion | null>(null);

  async function descargarCertificado(id: string) {
    const { url } = await api.obtenerUrlCertificado(id);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function guardar(datos: DatosCalibracion & { motivo?: string }) {
    if (corrigiendo) {
      await corregir.mutateAsync({ id: corrigiendo.id, datos: { ...datos, motivo: datos.motivo ?? "" } });
    } else {
      await crear.mutateAsync(datos);
    }
    setMostrandoFormulario(false);
    setCorrigiendo(null);
  }

  const semaforoActual = calibraciones?.[0]?.semaforo;

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Calibraciones</h2>
          {semaforoActual && <SemaforoBadge semaforo={semaforoActual} />}
        </div>
        {!mostrandoFormulario && (
          <Button
            size="sm"
            onClick={() => {
              setCorrigiendo(null);
              setMostrandoFormulario(true);
            }}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Registrar calibración
          </Button>
        )}
      </div>

      {mostrandoFormulario && (
        <div className="mb-4">
          <CalibracionFormulario
            equipoId={equipoId}
            corrigiendo={corrigiendo ?? undefined}
            guardando={crear.isPending || corregir.isPending}
            onGuardar={guardar}
            onCancelar={() => {
              setMostrandoFormulario(false);
              setCorrigiendo(null);
            }}
          />
        </div>
      )}

      {isLoading && <Skeleton className="h-32 w-full" />}

      {!isLoading && calibraciones && (
        <>
          <div className="mb-4">
            <TendenciaCalibraciones calibraciones={calibraciones} />
          </div>

          {calibraciones.length > 0 && (
            <ul className="space-y-2">
              {calibraciones.map((calibracion) => (
                <li key={calibracion.id} className="rounded-md border border-border p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-ink">
                        {calibracion.fecha_calibracion} · próxima: {calibracion.proxima_fecha}
                      </p>
                      <p className="text-xs text-ink-soft">
                        {ETIQUETAS_RESULTADO[calibracion.resultado]}
                        {calibracion.laboratorio_proveedor && ` · ${calibracion.laboratorio_proveedor}`}
                        {calibracion.corrige_a_id && " · corrección"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <SemaforoBadge semaforo={calibracion.semaforo} />
                      {calibracion.tiene_certificado && (
                        <Button
                          variant="secondary"
                          size="sm"
                          title="Descargar certificado"
                          onClick={() => descargarCertificado(calibracion.id)}
                        >
                          <Download className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      )}
                      {!calibracion.corrige_a_id && (
                        <Button
                          variant="secondary"
                          size="sm"
                          title="Corregir este registro"
                          aria-label="Corregir este registro"
                          onClick={() => {
                            setCorrigiendo(calibracion);
                            setMostrandoFormulario(true);
                          }}
                        >
                          <Pencil className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      )}
                    </div>
                  </div>
                  {calibracion.motivo_correccion && (
                    <p className="mt-2 text-xs text-ink-soft">Motivo: {calibracion.motivo_correccion}</p>
                  )}
                  {calibracion.resultado === "no_conforme" && (
                    <div className="mt-2 flex items-start gap-1.5 rounded-md bg-[#FEF2F2] p-2 text-xs text-[#991B1B]">
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
                      Resultado no conforme — evalúa abrir un mantenimiento correctivo.
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
