import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Usuario } from "../types";

import { UsuariosListPage } from "./UsuariosListPage";

vi.mock("../api/usuariosApi", () => ({
  listarUsuarios: vi.fn(),
  listarRoles: vi.fn(),
  crearUsuario: vi.fn(),
}));

function renderComponente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <UsuariosListPage />
    </QueryClientProvider>,
  );
}

describe("UsuariosListPage", () => {
  it("muestra un error explícito cuando el listado falla al cargar", async () => {
    const { listarUsuarios } = await import("../api/usuariosApi");
    vi.mocked(listarUsuarios).mockRejectedValue(new Error("network error"));

    renderComponente();

    expect(await screen.findByText("No se pudo cargar el listado")).toBeInTheDocument();
    expect(screen.queryByText("Sin usuarios")).not.toBeInTheDocument();
  });

  it("muestra 'sin usuarios' cuando el listado carga vacío correctamente", async () => {
    const { listarUsuarios } = await import("../api/usuariosApi");
    vi.mocked(listarUsuarios).mockResolvedValue({ items: [], total: 0, pagina: 1, tamano_pagina: 20 });

    renderComponente();

    expect(await screen.findByText("Sin usuarios")).toBeInTheDocument();
    expect(screen.queryByText("No se pudo cargar el listado")).not.toBeInTheDocument();
  });

  it("pagina: avanza a la página siguiente y deshabilita 'Anterior' en la primera", async () => {
    const { listarUsuarios } = await import("../api/usuariosApi");

    const usuario = (id: string): Usuario => ({
      id,
      nombre_completo: `Usuario ${id}`,
      correo: `${id}@lsp.gov.co`,
      estado: "activo",
      debe_cambiar_password: false,
      roles: ["tecnico"],
    });
    vi.mocked(listarUsuarios).mockImplementation(async (pagina = 1) => {
      if (pagina === 1) {
        return { items: Array.from({ length: 20 }, (_, i) => usuario(`p1-${i}`)), total: 25, pagina: 1, tamano_pagina: 20 };
      }
      return { items: Array.from({ length: 5 }, (_, i) => usuario(`p2-${i}`)), total: 25, pagina: 2, tamano_pagina: 20 };
    });

    renderComponente();
    const usuarioDePrueba = userEvent.setup();

    expect(await screen.findByText("Página 1 de 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /anterior/i })).toBeDisabled();

    await usuarioDePrueba.click(screen.getByRole("button", { name: /siguiente/i }));

    expect(await screen.findByText("Página 2 de 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /siguiente/i })).toBeDisabled();
    expect(listarUsuarios).toHaveBeenLastCalledWith(2, undefined);
  });
});
