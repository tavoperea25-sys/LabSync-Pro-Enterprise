import { useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/shared/components/ui/button";

import type { Calibracion } from "../types";
import { ETIQUETAS_RESULTADO } from "../types";

/** RF-CAL-04 / HU-MET-02 — tendencia de incertidumbre de medición en el
 * tiempo (el indicador numérico real de desempeño metrológico; "conforme/no
 * conforme" es categórico, no graficable como línea). Siempre acompañada de
 * una tabla de datos accesible (docs/11-design-system.md, regla
 * `data-table`) — nunca solo el gráfico. */
export function TendenciaCalibraciones({ calibraciones }: { calibraciones: Calibracion[] }) {
  const [mostrarTabla, setMostrarTabla] = useState(false);

  const puntos = [...calibraciones]
    .filter((c) => c.incertidumbre !== null)
    .sort((a, b) => a.fecha_calibracion.localeCompare(b.fecha_calibracion))
    .map((c) => ({
      fecha: c.fecha_calibracion,
      incertidumbre: Number(c.incertidumbre),
      resultado: c.resultado,
    }));

  if (calibraciones.length === 0) {
    return <p className="text-sm text-ink-soft">Aún no hay calibraciones registradas para este equipo.</p>;
  }

  if (puntos.length === 0) {
    return (
      <p className="text-sm text-ink-soft">
        Ninguna calibración registrada tiene incertidumbre de medición — no hay tendencia que graficar.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-soft">
          Tendencia de incertidumbre
        </h3>
        <Button variant="secondary" size="sm" onClick={() => setMostrarTabla((v) => !v)}>
          {mostrarTabla ? "Ver gráfica" : "Ver tabla de datos"}
        </Button>
      </div>

      {mostrarTabla ? (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-alt text-left text-xs font-semibold uppercase tracking-wide text-ink-soft">
                <th scope="col" className="px-3 py-2">Fecha</th>
                <th scope="col" className="px-3 py-2">Incertidumbre</th>
                <th scope="col" className="px-3 py-2">Resultado</th>
              </tr>
            </thead>
            <tbody>
              {puntos.map((p) => (
                <tr key={p.fecha} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 text-ink">{p.fecha}</td>
                  <td className="px-3 py-2 text-ink">{p.incertidumbre}</td>
                  <td className="px-3 py-2 text-ink-soft">{ETIQUETAS_RESULTADO[p.resultado]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-64 w-full" role="img" aria-label="Gráfica de línea de la tendencia de incertidumbre de medición en el tiempo">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={puntos} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="fecha" tick={{ fontSize: 12 }} stroke="var(--text-secondary)" />
              <YAxis tick={{ fontSize: 12 }} stroke="var(--text-secondary)" />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
                formatter={(valor) => [valor, "Incertidumbre"]}
              />
              <Line type="monotone" dataKey="incertidumbre" stroke="#198754" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
