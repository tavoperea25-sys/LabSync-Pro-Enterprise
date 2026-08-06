import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AlertasPage } from "./AlertasPage";

vi.mock("../api/alertasApi", () => ({
  listarAlertas: vi.fn(),
  marcarLeida: vi.fn(),
  resolverManual: vi.fn(),
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AlertasPage />
    </QueryClientProvider>,
  );
}

describe("AlertasPage", () => {
  it("muestra un error explícito (no 'sin alertas') cuando el listado falla al cargar", async () => {
    const { listarAlertas } = await import("../api/alertasApi");
    vi.mocked(listarAlertas).mockRejectedValue(new Error("network error"));

    renderComponente();

    expect(await screen.findByText("No se pudo cargar el listado")).toBeInTheDocument();
    expect(screen.queryByText("Sin alertas")).not.toBeInTheDocument();
  });

  it("muestra 'sin alertas' cuando el listado carga vacío correctamente", async () => {
    const { listarAlertas } = await import("../api/alertasApi");
    vi.mocked(listarAlertas).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    renderComponente();

    expect(await screen.findByText("Sin alertas")).toBeInTheDocument();
    expect(screen.queryByText("No se pudo cargar el listado")).not.toBeInTheDocument();
  });
});
