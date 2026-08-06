import { useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Textarea } from "@/shared/components/ui/textarea";

import type { DatosCierre } from "../types";

interface Props {
  guardando: boolean;
  onGuardar: (datos: DatosCierre) => Promise<void>;
  onCancelar: () => void;
}

export function CerrarMantenimientoFormulario({ guardando, onGuardar, onCancelar }: Props) {
  const [fechaEjecutada, setFechaEjecutada] = useState("");
  const [repuestos, setRepuestos] = useState("");
  const [tiempoInactividad, setTiempoInactividad] = useState("");
  const [costo, setCosto] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function confirmar() {
    if (!fechaEjecutada) {
      setError("La fecha de ejecución es obligatoria (RN-MANT-02).");
      return;
    }
    setError(null);
    try {
      await onGuardar({
        fecha_ejecutada: fechaEjecutada,
        repuestos_utilizados: repuestos || null,
        tiempo_inactividad_horas: tiempoInactividad || null,
        costo: costo || null,
        descripcion: descripcion || null,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cerrar el mantenimiento.");
    }
  }

  return (
    <div className="mt-2 rounded-md border border-border bg-surface-alt p-4">
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Input
          label="Fecha de ejecución"
          type="date"
          value={fechaEjecutada}
          onChange={(e) => setFechaEjecutada(e.target.value)}
        />
        <Input
          label="Tiempo de inactividad (horas)"
          type="number"
          step="any"
          min={0}
          value={tiempoInactividad}
          onChange={(e) => setTiempoInactividad(e.target.value)}
        />
      </div>
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Input label="Costo" type="number" step="any" min={0} value={costo} onChange={(e) => setCosto(e.target.value)} />
        <Input label="Repuestos utilizados" value={repuestos} onChange={(e) => setRepuestos(e.target.value)} />
      </div>
      <Textarea label="Notas de cierre" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <Button size="sm" cargando={guardando} onClick={confirmar}>
          Cerrar mantenimiento
        </Button>
        <Button variant="secondary" size="sm" onClick={onCancelar}>
          Volver
        </Button>
      </div>
    </div>
  );
}
