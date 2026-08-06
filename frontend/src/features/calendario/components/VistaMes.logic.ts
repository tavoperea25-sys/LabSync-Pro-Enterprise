import type { EventoCalendario } from "../types";

export function celdasDelMes(fechaDeReferencia: Date): Date[] {
  const primerDia = new Date(fechaDeReferencia.getFullYear(), fechaDeReferencia.getMonth(), 1);
  // Lunes=0 ... Domingo=6 (getDay() nativo es Domingo=0, se rota).
  const desfaseInicio = (primerDia.getDay() + 6) % 7;
  const inicio = new Date(primerDia);
  inicio.setDate(inicio.getDate() - desfaseInicio);

  const celdas: Date[] = [];
  for (let i = 0; i < 42; i++) {
    const dia = new Date(inicio);
    dia.setDate(dia.getDate() + i);
    celdas.push(dia);
  }
  return celdas;
}

export function mismodia(a: Date, iso: string): boolean {
  const b = new Date(iso);
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

export function claveDia(fecha: Date): string {
  return `${fecha.getFullYear()}-${fecha.getMonth()}-${fecha.getDate()}`;
}

/** Agrupa una sola vez por día — usado por `VistaMes` para no filtrar el
 * arreglo completo de eventos 42 veces por render (una por celda). */
export function agruparEventosPorDia(eventos: EventoCalendario[]): Map<string, EventoCalendario[]> {
  const mapa = new Map<string, EventoCalendario[]>();
  for (const evento of eventos) {
    const clave = claveDia(new Date(evento.fecha));
    const delDia = mapa.get(clave);
    if (delDia) {
      delDia.push(evento);
    } else {
      mapa.set(clave, [evento]);
    }
  }
  return mapa;
}
