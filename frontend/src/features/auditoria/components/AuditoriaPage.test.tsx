import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { LogAuditoria } from "../types";

import { AuditoriaPage } from "./AuditoriaPage";

vi.mock("../api/auditoriaApi", () => ({
  listarAuditoria: vi.fn(),
  obtenerValoresFiltro: vi.fn(),
  exportarAuditoria: vi.fn(),
}));

vi.mock("@/features/usuarios/api/usuariosApi", () => ({
  listarUsuarios: vi.fn(),
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuditoriaPage />
    </QueryClientProvider>,
  );
}

describe("AuditoriaPage", () => {
  it("muestra un error explícito cuando el listado falla al cargar", async () => {
    const { listarAuditoria, obtenerValoresFiltro } = await import("../api/auditoriaApi");
    const { listarUsuarios } = await import("@/features/usuarios/api/usuariosApi");
    vi.mocked(listarAuditoria).mockRejectedValue(new Error("network error"));
    vi.mocked(obtenerValoresFiltro).mockResolvedValue({ modulos: [], acciones: [] });
    vi.mocked(listarUsuarios).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    renderComponente();

    expect(await screen.findByText("No se pudo cargar el listado")).toBeInTheDocument();
    expect(screen.queryByText("Sin registros")).not.toBeInTheDocument();
  });

  it("muestra 'sin registros' cuando el listado carga vacío correctamente", async () => {
    const { listarAuditoria, obtenerValoresFiltro } = await import("../api/auditoriaApi");
    const { listarUsuarios } = await import("@/features/usuarios/api/usuariosApi");
    vi.mocked(listarAuditoria).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });
    vi.mocked(obtenerValoresFiltro).mockResolvedValue({ modulos: [], acciones: [] });
    vi.mocked(listarUsuarios).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    renderComponente();

    expect(await screen.findByText("Sin registros")).toBeInTheDocument();
    expect(screen.queryByText("No se pudo cargar el listado")).not.toBeInTheDocument();
  });

  it("pagina: avanza a la página siguiente y deshabilita 'Anterior' en la primera", async () => {
    const { listarAuditoria, obtenerValoresFiltro } = await import("../api/auditoriaApi");
    const { listarUsuarios } = await import("@/features/usuarios/api/usuariosApi");
    vi.mocked(obtenerValoresFiltro).mockResolvedValue({ modulos: [], acciones: [] });
    vi.mocked(listarUsuarios).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    const log = (id: string): LogAuditoria => ({
      id,
      usuario_id: null,
      ip_origen: null,
      modulo: "equipos",
      accion: "crear",
      entidad_tipo: "equipo",
      entidad_id: null,
      valor_anterior: null,
      valor_nuevo: null,
      creado_en: "2026-08-05T10:00:00Z",
    });
    vi.mocked(listarAuditoria).mockImplementation(async (filtros) => {
      if ((filtros.pagina ?? 1) === 1) {
        return { items: Array.from({ length: 20 }, (_, i) => log(`p1-${i}`)), total: 25, pagina: 1, tamano_pagina: 20 };
      }
      return { items: Array.from({ length: 5 }, (_, i) => log(`p2-${i}`)), total: 25, pagina: 2, tamano_pagina: 20 };
    });

    renderComponente();
    const usuario = userEvent.setup();

    expect(await screen.findByText("Página 1 de 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /anterior/i })).toBeDisabled();

    await usuario.click(screen.getByRole("button", { name: /siguiente/i }));

    expect(await screen.findByText("Página 2 de 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /siguiente/i })).toBeDisabled();
    expect(listarAuditoria).toHaveBeenLastCalledWith(expect.objectContaining({ pagina: 2 }));
  });
});
