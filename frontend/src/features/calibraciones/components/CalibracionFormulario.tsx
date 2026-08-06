import { useRef, useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Select } from "@/shared/components/ui/select";
import { Textarea } from "@/shared/components/ui/textarea";

import * as api from "../api/calibracionesApi";
import {
  ETIQUETAS_RESULTADO,
  EXTENSIONES_CERTIFICADO,
  RESULTADOS_CALIBRACION,
  TAMANO_MAXIMO_CERTIFICADO_BYTES,
  type ArchivoCertificado,
  type Calibracion,
  type DatosCalibracion,
  type ResultadoCalibracion,
} from "../types";

interface Props {
  equipoId: string;
  /** Si se da, el formulario opera en modo "corregir" sobre esta calibración. */
  corrigiendo?: Calibracion;
  guardando: boolean;
  onGuardar: (datos: DatosCalibracion & { motivo?: string }) => Promise<void>;
  onCancelar: () => void;
}

export function CalibracionFormulario({ equipoId, corrigiendo, guardando, onGuardar, onCancelar }: Props) {
  const [fechaCalibracion, setFechaCalibracion] = useState(corrigiendo?.fecha_calibracion ?? "");
  const [frecuenciaMeses, setFrecuenciaMeses] = useState(String(corrigiendo?.frecuencia_meses ?? "12"));
  const [laboratorioProveedor, setLaboratorioProveedor] = useState(corrigiendo?.laboratorio_proveedor ?? "");
  const [numeroCertificado, setNumeroCertificado] = useState(corrigiendo?.numero_certificado ?? "");
  const [resultado, setResultado] = useState<ResultadoCalibracion>(corrigiendo?.resultado ?? "conforme");
  const [incertidumbre, setIncertidumbre] = useState(corrigiendo?.incertidumbre ?? "");
  const [observaciones, setObservaciones] = useState(corrigiendo?.observaciones ?? "");
  const [motivo, setMotivo] = useState("");
  const [archivo, setArchivo] = useState<File | null>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputArchivoRef = useRef<HTMLInputElement>(null);

  function onSeleccionarArchivo(seleccionado: File | undefined) {
    if (!seleccionado) return;
    if (!seleccionado.name.toLowerCase().endsWith(".pdf") || seleccionado.type !== "application/pdf") {
      setError("El certificado debe ser un archivo PDF.");
      return;
    }
    if (seleccionado.size > TAMANO_MAXIMO_CERTIFICADO_BYTES) {
      setError("El certificado supera 20 MB.");
      return;
    }
    setError(null);
    setArchivo(seleccionado);
  }

  async function confirmar() {
    if (!fechaCalibracion) {
      setError("La fecha de calibración es obligatoria.");
      return;
    }
    if (corrigiendo && !motivo.trim()) {
      setError("El motivo de la corrección es obligatorio.");
      return;
    }
    setError(null);
    try {
      let certificado: ArchivoCertificado | null = null;
      if (archivo) {
        setSubiendo(true);
        const { url_subida, object_key } = await api.solicitarUrlCertificado(
          archivo.name,
          archivo.type,
          archivo.size,
        );
        await api.subirArchivoConProgreso(url_subida, archivo, () => {});
        certificado = {
          object_key,
          nombre_archivo: archivo.name,
          tamano_bytes: archivo.size,
          tipo_mime: archivo.type,
        };
        setSubiendo(false);
      }

      await onGuardar({
        equipo_id: equipoId,
        fecha_calibracion: fechaCalibracion,
        frecuencia_meses: Number(frecuenciaMeses),
        laboratorio_proveedor: laboratorioProveedor || null,
        numero_certificado: numeroCertificado || null,
        resultado,
        incertidumbre: incertidumbre || null,
        observaciones: observaciones || null,
        certificado,
        ...(corrigiendo ? { motivo: motivo.trim() } : {}),
      });
    } catch (err) {
      setSubiendo(false);
      setError(err instanceof ApiError ? err.message : "No se pudo guardar la calibración.");
    }
  }

  return (
    <div className="rounded-md border border-border bg-surface-alt p-4">
      {corrigiendo && (
        <Textarea
          label="Motivo de la corrección"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          placeholder="Por qué se corrige este registro (obligatorio, RN-CAL-02)…"
        />
      )}
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Input
          label="Fecha de calibración"
          type="date"
          value={fechaCalibracion}
          onChange={(e) => setFechaCalibracion(e.target.value)}
        />
        <Input
          label="Frecuencia (meses)"
          type="number"
          min={1}
          value={frecuenciaMeses}
          onChange={(e) => setFrecuenciaMeses(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Input
          label="Laboratorio proveedor"
          value={laboratorioProveedor}
          onChange={(e) => setLaboratorioProveedor(e.target.value)}
        />
        <Input
          label="N° de certificado"
          value={numeroCertificado}
          onChange={(e) => setNumeroCertificado(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Select label="Resultado" value={resultado} onChange={(e) => setResultado(e.target.value as ResultadoCalibracion)}>
          {RESULTADOS_CALIBRACION.map((valor) => (
            <option key={valor} value={valor}>
              {ETIQUETAS_RESULTADO[valor]}
            </option>
          ))}
        </Select>
        <Input
          label="Incertidumbre de medición"
          type="number"
          step="any"
          value={incertidumbre ?? ""}
          onChange={(e) => setIncertidumbre(e.target.value)}
        />
      </div>
      <Textarea label="Observaciones" value={observaciones ?? ""} onChange={(e) => setObservaciones(e.target.value)} />

      <div className="mb-4">
        <label className="mb-1.5 block text-sm font-semibold text-ink-soft">Certificado (PDF, opcional)</label>
        <div className="flex items-center gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={() => inputArchivoRef.current?.click()}>
            {archivo ? archivo.name : "Elegir archivo"}
          </Button>
          <input
            ref={inputArchivoRef}
            type="file"
            accept={EXTENSIONES_CERTIFICADO}
            className="hidden"
            onChange={(e) => onSeleccionarArchivo(e.target.files?.[0])}
          />
        </div>
      </div>

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <Button size="sm" cargando={guardando || subiendo} onClick={confirmar}>
          {corrigiendo ? "Guardar corrección" : "Registrar calibración"}
        </Button>
        <Button variant="secondary" size="sm" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}
