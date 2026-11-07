import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { EquipoFormPage } from "./EquipoFormPage";

vi.mock("../hooks/useEquipos", () => ({
  useEquipo: vi.fn(() => ({ data: undefined, isLoading: false })),
  useCategorias: vi.fn(() => ({ data: [] })),
  useAreas: vi.fn(() => ({ data: [] })),
  useCrearEquipo: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useActualizarEquipo: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}));

function renderFormulario() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/equipos/nuevo"]}>
        <EquipoFormPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("EquipoFormPage", () => {
  it("muestra el mensaje en español de zod cuando el código interno está vacío", async () => {
    renderFormulario();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: /crear equipo/i }));

    expect(await screen.findByText("El código interno es obligatorio.")).toBeInTheDocument();
  });

  it("muestra un mensaje en español (no en inglés) cuando el código interno supera los 50 caracteres", async () => {
    renderFormulario();
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/código interno/i), "x".repeat(51));
    await usuario.type(screen.getByLabelText(/^nombre$/i), "Equipo de prueba");
    await usuario.click(screen.getByRole("button", { name: /crear equipo/i }));

    expect(
      await screen.findByText("Demasiado grande: se esperaba que texto tuviera <=50 caracteres"),
    ).toBeInTheDocument();
  });
});
