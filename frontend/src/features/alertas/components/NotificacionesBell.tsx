import { AlertTriangle, Bell } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "@/shared/components/ui/empty-state";

import { useAlertas, useContarActivas, useMarcarLeida, useResolverManual } from "../hooks/useAlertas";
import { AlertaItem } from "./AlertaItem";

/** Reemplaza el botón de campana estático de `Navbar.tsx` (stub visual de
 * Sprints 5-7) — RF-ALT-04/05. Muestra el conteo de alertas activas como
 * badge y una lista corta con acciones rápidas; el listado completo con
 * filtros vive en `/alertas` (`AlertasPage`). */
export function NotificacionesBell() {
  const navigate = useNavigate();
  const [abierto, setAbierto] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const botonRef = useRef<HTMLButtonElement>(null);

  const { data: contador } = useContarActivas();
  // RNF-PERF-03 — se pide una página chica directamente al servidor (antes
  // traía TODAS las activas y recortaba a 8 del lado del cliente).
  const { data, isLoading, isError } = useAlertas("activa", 1, 8);
  const marcarLeida = useMarcarLeida();
  const resolver = useResolverManual();

  useEffect(() => {
    if (!abierto) return;
    function alHacerClicFuera(evt: MouseEvent) {
      if (!panelRef.current?.contains(evt.target as Node)) setAbierto(false);
    }
    function alPresionarTecla(evt: KeyboardEvent) {
      if (evt.key === "Escape") {
        setAbierto(false);
        botonRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", alHacerClicFuera);
    document.addEventListener("keydown", alPresionarTecla);
    return () => {
      document.removeEventListener("mousedown", alHacerClicFuera);
      document.removeEventListener("keydown", alPresionarTecla);
    };
  }, [abierto]);

  const activasVisibles = data?.items ?? [];
  const conteo = contador?.activas ?? 0;

  return (
    <div className="relative" ref={panelRef}>
      <button
        ref={botonRef}
        type="button"
        aria-label={conteo > 0 ? `Notificaciones, ${conteo} activas` : "Notificaciones"}
        aria-haspopup="menu"
        aria-expanded={abierto}
        onClick={() => setAbierto((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-md text-ink-soft transition-colors duration-fast hover:bg-surface-alt hover:text-ink focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-900"
      >
        <Bell className="h-[18px] w-[18px]" aria-hidden="true" />
        {conteo > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-none text-white">
            {conteo > 99 ? "99+" : conteo}
          </span>
        )}
      </button>

      {abierto && (
        <div
          role="menu"
          aria-label="Notificaciones"
          className="absolute right-0 top-11 z-20 max-h-[28rem] w-96 overflow-y-auto rounded-md border border-border bg-surface p-2 shadow-ambient"
        >
          <div className="flex items-center justify-between px-1.5 py-1">
            <p className="text-sm font-semibold text-ink">Alertas activas</p>
            <button
              type="button"
              onClick={() => {
                setAbierto(false);
                navigate("/alertas");
              }}
              className="text-xs font-medium text-primary-900 hover:underline"
            >
              Ver todas
            </button>
          </div>

          {isLoading && <p className="px-1.5 py-4 text-sm text-ink-soft">Cargando…</p>}

          {isError && (
            <EmptyState
              icon={AlertTriangle}
              title="No se pudo cargar"
              description="Intenta de nuevo en unos segundos."
            />
          )}

          {!isLoading && !isError && activasVisibles.length === 0 && (
            <EmptyState icon={Bell} title="Sin alertas activas" description="Todo al día." />
          )}

          {!isLoading && !isError && activasVisibles.length > 0 && (
            <div className="mt-1 space-y-1.5">
              {activasVisibles.map((alerta) => (
                <AlertaItem
                  key={alerta.id}
                  alerta={alerta}
                  onMarcarLeida={(id) => marcarLeida.mutate(id)}
                  onResolver={(id) => resolver.mutate(id)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
