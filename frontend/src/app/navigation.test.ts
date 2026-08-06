import { describe, expect, it } from "vitest";

import { NAV_ITEMS, navItemsParaRoles } from "./navigation";

describe("navItemsParaRoles", () => {
  it("un administrador ve todos los ítems, incluidos los restringidos", () => {
    const items = navItemsParaRoles(["administrador"]);
    expect(items.map((i) => i.label)).toEqual(NAV_ITEMS.map((i) => i.label));
  });

  it("un técnico no ve Reportes, Auditoría ni Usuarios", () => {
    const etiquetas = navItemsParaRoles(["tecnico"]).map((i) => i.label);
    expect(etiquetas).not.toContain("Reportes");
    expect(etiquetas).not.toContain("Auditoría");
    expect(etiquetas).not.toContain("Usuarios");
  });

  it("un técnico sí ve Configuración (RF-CFG-01: perfil propio es para cualquier rol)", () => {
    const etiquetas = navItemsParaRoles(["tecnico"]).map((i) => i.label);
    expect(etiquetas).toContain("Configuración");
  });

  it("calidad ve Auditoría pero no Usuarios", () => {
    const etiquetas = navItemsParaRoles(["calidad"]).map((i) => i.label);
    expect(etiquetas).toContain("Auditoría");
    expect(etiquetas).not.toContain("Usuarios");
  });

  it("un usuario con varios roles ve la unión de lo que cada rol permite", () => {
    // "consulta" solo no vería Reportes, pero si el mismo usuario también
    // tiene "metrologia" (que sí tiene reportes.generar), debe verlo.
    const etiquetas = navItemsParaRoles(["consulta", "metrologia"]).map((i) => i.label);
    expect(etiquetas).toContain("Reportes");
  });

  it("sin roles no se ve ningún ítem", () => {
    expect(navItemsParaRoles([])).toEqual([]);
  });

  it("un rol desconocido no ve nada", () => {
    expect(navItemsParaRoles(["rol_inexistente"])).toEqual([]);
  });
});
