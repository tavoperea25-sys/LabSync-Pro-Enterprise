import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/features/auth/hooks/AuthProvider";
import type { Usuario } from "@/features/auth/types";

import { ConfiguracionPage } from "./ConfiguracionPage";

vi.mock("@/features/auth/api/authApi", () => ({
  obtenerUsuarioActual: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("../api/configuracionApi", () => ({
  obtenerConfiguracion: vi.fn().mockResolvedValue({
    umbral_alerta_calibracion_dias: 30,
    umbral_alerta_mantenimiento_dias: 15,
    umbral_alerta_documento_dias: 30,
    politica_password: null,
    mapeo_estados_mantenimiento: null,
  }),
  obtenerInstitucion: vi.fn().mockResolvedValue({
    id: "inst-1",
    nombre: "Laboratorio de Salud Pública",
    slug: "lsp",
    logo_url: null,
    logo_object_key: null,
  }),
  listarCategorias: vi.fn().mockResolvedValue([]),
  listarAreas: vi.fn().mockResolvedValue([]),
}));

function usuarioBase(roles: string[]): Usuario {
  return {
    id: "u-1",
    nombre_completo: "Ana Pérez",
    correo: "ana@lsp.gov.co",
    roles,
    debe_cambiar_password: false,
    foto_url: null,
    foto_object_key: null,
  };
}

async function renderConfiguracion(roles: string[]) {
  const { obtenerUsuarioActual } = await import("@/features/auth/api/authApi");
  vi.mocked(obtenerUsuarioActual).mockResolvedValue(usuarioBase(roles));

  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/configuracion"]}>
        <AuthProvider>
          <ConfiguracionPage />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await waitFor(() => screen.getByRole("navigation", { name: /secciones de configuración/i }));
}

describe("ConfiguracionPage — gating por rol", () => {
  it("un técnico (no admin) solo ve la pestaña 'Mi perfil'", async () => {
    await renderConfiguracion(["tecnico"]);

    expect(screen.getByRole("button", { name: /mi perfil/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^laboratorio$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^alertas$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /categorías y áreas/i })).not.toBeInTheDocument();
  });

  it("un administrador ve las 4 pestañas", async () => {
    await renderConfiguracion(["administrador"]);

    expect(screen.getByRole("button", { name: /mi perfil/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^laboratorio$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^alertas$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /categorías y áreas/i })).toBeInTheDocument();
  });

  it("un administrador puede cambiar a la pestaña 'Laboratorio' y ver sus datos", async () => {
    await renderConfiguracion(["administrador"]);
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: /^laboratorio$/i }));

    expect(await screen.findByDisplayValue("Laboratorio de Salud Pública")).toBeInTheDocument();
  });

  it("un técnico no puede forzar la sección 'laboratorio' porque el componente ni se monta sin ser admin", async () => {
    // Regresión de seguridad de UI: el gating no es solo visual (ocultar el
    // botón) — `ConfiguracionPage` también condiciona el render de cada
    // sección a `esAdmin`, así que aunque el estado `seccion` cambiara por
    // otra vía, `LaboratorioSection` nunca se monta para un no-admin.
    await renderConfiguracion(["tecnico"]);

    expect(screen.queryByDisplayValue("Laboratorio de Salud Pública")).not.toBeInTheDocument();
  });
});
