import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Usuario } from "../types";
import { PanelUsuario } from "./PanelUsuario";

vi.mock("../api/usuariosApi", () => ({
  listarRoles: vi.fn(),
  listarSesiones: vi.fn(),
  activarUsuario: vi.fn(),
  desactivarUsuario: vi.fn(),
  actualizarUsuario: vi.fn(),
  asignarRoles: vi.fn(),
  cerrarSesion: vi.fn(),
}));

function usuarioActivo(overrides: Partial<Usuario> = {}): Usuario {
  return {
    id: "usr-1",
    nombre_completo: "Laura Ramírez",
    correo: "laura@demo.dev",
    estado: "activo",
    debe_cambiar_password: false,
    roles: ["tecnico"],
    ...overrides,
  };
}

function renderPanel(usuario: Usuario) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PanelUsuario usuario={usuario} />
    </QueryClientProvider>,
  );
}

async function abrirConfirmacion() {
  const usuarioInteraccion = userEvent.setup();
  const boton = screen.getByRole("button", { name: "Desactivar" });
  await usuarioInteraccion.click(boton);
  const dialogo = await screen.findByRole("alertdialog");
  return { usuarioInteraccion, boton, dialogo };
}

describe("PanelUsuario — confirmación al desactivar (I10)", () => {
  // Los mocks de "../api/usuariosApi" son spies compartidos por todo el
  // archivo (vi.mock se hoistea una sola vez) — sin limpiar entre tests, el
  // conteo de llamadas de un test se arrastra al siguiente.
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("no muestra el diálogo hasta hacer clic en Desactivar", async () => {
    const { listarRoles, listarSesiones } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    renderPanel(usuarioActivo());

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
  });

  it("cancelar no ejecuta la desactivación", async () => {
    const { listarRoles, listarSesiones, desactivarUsuario } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    renderPanel(usuarioActivo());

    const { usuarioInteraccion } = await abrirConfirmacion();
    await usuarioInteraccion.click(screen.getByRole("button", { name: "Cancelar" }));

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(desactivarUsuario).not.toHaveBeenCalled();
  });

  it("confirmar ejecuta la desactivación exactamente una vez", async () => {
    const { listarRoles, listarSesiones, desactivarUsuario } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    vi.mocked(desactivarUsuario).mockResolvedValue(usuarioActivo({ estado: "inactivo" }));
    renderPanel(usuarioActivo());

    const { usuarioInteraccion } = await abrirConfirmacion();
    await usuarioInteraccion.click(screen.getByRole("button", { name: "Sí, desactivar" }));

    await waitFor(() => expect(desactivarUsuario).toHaveBeenCalledTimes(1));
    expect(desactivarUsuario).toHaveBeenCalledWith("usr-1");
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
  });

  it("el diálogo se cierra con Escape sin ejecutar la acción", async () => {
    const { listarRoles, listarSesiones, desactivarUsuario } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    renderPanel(usuarioActivo());

    const { usuarioInteraccion } = await abrirConfirmacion();
    await usuarioInteraccion.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
    expect(desactivarUsuario).not.toHaveBeenCalled();
  });

  it("el foco vuelve al botón 'Desactivar' al cancelar", async () => {
    const { listarRoles, listarSesiones } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    renderPanel(usuarioActivo());

    const { usuarioInteraccion, boton } = await abrirConfirmacion();
    await usuarioInteraccion.click(screen.getByRole("button", { name: "Cancelar" }));

    await waitFor(() => expect(boton).toHaveFocus());
  });

  it("el foco vuelve al botón 'Desactivar' al cerrar con Escape", async () => {
    const { listarRoles, listarSesiones } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    renderPanel(usuarioActivo());

    const { usuarioInteraccion, boton } = await abrirConfirmacion();
    await usuarioInteraccion.keyboard("{Escape}");

    await waitFor(() => expect(boton).toHaveFocus());
  });

  it("el foco vuelve al botón 'Desactivar' tras confirmar", async () => {
    const { listarRoles, listarSesiones, desactivarUsuario } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    vi.mocked(desactivarUsuario).mockResolvedValue(usuarioActivo({ estado: "inactivo" }));
    renderPanel(usuarioActivo());

    const { usuarioInteraccion, boton } = await abrirConfirmacion();
    await usuarioInteraccion.click(screen.getByRole("button", { name: "Sí, desactivar" }));

    await waitFor(() => expect(boton).toHaveFocus());
  });

  it("el foco de apertura entra al diálogo y Tab en el último botón envuelve al primero", async () => {
    const { listarRoles, listarSesiones } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    renderPanel(usuarioActivo());

    const { usuarioInteraccion } = await abrirConfirmacion();
    const confirmar = screen.getByRole("button", { name: "Sí, desactivar" });
    const cancelar = screen.getByRole("button", { name: "Cancelar" });

    expect(confirmar).toHaveFocus();
    await usuarioInteraccion.tab();
    expect(cancelar).toHaveFocus();
    await usuarioInteraccion.tab();
    expect(confirmar).toHaveFocus();
  });

  it("activar un usuario inactivo no requiere confirmación (sin regresión del flujo existente)", async () => {
    const { listarRoles, listarSesiones, activarUsuario } = await import("../api/usuariosApi");
    vi.mocked(listarRoles).mockResolvedValue([]);
    vi.mocked(listarSesiones).mockResolvedValue([]);
    vi.mocked(activarUsuario).mockResolvedValue(usuarioActivo());
    renderPanel(usuarioActivo({ estado: "inactivo" }));
    const usuarioInteraccion = userEvent.setup();

    await usuarioInteraccion.click(screen.getByRole("button", { name: "Activar" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    await waitFor(() => expect(activarUsuario).toHaveBeenCalledWith("usr-1"));
  });
});
