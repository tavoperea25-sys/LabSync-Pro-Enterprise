import { Calendar } from "lucide-react";
import { Link } from "react-router-dom";

import { useEventos } from "@/features/calendario/hooks/useCalendario";
import { Badge } from "@/shared/components/ui/badge";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";

const DIAS_HORIZONTE = 30;

function inicioDeHoy(): Date {
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  return hoy;
}

function formatearDia(iso: string): { dia: string; mes: string } {
  const fecha = new Date(iso);
  return {
    dia: String(fecha.getDate()),
    mes: fecha.toLocaleDateString("es-CO", { month: "short" }).replace(".", ""),
  };
}

export function CalibrationAgenda() {
  const desde = inicioDeHoy();
  const hasta = new Date(desde);
  hasta.setDate(hasta.getDate() + DIAS_HORIZONTE);
  hasta.setHours(23, 59, 59, 999);

  const { data: eventos, isLoading } = useEventos({
    desde: desde.toISOString(),
    hasta: hasta.toISOString(),
    tipo: "calibracion",
  });

  const proximos = (eventos ?? [])
    .slice()
    .sort((a, b) => a.fecha.localeCompare(b.fecha))
    .slice(0, 5);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-ink-soft" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-ink">Calendario de calibraciones</h2>
        </div>
        <Link to="/calendario" className="text-xs font-semibold text-primary-600 hover:text-primary-900">
          Ver calendario →
        </Link>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {!isLoading && proximos.length === 0 && (
        <EmptyState
          icon={Calendar}
          title="Sin calibraciones próximas"
          description={`Ningún equipo tiene una calibración programada en los próximos ${DIAS_HORIZONTE} días.`}
        />
      )}

      {!isLoading && proximos.length > 0 && (
        <ul className="space-y-1">
          {proximos.map((evento) => {
            const { dia, mes } = formatearDia(evento.fecha);
            const vencida = new Date(evento.fecha) < desde;
            return (
              <li key={evento.id}>
                <Link
                  to={evento.origen_id ? `/equipos/${evento.origen_id}` : "/calendario"}
                  className="flex items-center gap-3 rounded-md px-2 py-2 transition-colors duration-fast hover:bg-surface-alt"
                >
                  <div className="w-9 flex-shrink-0 text-center">
                    <p className="font-display text-base font-bold leading-none tabular-nums text-ink">{dia}</p>
                    <p className="text-[10px] font-semibold uppercase text-ink-soft">{mes}</p>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">{evento.titulo}</p>
                    {evento.descripcion && (
                      <p className="truncate text-xs text-ink-soft">{evento.descripcion}</p>
                    )}
                  </div>
                  <Badge variant={vencida ? "danger" : "neutral"}>{vencida ? "Vencida" : "Programada"}</Badge>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
