import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AlertsSummary } from "./AlertsSummary";

vi.mock("@/features/alertas/api/alertasApi", () => ({
  listarAlertas: vi.fn(),
  contarActivas: vi.fn(),
  marcarLeida: vi.fn(),
  resolverManual: vi.fn(),
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AlertsSummary />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AlertsSummary", () => {
  it("no afirma que todo está en orden cuando el listado falla al cargar", async () => {
    const { listarAlertas } = await import("@/features/alertas/api/alertasApi");
    vi.mocked(listarAlertas).mockRejectedValue(new Error("network error"));

    renderComponente();

    expect(await screen.findByText(/No se pudo cargar el centro de alertas/)).toBeInTheDocument();
    expect(screen.queryByText(/Todos los equipos y procesos están dentro de parámetro/)).not.toBeInTheDocument();
  });

  it("muestra el mensaje de todo en orden cuando el listado carga vacío correctamente", async () => {
    const { listarAlertas } = await import("@/features/alertas/api/alertasApi");
    vi.mocked(listarAlertas).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    renderComponente();

    expect(await screen.findByText(/Todos los equipos y procesos están dentro de parámetro/)).toBeInTheDocument();
    expect(screen.queryByText(/No se pudo cargar el centro de alertas/)).not.toBeInTheDocument();
  });
});
