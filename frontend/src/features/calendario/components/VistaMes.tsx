import { useMemo } from "react";

import type { EventoCalendario } from "../types";
import { EventoChip } from "./EventoChip";
import { agruparEventosPorDia, celdasDelMes, claveDia, mismodia } from "./VistaMes.logic";

const DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const MAX_EVENTOS_VISIBLES = 3;

export function VistaMes({
  fechaDeReferencia,
  eventos,
  onEditar,
  onCrearEnFecha,
}: {
  fechaDeReferencia: Date;
  eventos: EventoCalendario[];
  onEditar: (evento: EventoCalendario) => void;
  onCrearEnFecha: (fecha: Date) => void;
}) {
  const celdas = celdasDelMes(fechaDeReferencia);
  const hoy = new Date();
  // El agrupamiento se recalcula solo cuando cambia la referencia de
  // `eventos` (React Query conserva la misma referencia entre renders si los
  // datos no cambiaron) — evita repetir el recorrido completo del arreglo en
  // cada una de las 42 celdas ante un re-render no relacionado (p. ej. al
  // abrir el formulario de un evento).
  const eventosPorDia = useMemo(() => agruparEventosPorDia(eventos), [eventos]);

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="grid grid-cols-7 border-b border-border bg-surface-alt">
        {DIAS_SEMANA.map((dia) => (
          <div key={dia} className="px-2 py-1.5 text-center text-xs font-semibold text-ink-soft">
            {dia}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7">
        {celdas.map((dia, indice) => {
          const delMesActual = dia.getMonth() === fechaDeReferencia.getMonth();
          const esHoy = mismodia(dia, hoy.toISOString());
          const eventosDelDia = eventosPorDia.get(claveDia(dia)) ?? [];
          const visibles = eventosDelDia.slice(0, MAX_EVENTOS_VISIBLES);
          const restantes = eventosDelDia.length - visibles.length;

          return (
            // Un <div role="button"> (no <button>) a propósito: cada chip de
            // evento adentro ya es su propio <button> — anidar <button> en
            // <button> es HTML inválido y rompe el manejo de clics del hijo.
            <div
              key={indice}
              role="button"
              tabIndex={0}
              onClick={() => onCrearEnFecha(dia)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onCrearEnFecha(dia);
                }
              }}
              className={`flex min-h-24 cursor-pointer flex-col items-stretch gap-0.5 border-b border-r border-border p-1 text-left last:border-r-0 hover:bg-surface-alt ${
                delMesActual ? "bg-surface" : "bg-surface-alt/40"
              }`}
            >
              <span
                className={`mb-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                  esHoy ? "bg-primary-900 font-semibold text-white" : delMesActual ? "text-ink" : "text-ink-soft"
                }`}
              >
                {dia.getDate()}
              </span>
              {visibles.map((evento) => (
                <span key={evento.id} onClick={(e) => e.stopPropagation()}>
                  <EventoChip evento={evento} onEditar={onEditar} />
                </span>
              ))}
              {restantes > 0 && <span className="px-1.5 text-xs text-ink-soft">+{restantes} más</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
