import { describe, expect, it } from "vitest";

import type { EventoCalendario } from "../types";
import { agruparEventosPorDia, mismodia } from "./VistaMes.logic";

function evento(overrides: Partial<EventoCalendario> & Pick<EventoCalendario, "id" | "fecha">): EventoCalendario {
  return {
    tipo: "institucional",
    titulo: "Evento",
    descripcion: null,
    origen_tipo: null,
    origen_id: null,
    editable: true,
    ...overrides,
  };
}

describe("mismodia", () => {
  it("reconoce el mismo día cuando el ISO cae a mediodía UTC (convención del backend)", () => {
    // El backend ancla fechas sintetizadas (calibraciones, mantenimientos, etc.)
    // a mediodía UTC para que la comparación de "día" sea estable sin importar
    // el huso horario de quien la vea (ver Sprint 9). Esta prueba documenta esa
    // convención; no la puede demostrar por sí sola porque el runner corre en
    // UTC, donde medianoche y mediodía UTC caen igual en el mismo día local.
    const celda = new Date(2026, 5, 15); // 15 de junio local, medianoche local
    expect(mismodia(celda, "2026-06-15T12:00:00Z")).toBe(true);
  });

  it("no confunde días distintos aunque estén a menos de 24h de diferencia", () => {
    const celda = new Date(2026, 5, 15);
    expect(mismodia(celda, "2026-06-16T12:00:00Z")).toBe(false);
    expect(mismodia(celda, "2026-06-14T12:00:00Z")).toBe(false);
  });

  it("compara año, mes y día — no solo el día del mes", () => {
    const celda = new Date(2026, 5, 15);
    expect(mismodia(celda, "2025-06-15T12:00:00Z")).toBe(false);
    expect(mismodia(celda, "2026-07-15T12:00:00Z")).toBe(false);
  });

  it("un ISO con fecha y hora exactas del mismo día local sigue contando como el mismo día", () => {
    const celda = new Date(2026, 5, 15);
    expect(mismodia(celda, new Date(2026, 5, 15, 9, 0).toISOString())).toBe(true);
  });
});

describe("agruparEventosPorDia (M10 — base de la memoización de VistaMes)", () => {
  it("agrupa varios eventos del mismo día bajo la misma clave", () => {
    const a = evento({ id: "a", fecha: new Date(2026, 5, 15, 8, 0).toISOString() });
    const b = evento({ id: "b", fecha: new Date(2026, 5, 15, 14, 0).toISOString() });
    const c = evento({ id: "c", fecha: new Date(2026, 5, 16, 8, 0).toISOString() });

    const mapa = agruparEventosPorDia([a, b, c]);

    expect(mapa.get(`2026-5-15`)).toEqual([a, b]);
    expect(mapa.get(`2026-5-16`)).toEqual([c]);
  });

  it("preserva el orden original de entrada dentro de cada día (mismo resultado que .filter())", () => {
    const primero = evento({ id: "primero", fecha: new Date(2026, 5, 15, 9, 0).toISOString() });
    const segundo = evento({ id: "segundo", fecha: new Date(2026, 5, 15, 7, 0).toISOString() });

    const mapa = agruparEventosPorDia([primero, segundo]);

    expect(mapa.get(`2026-5-15`)?.map((e) => e.id)).toEqual(["primero", "segundo"]);
  });

  it("no crea entradas para días sin eventos y devuelve un mapa vacío para un arreglo vacío", () => {
    const mapa = agruparEventosPorDia([]);
    expect(mapa.size).toBe(0);
    expect(mapa.get("2026-5-15")).toBeUndefined();
  });

  it("no mezcla eventos del mismo día del mes en años o meses distintos", () => {
    const juninio2026 = evento({ id: "jun-2026", fecha: new Date(2026, 5, 15, 8, 0).toISOString() });
    const julio2026 = evento({ id: "jul-2026", fecha: new Date(2026, 6, 15, 8, 0).toISOString() });
    const junio2027 = evento({ id: "jun-2027", fecha: new Date(2027, 5, 15, 8, 0).toISOString() });

    const mapa = agruparEventosPorDia([juninio2026, julio2026, junio2027]);

    expect(mapa.get("2026-5-15")).toEqual([juninio2026]);
    expect(mapa.get("2026-6-15")).toEqual([julio2026]);
    expect(mapa.get("2027-5-15")).toEqual([junio2027]);
  });
});
