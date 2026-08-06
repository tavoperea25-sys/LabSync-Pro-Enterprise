import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { CriticosPage } from "./CriticosPage";

vi.mock("../api/calibracionesApi", () => ({
  listarCriticos: vi.fn(),
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <CriticosPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CriticosPage", () => {
  it("muestra un error explícito cuando el listado falla al cargar", async () => {
    const { listarCriticos } = await import("../api/calibracionesApi");
    vi.mocked(listarCriticos).mockRejectedValue(new Error("network error"));

    renderComponente();

    expect(await screen.findByText("No se pudo cargar el listado")).toBeInTheDocument();
    expect(screen.queryByText("Sin equipos críticos")).not.toBeInTheDocument();
  });

  it("muestra 'sin equipos críticos' cuando el listado carga vacío correctamente", async () => {
    const { listarCriticos } = await import("../api/calibracionesApi");
    vi.mocked(listarCriticos).mockResolvedValue([]);

    renderComponente();

    expect(await screen.findByText("Sin equipos críticos")).toBeInTheDocument();
    expect(screen.queryByText("No se pudo cargar el listado")).not.toBeInTheDocument();
  });
});
