import { describe, expect, it } from "vitest";

import { arcosDelDonut, CIRCUNFERENCIA } from "./EquipmentStatusDonut.logic";

describe("arcosDelDonut", () => {
  it("un único segmento con el 100% del total cubre toda la circunferencia", () => {
    // Caso real más común: todos los equipos "operativos", el resto en 0.
    // Es justo el caso que `recharts@3` renderizaba como un arco
    // degenerado invisible — motivo por el que este cálculo es a mano.
    const [arco] = arcosDelDonut([{ clave: "equipos_operativos", color: "#16A34A", valor: 4 }]);
    const [largo] = arco!.dasharray.split(" ").map(Number);
    expect(largo).toBeCloseTo(CIRCUNFERENCIA, 5);
    expect(arco!.dashoffset).toBeCloseTo(0, 5);
  });

  it("reparte la circunferencia proporcionalmente entre varios segmentos", () => {
    const arcos = arcosDelDonut([
      { clave: "equipos_operativos", color: "#16A34A", valor: 3 },
      { clave: "equipos_en_mantenimiento", color: "#F59E0B", valor: 1 },
    ]);
    const largoOperativos = Number(arcos[0]!.dasharray.split(" ")[0]!);
    const largoMantenimiento = Number(arcos[1]!.dasharray.split(" ")[0]!);

    expect(largoOperativos).toBeCloseTo(CIRCUNFERENCIA * 0.75, 5);
    expect(largoMantenimiento).toBeCloseTo(CIRCUNFERENCIA * 0.25, 5);
    // La suma de todos los arcos siempre debe cerrar la circunferencia
    // completa, sin importar en cuántos segmentos se reparta.
    expect(largoOperativos + largoMantenimiento).toBeCloseTo(CIRCUNFERENCIA, 5);
  });

  it("cada segmento arranca exactamente donde termina el anterior (offset acumulado)", () => {
    const arcos = arcosDelDonut([
      { clave: "equipos_operativos", color: "#16A34A", valor: 1 },
      { clave: "equipos_en_mantenimiento", color: "#F59E0B", valor: 1 },
      { clave: "equipos_fuera_de_servicio", color: "#DC2626", valor: 2 },
    ]);
    const largos = arcos.map((a) => Number(a.dasharray.split(" ")[0]));

    expect(arcos[0]!.dashoffset).toBeCloseTo(0, 5);
    expect(arcos[1]!.dashoffset).toBeCloseTo(-largos[0]!, 5);
    expect(arcos[2]!.dashoffset).toBeCloseTo(-(largos[0]! + largos[1]!), 5);
  });
});
