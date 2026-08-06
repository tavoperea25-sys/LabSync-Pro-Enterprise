import { AlertCircle, Lightbulb, Sparkles, TrendingUp } from "lucide-react";

import type { EquipoCritico, Kpis } from "../types";

/** RF futuro (roadmap Fase 6+, `docs/17-roadmap.md`) — no hay backend de IA
 * todavía. Solo el primer insight es un dato real (conteo de equipos que ya
 * calcula `DashboardService`); los otros dos son contenido ilustrativo,
 * marcados explícitamente como "Vista previa" para no aparentar más
 * inteligencia de la que existe (mismo criterio de honestidad de datos que
 * ya se aplicó al Dashboard original — ver docs/00-analisis-critico-y-recomendaciones.md). */
export function AiAssistantCard({ kpis, equiposCriticos }: { kpis?: Kpis; equiposCriticos?: EquipoCritico[] }) {
  const totalAtencion = equiposCriticos?.length ?? 0;
  const primerEquipoCritico = equiposCriticos?.[0];

  return (
    <div className="relative overflow-hidden rounded-lg border border-border bg-surface p-5">
      <div
        className="absolute inset-x-0 top-0 h-[3px]"
        style={{ background: "linear-gradient(90deg, #6D5BD0, #34B3A0, #198754)" }}
      />
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-sm"
            style={{ background: "linear-gradient(135deg, #6D5BD0, #34B3A0)" }}
          >
            <Sparkles className="h-4 w-4 text-white" aria-hidden="true" />
          </div>
          <h2 className="text-sm font-bold text-ink">
            LabSync AI Assistant{" "}
            <span className="ml-1.5 rounded-full bg-[#6D5BD0]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#6D5BD0]">
              Vista previa
            </span>
          </h2>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="rounded-md border border-border-soft bg-surface-alt p-3.5">
          <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-soft">
            <AlertCircle className="h-3 w-3" aria-hidden="true" /> Requiere atención
          </p>
          <p className="text-xs leading-relaxed text-ink">
            {totalAtencion > 0
              ? `${totalAtencion} equipo${totalAtencion === 1 ? "" : "s"} necesita${totalAtencion === 1 ? "" : "n"} revisión: calibración vencida o estado operativo distinto de "operativo".`
              : "Ningún equipo requiere atención en este momento."}
          </p>
        </div>

        <div className="rounded-md border border-border-soft bg-surface-alt p-3.5">
          <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-ink-soft">
            <TrendingUp className="h-3 w-3" aria-hidden="true" /> Tendencia (vista previa)
          </p>
          <p className="text-xs leading-relaxed text-ink">
            Cuando haya suficiente historial, aquí se mostrarán patrones detectados automáticamente — por
            ejemplo, un aumento de desviaciones repetidas en un área o categoría de equipo.
          </p>
        </div>

        <div className="rounded-md border border-[#6D5BD0]/25 bg-[#6D5BD0]/[0.05] p-3.5">
          <p className="mb-1.5 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-[#6D5BD0]">
            <Lightbulb className="h-3 w-3" aria-hidden="true" /> Recomendación (vista previa)
          </p>
          <p className="text-xs leading-relaxed text-ink">
            {primerEquipoCritico
              ? `Prioriza "${primerEquipoCritico.equipo_nombre}" — es el equipo con mayor urgencia en la tabla de abajo.`
              : kpis
                ? "No hay ninguna acción urgente que recomendar en este momento."
                : "Cargando recomendaciones…"}
          </p>
        </div>
      </div>
    </div>
  );
}
