import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { IncidenciaQr } from "../types";
import { IncidenciasQrPendientes } from "./IncidenciasQrPendientes";

vi.mock("../api/qrApi", () => ({
  listarIncidencias: vi.fn(),
  actualizarEstadoIncidencia: vi.fn(),
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <IncidenciasQrPendientes />
    </QueryClientProvider>,
  );
}

function incidencia(overrides: Partial<IncidenciaQr> = {}): IncidenciaQr {
  return {
    id: "inc-1",
    equipo_id: "eq-1",
    equipo_codigo_interno: "EQ-01",
    equipo_nombre: "Centrífuga",
    descripcion: "El equipo hace ruido extraño.",
    contacto_nombre: "Juan Pérez",
    contacto_medio: null,
    estado: "pendiente",
    creado_en: "2026-08-01T10:00:00Z",
    ...overrides,
  };
}

describe("IncidenciasQrPendientes", () => {
  it("no renderiza nada cuando no hay incidencias pendientes ni en revisión", async () => {
    const { listarIncidencias } = await import("../api/qrApi");
    vi.mocked(listarIncidencias).mockResolvedValue([incidencia({ estado: "resuelta" })]);

    const { container } = renderComponente();

    // Espera a que la query resuelva antes de afirmar que no hay nada.
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(container).toBeEmptyDOMElement();
  });

  it("muestra la incidencia pendiente con los datos del equipo y quien la reportó", async () => {
    const { listarIncidencias } = await import("../api/qrApi");
    vi.mocked(listarIncidencias).mockResolvedValue([incidencia()]);

    renderComponente();

    expect(await screen.findByText(/EQ-01 · Centrífuga/)).toBeInTheDocument();
    expect(screen.getByText("El equipo hace ruido extraño.")).toBeInTheDocument();
    expect(screen.getByText(/Reportado por Juan Pérez/)).toBeInTheDocument();
    expect(screen.getByText("Pendiente de triage")).toBeInTheDocument();
  });

  it("marcar en revisión llama a la API con el siguiente estado", async () => {
    const { listarIncidencias, actualizarEstadoIncidencia } = await import("../api/qrApi");
    vi.mocked(listarIncidencias).mockResolvedValue([incidencia()]);
    vi.mocked(actualizarEstadoIncidencia).mockResolvedValue({ id: "inc-1", estado: "en_revision" });

    renderComponente();
    const usuario = userEvent.setup();

    await usuario.click(await screen.findByRole("button", { name: /marcar en revisión/i }));

    expect(actualizarEstadoIncidencia).toHaveBeenCalledWith("inc-1", "en_revision");
  });

  it("una incidencia en revisión ofrece la acción de marcar resuelta, no la de en revisión", async () => {
    const { listarIncidencias } = await import("../api/qrApi");
    vi.mocked(listarIncidencias).mockResolvedValue([incidencia({ estado: "en_revision" })]);

    renderComponente();

    expect(await screen.findByRole("button", { name: /marcar resuelta/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /marcar en revisión/i })).not.toBeInTheDocument();
  });
});
