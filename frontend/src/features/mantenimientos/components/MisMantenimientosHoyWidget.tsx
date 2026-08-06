import { CalendarClock } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Skeleton } from "@/shared/components/ui/skeleton";

import { useMisMantenimientosDeHoy } from "../hooks/useMantenimientos";
import { ETIQUETAS_TIPO } from "../types";
import { EstadoMantenimientoBadge } from "./EstadoMantenimientoBadge";

/** HU-TEC-01 — "como técnico quiero ver mis mantenimientos de hoy al
 * entrar al sistema". */
export function MisMantenimientosHoyWidget() {
  const navigate = useNavigate();
  const { data: mantenimientos, isLoading } = useMisMantenimientosDeHoy();

  if (isLoading) {
    return <Skeleton className="mt-6 h-32 w-full" />;
  }

  if (!mantenimientos || mantenimientos.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex items-center gap-2">
        <CalendarClock className="h-4 w-4 text-primary-900" aria-hidden="true" />
        <h2 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
          Mis mantenimientos de hoy
        </h2>
      </div>
      <ul className="space-y-2">
        {mantenimientos.map((mantenimiento) => (
          <li key={mantenimiento.id}>
            <button
              type="button"
              onClick={() => navigate(`/equipos/${mantenimiento.equipo_id}`)}
              className="flex w-full items-center justify-between gap-3 rounded-md border border-border px-3 py-2 text-left hover:bg-surface-alt"
            >
              <span className="truncate text-sm font-medium text-ink">
                {ETIQUETAS_TIPO[mantenimiento.tipo]}
                {mantenimiento.descripcion && ` · ${mantenimiento.descripcion}`}
              </span>
              <EstadoMantenimientoBadge estado={mantenimiento.estado} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
