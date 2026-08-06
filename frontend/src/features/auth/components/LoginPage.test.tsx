import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/features/auth/hooks/AuthProvider";

import { LoginPage } from "./LoginPage";

vi.mock("@/features/auth/api/authApi", () => ({
  obtenerUsuarioActual: vi.fn().mockRejectedValue(new Error("sin sesión")),
  login: vi.fn(),
  logout: vi.fn(),
}));

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  it("muestra errores de validación cuando el formulario está vacío", async () => {
    renderLoginPage();
    const usuario = userEvent.setup();

    await waitFor(() => screen.getByRole("button", { name: /iniciar sesión/i }));
    await usuario.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText(/ingresa el identificador de tu laboratorio/i)).toBeInTheDocument();
    expect(await screen.findByText(/ingresa un correo válido/i)).toBeInTheDocument();
  });

  it("permite alternar la visibilidad de la contraseña", async () => {
    renderLoginPage();
    const usuario = userEvent.setup();

    // `getByLabelText` también matchea el botón de mostrar/ocultar (tiene
    // `aria-label="Mostrar contraseña"`) — se restringe a un <input> real.
    await waitFor(() => screen.getByLabelText(/contraseña/i, { selector: "input" }));
    const campoPassword = screen.getByLabelText(/contraseña/i, { selector: "input" }) as HTMLInputElement;
    expect(campoPassword.type).toBe("password");

    await usuario.click(screen.getByRole("button", { name: /mostrar contraseña/i }));
    expect(campoPassword.type).toBe("text");
  });
});
