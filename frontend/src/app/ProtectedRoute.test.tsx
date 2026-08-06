import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/features/auth/hooks/AuthProvider";
import type { Usuario } from "@/features/auth/types";

import { ProtectedRoute } from "./ProtectedRoute";

vi.mock("@/features/auth/api/authApi", () => ({
  obtenerUsuarioActual: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
}));

function usuarioBase(debeCambiarPassword: boolean): Usuario {
  return {
    id: "u-1",
    nombre_completo: "Ana Pérez",
    correo: "ana@lsp.gov.co",
    roles: ["tecnico"],
    debe_cambiar_password: debeCambiarPassword,
    foto_url: null,
    foto_object_key: null,
  };
}

async function renderEnRuta(debeCambiarPassword: boolean, rutaInicial: string) {
  const { obtenerUsuarioActual } = await import("@/features/auth/api/authApi");
  vi.mocked(obtenerUsuarioActual).mockResolvedValue(usuarioBase(debeCambiarPassword));

  render(
    <MemoryRouter initialEntries={[rutaInicial]}>
      <AuthProvider>
        <Routes>
          <Route path="/cambiar-password" element={<div>Página de cambio obligatorio</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Contenido protegido del dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute — RF-USR-04", () => {
  it("redirige a /cambiar-password cuando el usuario tiene una contraseña pendiente", async () => {
    await renderEnRuta(true, "/dashboard");

    expect(await screen.findByText("Página de cambio obligatorio")).toBeInTheDocument();
    expect(screen.queryByText("Contenido protegido del dashboard")).not.toBeInTheDocument();
  });

  it("no redirige y muestra el contenido normal cuando la contraseña ya fue cambiada", async () => {
    await renderEnRuta(false, "/dashboard");

    expect(await screen.findByText("Contenido protegido del dashboard")).toBeInTheDocument();
  });

  it("no entra en bucle de redirección estando ya en /cambiar-password", async () => {
    await renderEnRuta(true, "/cambiar-password");

    expect(await screen.findByText("Página de cambio obligatorio")).toBeInTheDocument();
  });
});
