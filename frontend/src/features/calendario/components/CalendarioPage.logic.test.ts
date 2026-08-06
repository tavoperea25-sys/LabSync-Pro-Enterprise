import { describe, expect, it } from "vitest";

import { avanzar, calcularRango } from "./CalendarioPage.logic";

/** Compara por partes de fecha LOCALES, nunca `toISOString()` (que
 * convierte a UTC y volvería estas pruebas dependientes del huso horario
 * de quien las corra) — `calcularRango`/`avanzar` operan enteramente con
 * getters/setters locales de `Date`, así que la comparación debe hacerlo
 * también. */
function fechaLocal(fecha: Date): string {
  const anio = fecha.getFullYear();
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${anio}-${mes}-${dia}`;
}

describe("calcularRango", () => {
  it("vista 'dia' cubre exactamente ese día", () => {
    const { desde, hasta } = calcularRango("dia", new Date(2026, 5, 15, 14, 30));
    expect(fechaLocal(desde)).toBe("2026-06-15");
    expect(desde.getHours()).toBe(0);
    expect(fechaLocal(hasta)).toBe("2026-06-15");
    expect(hasta.getHours()).toBe(23);
  });

  it("vista 'semana' empieza en lunes, sin importar qué día de la semana sea la referencia", () => {
    // Miércoles 17 de junio de 2026 -> la semana debe ir de lunes 15 a domingo 21.
    const { desde, hasta } = calcularRango("semana", new Date(2026, 5, 17));
    expect(desde.getDay()).toBe(1); // lunes
    expect(fechaLocal(desde)).toBe("2026-06-15");
    expect(hasta.getDay()).toBe(0); // domingo
    expect(fechaLocal(hasta)).toBe("2026-06-21");
  });

  it("vista 'semana' con referencia en domingo retrocede hasta el lunes de esa misma semana", () => {
    // Domingo 21 de junio de 2026 pertenece a la semana que empezó el 15.
    const { desde } = calcularRango("semana", new Date(2026, 5, 21));
    expect(fechaLocal(desde)).toBe("2026-06-15");
  });

  it("vista 'mes' arranca en el lunes on/antes del día 1 y cubre una grilla de 42 días", () => {
    // 1 de junio de 2026 es lunes -> la grilla arranca exactamente ahí.
    const { desde, hasta } = calcularRango("mes", new Date(2026, 5, 15));
    expect(desde.getDay()).toBe(1);
    expect(fechaLocal(desde)).toBe("2026-06-01");
    const diasEnGrilla = Math.round((hasta.getTime() - desde.getTime()) / 86_400_000);
    expect(diasEnGrilla).toBe(42); // 42 celdas = desde..desde+41 días inclusive
  });

  it("vista 'mes' con el día 1 a mitad de semana retrocede hasta el lunes anterior", () => {
    // 1 de julio de 2026 es miércoles -> la grilla debe arrancar el lunes 29 de junio.
    const { desde } = calcularRango("mes", new Date(2026, 6, 10));
    expect(desde.getDay()).toBe(1);
    expect(fechaLocal(desde)).toBe("2026-06-29");
  });

  it("vista 'agenda' cubre hoy más 90 días (91 días en total)", () => {
    const { desde, hasta } = calcularRango("agenda", new Date(2026, 0, 1));
    const dias = Math.round((hasta.getTime() - desde.getTime()) / 86_400_000);
    expect(dias).toBe(91);
  });
});

describe("avanzar", () => {
  it("vista 'dia' suma o resta un día", () => {
    const base = new Date(2026, 5, 15);
    expect(fechaLocal(avanzar("dia", base, 1))).toBe("2026-06-16");
    expect(fechaLocal(avanzar("dia", base, -1))).toBe("2026-06-14");
  });

  it("vista 'semana' suma o resta 7 días", () => {
    const base = new Date(2026, 5, 15);
    expect(fechaLocal(avanzar("semana", base, 1))).toBe("2026-06-22");
    expect(fechaLocal(avanzar("semana", base, -1))).toBe("2026-06-08");
  });

  it("vista 'mes' cruza el año correctamente", () => {
    expect(fechaLocal(avanzar("mes", new Date(2026, 11, 15), 1))).toBe("2027-01-15");
    expect(fechaLocal(avanzar("mes", new Date(2026, 0, 15), -1))).toBe("2025-12-15");
  });

  it("vista 'mes' desde el día 31 no se desborda a otro mes (regresión)", () => {
    // Sin el clamp de día, `Date.setMonth()` normaliza "31 de febrero" a
    // marzo — un usuario viendo el 31 de enero y pidiendo "mes siguiente"
    // terminaría viendo marzo, saltándose febrero por completo.
    const resultado = avanzar("mes", new Date(2026, 0, 31), 1);
    expect(resultado.getMonth()).toBe(1); // febrero, no marzo
    expect(fechaLocal(resultado)).toBe("2026-02-28"); // último día de febrero 2026 (no bisiesto)
  });

  it("vista 'mes' desde el día 31 retrocediendo también clampea al mes correcto", () => {
    const resultado = avanzar("mes", new Date(2026, 2, 31), -1); // 31 de marzo
    expect(resultado.getMonth()).toBe(1); // febrero
    expect(fechaLocal(resultado)).toBe("2026-02-28");
  });

  it("vista 'mes' preserva el día cuando el mes destino sí lo tiene", () => {
    const resultado = avanzar("mes", new Date(2026, 0, 15), 1);
    expect(fechaLocal(resultado)).toBe("2026-02-15");
  });

  it("vista 'agenda' suma o resta 90 días", () => {
    const base = new Date(2026, 0, 1);
    const dias = Math.round((avanzar("agenda", base, 1).getTime() - base.getTime()) / 86_400_000);
    expect(dias).toBe(90);
  });
});
