import { FileText, Paperclip, Play, Plus, X } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";

import * as api from "../api/mantenimientosApi";
import {
  useAgregarEvidencia,
  useAsignarInforme,
  useCancelarMantenimiento,
  useCerrarMantenimiento,
  useCrearMantenimiento,
  useIniciarMantenimiento,
  useMantenimientosPorEquipo,
} from "../hooks/useMantenimientos";
import {
  ETIQUETAS_TIPO,
  TAMANO_MAXIMO_EVIDENCIA_BYTES,
  TAMANO_MAXIMO_INFORME_BYTES,
  type DatosCierre,
  type DatosMantenimiento,
  type Mantenimiento,
} from "../types";
import { CerrarMantenimientoFormulario } from "./CerrarMantenimientoFormulario";
import { EstadoMantenimientoBadge } from "./EstadoMantenimientoBadge";
import { MantenimientoFormulario } from "./MantenimientoFormulario";

export function MantenimientosSection({ equipoId }: { equipoId: string }) {
  const { data: mantenimientos, isLoading } = useMantenimientosPorEquipo(equipoId);
  const crear = useCrearMantenimiento(equipoId);
  const iniciar = useIniciarMantenimiento(equipoId);
  const cerrar = useCerrarMantenimiento(equipoId);
  const cancelar = useCancelarMantenimiento(equipoId);
  const asignarInforme = useAsignarInforme(equipoId);

  const [mostrandoFormulario, setMostrandoFormulario] = useState(false);
  const [cerrandoId, setCerrandoId] = useState<string | null>(null);
  const [cancelandoId, setCancelandoId] = useState<string | null>(null);
  const [motivoCancelacion, setMotivoCancelacion] = useState("");

  async function crearMantenimiento(datos: DatosMantenimiento) {
    await crear.mutateAsync(datos);
    setMostrandoFormulario(false);
  }

  async function cerrarMantenimiento(id: string, datos: DatosCierre) {
    await cerrar.mutateAsync({ id, datos });
    setCerrandoId(null);
  }

  async function confirmarCancelacion(id: string) {
    if (!motivoCancelacion.trim()) return;
    await cancelar.mutateAsync({ id, motivo: motivoCancelacion.trim() });
    setCancelandoId(null);
    setMotivoCancelacion("");
  }

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">Mantenimientos</h2>
        {!mostrandoFormulario && (
          <Button size="sm" onClick={() => setMostrandoFormulario(true)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Registrar mantenimiento
          </Button>
        )}
      </div>

      {mostrandoFormulario && (
        <div className="mb-4">
          <MantenimientoFormulario
            equipoId={equipoId}
            guardando={crear.isPending}
            onGuardar={crearMantenimiento}
            onCancelar={() => setMostrandoFormulario(false)}
          />
        </div>
      )}

      {isLoading && <Skeleton className="h-32 w-full" />}

      {!isLoading && mantenimientos?.length === 0 && (
        <p className="text-sm text-ink-soft">Aún no hay mantenimientos registrados para este equipo.</p>
      )}

      {!!mantenimientos?.length && (
        <ul className="space-y-2">
          {mantenimientos.map((mantenimiento) => (
            <FilaMantenimiento
              key={mantenimiento.id}
              mantenimiento={mantenimiento}
              cerrando={cerrandoId === mantenimiento.id}
              cancelando={cancelandoId === mantenimiento.id}
              motivoCancelacion={motivoCancelacion}
              onIniciar={() => iniciar.mutateAsync(mantenimiento.id)}
              iniciando={iniciar.isPending}
              onAbrirCerrar={() => setCerrandoId(mantenimiento.id)}
              onCerrarGuardar={(datos) => cerrarMantenimiento(mantenimiento.id, datos)}
              onCerrarCancelar={() => setCerrandoId(null)}
              cerrandoPending={cerrar.isPending}
              onAbrirCancelar={() => setCancelandoId(mantenimiento.id)}
              onCambiarMotivoCancelacion={setMotivoCancelacion}
              onConfirmarCancelacion={() => confirmarCancelacion(mantenimiento.id)}
              onCerrarCancelacion={() => {
                setCancelandoId(null);
                setMotivoCancelacion("");
              }}
              cancelandoPending={cancelar.isPending}
              onAsignarInforme={(archivo) => asignarInforme.mutateAsync({ id: mantenimiento.id, archivo })}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

interface FilaProps {
  mantenimiento: Mantenimiento;
  cerrando: boolean;
  cancelando: boolean;
  motivoCancelacion: string;
  onIniciar: () => Promise<Mantenimiento>;
  iniciando: boolean;
  onAbrirCerrar: () => void;
  onCerrarGuardar: (datos: DatosCierre) => Promise<void>;
  onCerrarCancelar: () => void;
  cerrandoPending: boolean;
  onAbrirCancelar: () => void;
  onCambiarMotivoCancelacion: (motivo: string) => void;
  onConfirmarCancelacion: () => Promise<void>;
  onCerrarCancelacion: () => void;
  cancelandoPending: boolean;
  onAsignarInforme: (archivo: { object_key: string; nombre_archivo: string; tamano_bytes: number; tipo_mime: string }) => Promise<Mantenimiento>;
}

function FilaMantenimiento({
  mantenimiento,
  cerrando,
  cancelando,
  motivoCancelacion,
  onIniciar,
  iniciando,
  onAbrirCerrar,
  onCerrarGuardar,
  onCerrarCancelar,
  cerrandoPending,
  onAbrirCancelar,
  onCambiarMotivoCancelacion,
  onConfirmarCancelacion,
  onCerrarCancelacion,
  cancelandoPending,
  onAsignarInforme,
}: FilaProps) {
  const agregarEvidencia = useAgregarEvidencia(mantenimiento.id);
  const inputEvidenciaRef = useRef<HTMLInputElement>(null);
  const inputInformeRef = useRef<HTMLInputElement>(null);
  const [subiendoEvidencia, setSubiendoEvidencia] = useState(false);
  const [subiendoInforme, setSubiendoInforme] = useState(false);
  const [errorArchivo, setErrorArchivo] = useState<string | null>(null);

  const abierto = mantenimiento.estado === "programado" || mantenimiento.estado === "en_ejecucion";

  async function onSeleccionarEvidencia(archivo: File | undefined) {
    if (!archivo) return;
    if (archivo.size > TAMANO_MAXIMO_EVIDENCIA_BYTES) {
      setErrorArchivo("La evidencia supera 10 MB.");
      return;
    }
    setErrorArchivo(null);
    setSubiendoEvidencia(true);
    try {
      const { url_subida, object_key } = await api.solicitarUrlEvidencia(
        archivo.name,
        archivo.type,
        archivo.size,
      );
      await api.subirArchivoConProgreso(url_subida, archivo, () => {});
      await agregarEvidencia.mutateAsync({
        object_key,
        nombre_archivo: archivo.name,
        tamano_bytes: archivo.size,
        tipo_mime: archivo.type,
      });
    } catch {
      setErrorArchivo("No se pudo subir la evidencia.");
    } finally {
      setSubiendoEvidencia(false);
      if (inputEvidenciaRef.current) inputEvidenciaRef.current.value = "";
    }
  }

  async function onSeleccionarInforme(archivo: File | undefined) {
    if (!archivo) return;
    if (archivo.type !== "application/pdf") {
      setErrorArchivo("El informe debe ser un archivo PDF.");
      return;
    }
    if (archivo.size > TAMANO_MAXIMO_INFORME_BYTES) {
      setErrorArchivo("El informe supera 20 MB.");
      return;
    }
    setErrorArchivo(null);
    setSubiendoInforme(true);
    try {
      const { url_subida, object_key } = await api.solicitarUrlInforme(
        archivo.name,
        archivo.type,
        archivo.size,
      );
      await api.subirArchivoConProgreso(url_subida, archivo, () => {});
      await onAsignarInforme({
        object_key,
        nombre_archivo: archivo.name,
        tamano_bytes: archivo.size,
        tipo_mime: archivo.type,
      });
    } catch {
      setErrorArchivo("No se pudo subir el informe.");
    } finally {
      setSubiendoInforme(false);
      if (inputInformeRef.current) inputInformeRef.current.value = "";
    }
  }

  async function descargarInforme() {
    const { url } = await api.obtenerUrlInforme(mantenimiento.id);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <li className="rounded-md border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-ink">
            {ETIQUETAS_TIPO[mantenimiento.tipo]}
            {mantenimiento.fecha_programada && ` · programado: ${mantenimiento.fecha_programada}`}
          </p>
          <p className="text-xs text-ink-soft">
            {mantenimiento.fecha_ejecutada && `Ejecutado: ${mantenimiento.fecha_ejecutada}`}
            {mantenimiento.descripcion && ` · ${mantenimiento.descripcion}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <EstadoMantenimientoBadge estado={mantenimiento.estado} />
          {mantenimiento.estado === "programado" && (
            <Button size="sm" variant="secondary" cargando={iniciando} onClick={onIniciar}>
              <Play className="h-4 w-4" aria-hidden="true" />
              Iniciar
            </Button>
          )}
          {(mantenimiento.estado === "programado" || mantenimiento.estado === "en_ejecucion") &&
            !cerrando && (
              <Button size="sm" variant="secondary" onClick={onAbrirCerrar}>
                Cerrar
              </Button>
            )}
          {abierto && !cancelando && (
            <Button size="sm" variant="ghost" aria-label="Cancelar mantenimiento" onClick={onAbrirCancelar}>
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
          <Button
            size="sm"
            variant="secondary"
            title="Agregar evidencia fotográfica"
            cargando={subiendoEvidencia}
            onClick={() => inputEvidenciaRef.current?.click()}
          >
            <Paperclip className="h-4 w-4" aria-hidden="true" />
          </Button>
          <input
            ref={inputEvidenciaRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => onSeleccionarEvidencia(e.target.files?.[0])}
          />
          {mantenimiento.tiene_informe ? (
            <Button size="sm" variant="secondary" title="Descargar informe" onClick={descargarInforme}>
              <FileText className="h-4 w-4" aria-hidden="true" />
            </Button>
          ) : (
            <Button
              size="sm"
              variant="secondary"
              title="Adjuntar informe PDF"
              cargando={subiendoInforme}
              onClick={() => inputInformeRef.current?.click()}
            >
              <FileText className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
          <input
            ref={inputInformeRef}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => onSeleccionarInforme(e.target.files?.[0])}
          />
        </div>
      </div>

      {errorArchivo && (
        <p role="alert" aria-live="polite" className="mt-2 text-xs font-medium text-danger">
          {errorArchivo}
        </p>
      )}

      {cerrando && (
        <CerrarMantenimientoFormulario
          guardando={cerrandoPending}
          onGuardar={onCerrarGuardar}
          onCancelar={onCerrarCancelar}
        />
      )}

      {cancelando && (
        <div className="mt-2 rounded-md border border-danger/30 bg-[#FEF2F2] p-3">
          <label htmlFor={`motivo-${mantenimiento.id}`} className="mb-1.5 block text-sm font-semibold text-[#991B1B]">
            Motivo de la cancelación
          </label>
          <textarea
            id={`motivo-${mantenimiento.id}`}
            className="mb-2 w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm text-ink outline-none transition-colors duration-fast focus:border-primary-900 focus:ring-4 focus:ring-primary-900/15"
            value={motivoCancelacion}
            onChange={(e) => onCambiarMotivoCancelacion(e.target.value)}
            rows={2}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="destructive"
              cargando={cancelandoPending}
              disabled={!motivoCancelacion.trim()}
              onClick={onConfirmarCancelacion}
            >
              Confirmar cancelación
            </Button>
            <Button size="sm" variant="secondary" onClick={onCerrarCancelacion}>
              Volver
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}
