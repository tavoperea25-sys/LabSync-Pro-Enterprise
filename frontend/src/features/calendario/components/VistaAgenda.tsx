import { CalendarX } from "lucide-react";

import { EmptyState } from "@/shared/components/ui/empty-state";

import type { EventoCalendario } from "../types";
import { EventoChip } from "./EventoChip";

function formatearFechaLarga(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function agruparPorDia(eventos: EventoCalendario[]): [string, EventoCalendario[]][] {
  const grupos = new Map<string, EventoCalendario[]>();
  for (const evento of eventos) {
    const clave = evento.fecha.slice(0, 10);
    grupos.set(clave, [...(grupos.get(clave) ?? []), evento]);
  }
  return Array.from(grupos.entries()).sort(([a], [b]) => a.localeCompare(b));
}

export function VistaAgenda({
  eventos,
  onEditar,
}: {
  eventos: EventoCalendario[];
  onEditar: (evento: EventoCalendario) => void;
}) {
  if (eventos.length === 0) {
    return (
      <EmptyState icon={CalendarX} title="Sin eventos" description="No hay eventos en este rango de fechas." />
    );
  }

  const grupos = agruparPorDia(eventos);

  return (
    <div className="space-y-4">
      {grupos.map(([dia, eventosDelDia]) => (
        <div key={dia}>
          <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-soft">
            {formatearFechaLarga(dia)}
          </h3>
          <ul className="space-y-1 rounded-lg border border-border p-2">
            {eventosDelDia.map((evento) => (
              <li key={evento.id}>
                <EventoChip evento={evento} onEditar={onEditar} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
