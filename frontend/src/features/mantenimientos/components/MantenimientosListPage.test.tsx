import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { MantenimientosListPage } from "./MantenimientosListPage";

vi.mock("../api/mantenimientosApi", () => ({
  listarMantenimientos: vi.fn(),
}));

vi.mock("@/features/equipos/api/equiposApi", () => ({
  listarEquipos: vi.fn(),
}));

vi.mock("@/features/qr/components/IncidenciasQrPendientes", () => ({
  IncidenciasQrPendientes: () => null,
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <MantenimientosListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MantenimientosListPage", () => {
  it("muestra un error explícito cuando el listado falla al cargar", async () => {
    const { listarMantenimientos } = await import("../api/mantenimientosApi");
    const { listarEquipos } = await import("@/features/equipos/api/equiposApi");
    vi.mocked(listarMantenimientos).mockRejectedValue(new Error("network error"));
    vi.mocked(listarEquipos).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    renderComponente();

    expect(await screen.findByText("No se pudo cargar el listado")).toBeInTheDocument();
    expect(screen.queryByText("Sin mantenimientos registrados")).not.toBeInTheDocument();
  });

  it("muestra 'sin mantenimientos' cuando el listado carga vacío correctamente", async () => {
    const { listarMantenimientos } = await import("../api/mantenimientosApi");
    const { listarEquipos } = await import("@/features/equipos/api/equiposApi");
    vi.mocked(listarMantenimientos).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });
    vi.mocked(listarEquipos).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    renderComponente();

    expect(await screen.findByText("Sin mantenimientos registrados")).toBeInTheDocument();
    expect(screen.queryByText("No se pudo cargar el listado")).not.toBeInTheDocument();
  });
});
