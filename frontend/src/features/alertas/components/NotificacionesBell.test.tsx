import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { NotificacionesBell } from "./NotificacionesBell";

vi.mock("../api/alertasApi", () => ({
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
        <NotificacionesBell />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NotificacionesBell", () => {
  it("muestra un error explícito (no 'sin alertas activas') cuando el listado falla al cargar", async () => {
    const { listarAlertas, contarActivas } = await import("../api/alertasApi");
    vi.mocked(listarAlertas).mockRejectedValue(new Error("network error"));
    vi.mocked(contarActivas).mockResolvedValue({ activas: 0 });

    renderComponente();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: /notificaciones/i }));

    expect(await screen.findByText("No se pudo cargar")).toBeInTheDocument();
    expect(screen.queryByText("Sin alertas activas")).not.toBeInTheDocument();
  });

  it("muestra 'sin alertas activas' cuando el listado carga vacío correctamente", async () => {
    const { listarAlertas, contarActivas } = await import("../api/alertasApi");
    vi.mocked(listarAlertas).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 8 });
    vi.mocked(contarActivas).mockResolvedValue({ activas: 0 });

    renderComponente();
    const usuario = userEvent.setup();
    await usuario.click(screen.getByRole("button", { name: /notificaciones/i }));

    expect(await screen.findByText("Sin alertas activas")).toBeInTheDocument();
    expect(screen.queryByText("No se pudo cargar")).not.toBeInTheDocument();
  });
});
