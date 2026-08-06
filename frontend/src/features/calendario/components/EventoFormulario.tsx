import { useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Select } from "@/shared/components/ui/select";
import { Textarea } from "@/shared/components/ui/textarea";

import { ETIQUETAS_TIPO_EVENTO, TIPOS_EVENTO_MANUAL, type DatosEventoCalendario, type EventoCalendario, type TipoEventoManual } from "../types";

function aInputLocal(fechaIso: string): string {
  const fecha = new Date(fechaIso);
  const desfaseMin = fecha.getTimezoneOffset();
  return new Date(fecha.getTime() - desfaseMin * 60000).toISOString().slice(0, 16);
}

interface Props {
  editando?: EventoCalendario;
  fechaInicial?: string;
  guardando: boolean;
  onGuardar: (datos: DatosEventoCalendario) => Promise<void>;
  onCancelar: () => void;
}

export function EventoFormulario({ editando, fechaInicial, guardando, onGuardar, onCancelar }: Props) {
  const [tipo, setTipo] = useState<TipoEventoManual>((editando?.tipo as TipoEventoManual) ?? "institucional");
  const [titulo, setTitulo] = useState(editando?.titulo ?? "");
  const [fecha, setFecha] = useState(
    editando ? aInputLocal(editando.fecha) : fechaInicial ? aInputLocal(fechaInicial) : "",
  );
  const [descripcion, setDescripcion] = useState(editando?.descripcion ?? "");
  const [error, setError] = useState<string | null>(null);

  async function confirmar() {
    if (!titulo.trim()) {
      setError("El título es obligatorio.");
      return;
    }
    if (!fecha) {
      setError("La fecha es obligatoria.");
      return;
    }
    setError(null);
    try {
      await onGuardar({
        tipo,
        titulo: titulo.trim(),
        fecha: new Date(fecha).toISOString(),
        descripcion: descripcion || null,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el evento.");
    }
  }

  return (
    <div className="rounded-md border border-border bg-surface-alt p-4">
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Select label="Tipo" value={tipo} onChange={(e) => setTipo(e.target.value as TipoEventoManual)}>
          {TIPOS_EVENTO_MANUAL.map((valor) => (
            <option key={valor} value={valor}>
              {ETIQUETAS_TIPO_EVENTO[valor]}
            </option>
          ))}
        </Select>
        <Input label="Fecha y hora" type="datetime-local" value={fecha} onChange={(e) => setFecha(e.target.value)} />
      </div>
      <Input label="Título" value={titulo} onChange={(e) => setTitulo(e.target.value)} />
      <Textarea label="Descripción (opcional)" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <Button size="sm" cargando={guardando} onClick={confirmar}>
          {editando ? "Guardar cambios" : "Crear evento"}
        </Button>
        <Button variant="secondary" size="sm" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}
