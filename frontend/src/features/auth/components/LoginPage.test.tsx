import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import * as authApi from "@/features/auth/api/authApi";
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

  it("muestra el mensaje en español de zod cuando el correo está vacío", async () => {
    renderLoginPage();
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/laboratorio/i), "lab-demo");
    await usuario.type(screen.getByLabelText(/contraseña/i, { selector: "input" }), "clave-cualquiera");
    await usuario.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText("Ingresa un correo válido.")).toBeInTheDocument();
  });

  it("muestra el mensaje en español de zod cuando el correo tiene formato inválido", async () => {
    renderLoginPage();
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/laboratorio/i), "lab-demo");
    await usuario.type(screen.getByLabelText(/correo/i), "esto-no-es-un-correo");
    await usuario.type(screen.getByLabelText(/contraseña/i, { selector: "input" }), "clave-cualquiera");
    await usuario.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText("Ingresa un correo válido.")).toBeInTheDocument();
  });

  it("muestra el mensaje en español de zod cuando la contraseña está vacía", async () => {
    renderLoginPage();
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/laboratorio/i), "lab-demo");
    await usuario.type(screen.getByLabelText(/correo/i), "usuario@lab-demo.dev");
    await usuario.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    expect(await screen.findByText("Por favor ingresa tu contraseña.")).toBeInTheDocument();
  });

  it("z.email() acepta un correo de dominio institucional (nombre.apellido@cesar.gov.co)", async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce({
      access_token: "token-de-prueba",
      expira_en: 900,
      usuario: {
        id: "u1",
        nombre_completo: "Nombre Apellido",
        correo: "nombre.apellido@cesar.gov.co",
        roles: ["administrador"],
        debe_cambiar_password: false,
        foto_url: null,
        foto_object_key: null,
      },
    });
    renderLoginPage();
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/laboratorio/i), "lab-demo");
    await usuario.type(screen.getByLabelText(/correo/i), "nombre.apellido@cesar.gov.co");
    await usuario.type(screen.getByLabelText(/contraseña/i, { selector: "input" }), "clave-cualquiera");
    await usuario.click(screen.getByRole("button", { name: /iniciar sesión/i }));

    await waitFor(() => expect(authApi.login).toHaveBeenCalled());
    expect(screen.queryByText("Ingresa un correo válido.")).not.toBeInTheDocument();
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
