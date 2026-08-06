import type { VistaCalendario } from "../types";

const DIAS_AGENDA = 90;

function inicioDeDia(fecha: Date): Date {
  const copia = new Date(fecha);
  copia.setHours(0, 0, 0, 0);
  return copia;
}

function finDeDia(fecha: Date): Date {
  const copia = new Date(fecha);
  copia.setHours(23, 59, 59, 999);
  return copia;
}

export function calcularRango(vista: VistaCalendario, fechaRef: Date): { desde: Date; hasta: Date } {
  if (vista === "dia") {
    return { desde: inicioDeDia(fechaRef), hasta: finDeDia(fechaRef) };
  }
  if (vista === "semana") {
    const desfase = (fechaRef.getDay() + 6) % 7;
    const desde = inicioDeDia(fechaRef);
    desde.setDate(desde.getDate() - desfase);
    const hasta = finDeDia(new Date(desde));
    hasta.setDate(hasta.getDate() + 6);
    return { desde, hasta };
  }
  if (vista === "agenda") {
    const desde = inicioDeDia(fechaRef);
    const hasta = finDeDia(new Date(desde));
    hasta.setDate(hasta.getDate() + DIAS_AGENDA);
    return { desde, hasta };
  }
  // "mes" — incluye los días de relleno de la grilla (42 celdas), para que
  // los eventos de los bordes del mes anterior/siguiente también se traigan.
  const primerDia = new Date(fechaRef.getFullYear(), fechaRef.getMonth(), 1);
  const desfaseInicio = (primerDia.getDay() + 6) % 7;
  const desde = inicioDeDia(new Date(primerDia));
  desde.setDate(desde.getDate() - desfaseInicio);
  const hasta = finDeDia(new Date(desde));
  hasta.setDate(hasta.getDate() + 41);
  return { desde, hasta };
}

export function avanzar(vista: VistaCalendario, fechaRef: Date, direccion: 1 | -1): Date {
  if (vista === "mes") {
    // `Date.setMonth()` no clampea el día: el 31 de enero + 1 mes desborda
    // a marzo en vez de quedar en el último día de febrero — mismo problema
    // ya resuelto del lado del backend, ver `calcular_proxima_fecha` en
    // Calibraciones (Sprint 7). Sin este clamp, navegar "mes siguiente"
    // repetidamente desde un día 29-31 salta meses de forma silenciosa.
    const mesObjetivo = fechaRef.getMonth() + direccion;
    const ultimoDiaMesObjetivo = new Date(fechaRef.getFullYear(), mesObjetivo + 1, 0).getDate();
    const nueva = new Date(fechaRef);
    nueva.setDate(1); // evita un desborde intermedio mientras el día todavía es el original
    nueva.setMonth(mesObjetivo);
    nueva.setDate(Math.min(fechaRef.getDate(), ultimoDiaMesObjetivo));
    return nueva;
  }
  const nueva = new Date(fechaRef);
  if (vista === "dia") nueva.setDate(nueva.getDate() + direccion);
  else if (vista === "semana") nueva.setDate(nueva.getDate() + 7 * direccion);
  else nueva.setDate(nueva.getDate() + DIAS_AGENDA * direccion);
  return nueva;
}
