export type ClaveConteoEquipos =
  | "equipos_operativos"
  | "equipos_en_mantenimiento"
  | "equipos_fuera_de_servicio"
  | "equipos_de_baja";

// Radio medio del anillo (entre el radio interno y externo) y grosor del
// trazo — define visualmente el donut vía `stroke-dasharray`.
export const RADIO = 66;
export const GROSOR = 24;
export const CIRCUNFERENCIA = 2 * Math.PI * RADIO;

/** Donut SVG hecho a mano en vez de `recharts`: con datos reales del
 * laboratorio, lo habitual es que una sola categoría concentre el 100% de
 * los equipos (todo "operativo", nada en las demás) — y `recharts@3` en
 * este proyecto renderiza esa situación (un único segmento con el 100% del
 * total) como un arco degenerado invisible, con o sin "endAngle" acotado a
 * menos de 360°. En vez de perseguir ese comportamiento interno no
 * documentado, se calcula el arco de cada segmento directamente contra la
 * circunferencia — es la misma matemática que cualquier gráfica de dona,
 * sin sorpresas de librería. */
export function arcosDelDonut(segmentos: { clave: ClaveConteoEquipos; color: string; valor: number }[]): {
  clave: ClaveConteoEquipos;
  color: string;
  dasharray: string;
  dashoffset: number;
}[] {
  const total = segmentos.reduce((suma, s) => suma + s.valor, 0);
  let acumulado = 0;
  return segmentos.map((s) => {
    const largo = (s.valor / total) * CIRCUNFERENCIA;
    const arco = { clave: s.clave, color: s.color, dasharray: `${largo} ${CIRCUNFERENCIA}`, dashoffset: -acumulado };
    acumulado += largo;
    return arco;
  });
}
