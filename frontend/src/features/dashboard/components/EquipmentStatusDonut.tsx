import { PieChart as PieChartIcon } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";

import type { Kpis } from "../types";

import { arcosDelDonut, GROSOR, RADIO, type ClaveConteoEquipos } from "./EquipmentStatusDonut.logic";

const SEGMENTOS: { clave: ClaveConteoEquipos; etiqueta: string; color: string }[] = [
  { clave: "equipos_operativos", etiqueta: "Operativos", color: "#16A34A" },
  { clave: "equipos_en_mantenimiento", etiqueta: "En mantenimiento", color: "#F59E0B" },
  { clave: "equipos_fuera_de_servicio", etiqueta: "Fuera de servicio", color: "#DC2626" },
  { clave: "equipos_de_baja", etiqueta: "De baja", color: "#94A3B8" },
];

export function EquipmentStatusDonut({
  kpis,
  isLoading,
}: {
  kpis?: Kpis;
  isLoading: boolean;
}) {
  const [mostrarTabla, setMostrarTabla] = useState(false);
  const segmentosConDatos = kpis ? SEGMENTOS.filter((s) => kpis[s.clave] > 0) : [];
  const arcos = kpis ? arcosDelDonut(segmentosConDatos.map((s) => ({ ...s, valor: kpis[s.clave] }))) : [];

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PieChartIcon className="h-4 w-4 text-ink-soft" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-ink">Estado de equipos</h2>
        </div>
        <div className="flex items-center gap-2">
          {!isLoading && kpis && kpis.equipos_total > 0 && (
            <Button variant="ghost" size="sm" onClick={() => setMostrarTabla((v) => !v)}>
              {mostrarTabla ? "Ver gráfica" : "Ver tabla"}
            </Button>
          )}
          <Link to="/equipos" className="text-xs font-semibold text-primary-600 hover:text-primary-900">
            Ver equipos →
          </Link>
        </div>
      </div>

      {isLoading && <Skeleton className="h-48 w-full" />}

      {!isLoading && kpis && kpis.equipos_total === 0 && (
        <EmptyState
          icon={PieChartIcon}
          title="Todavía no hay equipos"
          description="Registra el primer equipo del laboratorio para ver su distribución aquí."
        />
      )}

      {!isLoading && kpis && kpis.equipos_total > 0 && (
        <>
          {mostrarTabla ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wide text-ink-soft">
                  <th scope="col" className="py-2">Estado</th>
                  <th scope="col" className="py-2">Equipos</th>
                </tr>
              </thead>
              <tbody>
                {SEGMENTOS.map((s) => (
                  <tr key={s.clave} className="border-b border-border last:border-0">
                    <td className="py-2 text-ink">
                      <span className="mr-2 inline-block h-2 w-2 rounded-sm" style={{ background: s.color }} />
                      {s.etiqueta}
                    </td>
                    <td className="py-2 tabular-nums text-ink">{kpis[s.clave]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="flex items-center gap-5">
              <svg
                width="160"
                height="160"
                viewBox="0 0 160 160"
                className="flex-shrink-0"
                role="img"
                aria-label={`Distribución de ${kpis.equipos_total} equipos por estado operativo`}
              >
                <circle cx="80" cy="80" r={RADIO} fill="none" stroke="var(--border)" strokeWidth={GROSOR} />
                {arcos.map((arco) => (
                  <circle
                    key={arco.clave}
                    cx="80"
                    cy="80"
                    r={RADIO}
                    fill="none"
                    stroke={arco.color}
                    strokeWidth={GROSOR}
                    strokeDasharray={arco.dasharray}
                    strokeDashoffset={arco.dashoffset}
                    transform="rotate(-90 80 80)"
                  />
                ))}
                <text x="80" y="76" textAnchor="middle" fontSize="26" fontWeight="750" fill="var(--text-primary)">
                  {kpis.equipos_total}
                </text>
                <text x="80" y="94" textAnchor="middle" fontSize="10.5" fontWeight="600" fill="var(--text-secondary)">
                  equipos
                </text>
              </svg>
              <ul className="flex-1 space-y-2 text-sm">
                {SEGMENTOS.map((s) => (
                  <li key={s.clave} className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-ink-soft">
                      <span className="h-2 w-2 rounded-sm" style={{ background: s.color }} />
                      {s.etiqueta}
                    </span>
                    <span className="font-semibold tabular-nums text-ink">{kpis[s.clave]}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
