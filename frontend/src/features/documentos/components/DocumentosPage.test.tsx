import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { DocumentosPage } from "./DocumentosPage";

vi.mock("../api/documentosApi", () => ({
  listarDocumentos: vi.fn(),
  listarCarpetas: vi.fn(),
  obtenerCarpeta: vi.fn(),
  crearCarpeta: vi.fn(),
  alternarFavorito: vi.fn(),
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DocumentosPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DocumentosPage", () => {
  it("muestra un error explícito cuando el listado de documentos falla al cargar", async () => {
    const { listarDocumentos, listarCarpetas } = await import("../api/documentosApi");
    vi.mocked(listarDocumentos).mockRejectedValue(new Error("network error"));
    vi.mocked(listarCarpetas).mockResolvedValue([]);

    renderComponente();

    expect(await screen.findByText("No se pudo cargar el listado")).toBeInTheDocument();
    expect(screen.queryByText("Esta carpeta está vacía")).not.toBeInTheDocument();
  });

  it("muestra 'carpeta vacía' cuando el listado carga vacío correctamente", async () => {
    const { listarDocumentos, listarCarpetas } = await import("../api/documentosApi");
    vi.mocked(listarDocumentos).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });
    vi.mocked(listarCarpetas).mockResolvedValue([]);

    renderComponente();

    expect(await screen.findByText("Esta carpeta está vacía")).toBeInTheDocument();
    expect(screen.queryByText("No se pudo cargar el listado")).not.toBeInTheDocument();
  });
});
