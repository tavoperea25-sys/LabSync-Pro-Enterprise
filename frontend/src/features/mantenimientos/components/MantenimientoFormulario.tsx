import { useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Select } from "@/shared/components/ui/select";
import { Textarea } from "@/shared/components/ui/textarea";

import { ETIQUETAS_TIPO, TIPOS_MANTENIMIENTO, type DatosMantenimiento, type TipoMantenimiento } from "../types";

interface Props {
  equipoId: string;
  guardando: boolean;
  onGuardar: (datos: DatosMantenimiento) => Promise<void>;
  onCancelar: () => void;
}

export function MantenimientoFormulario({ equipoId, guardando, onGuardar, onCancelar }: Props) {
  const [tipo, setTipo] = useState<TipoMantenimiento>("preventivo");
  const [fechaProgramada, setFechaProgramada] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [frecuenciaMeses, setFrecuenciaMeses] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function confirmar() {
    setError(null);
    try {
      await onGuardar({
        equipo_id: equipoId,
        tipo,
        fecha_programada: fechaProgramada || null,
        descripcion: descripcion || null,
        frecuencia_meses:
          tipo === "preventivo" && frecuenciaMeses ? Number(frecuenciaMeses) : null,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo registrar el mantenimiento.");
    }
  }

  return (
    <div className="rounded-md border border-border bg-surface-alt p-4">
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Select label="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoMantenimiento)}>
          {TIPOS_MANTENIMIENTO.map((valor) => (
            <option key={valor} value={valor}>
              {ETIQUETAS_TIPO[valor]}
            </option>
          ))}
        </Select>
        <Input
          label="Fecha programada"
          type="date"
          value={fechaProgramada}
          onChange={(e) => setFechaProgramada(e.target.value)}
        />
      </div>

      {tipo === "preventivo" && (
        <Input
          label="Frecuencia de recurrencia (meses, opcional)"
          type="number"
          min={1}
          value={frecuenciaMeses}
          onChange={(e) => setFrecuenciaMeses(e.target.value)}
        />
      )}

      <Textarea label="Descripción" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <Button size="sm" cargando={guardando} onClick={confirmar}>
          Registrar mantenimiento
        </Button>
        <Button variant="secondary" size="sm" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}
