import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ProtectedRoute } from "@/app/ProtectedRoute";
import { AuthProvider } from "@/features/auth/hooks/AuthProvider";
import { ApiError } from "@/lib/httpClient";

import { PerfilSection } from "./PerfilSection";

vi.mock("@/features/auth/api/authApi", () => ({
  obtenerUsuarioActual: vi.fn().mockResolvedValue({
    id: "u-1",
    nombre_completo: "Ana Pérez",
    correo: "ana@lsp.gov.co",
    roles: ["tecnico"],
    debe_cambiar_password: false,
    foto_url: null,
    foto_object_key: null,
  }),
  login: vi.fn(),
  logout: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("../api/configuracionApi", () => ({
  actualizarPerfilPropio: vi.fn(),
  cambiarPasswordPropio: vi.fn(),
}));

function renderPerfilSection() {
  // `PerfilSection` precarga sus campos con `useState(usuario?.nombre_completo
  // ?? "")` — un valor inicial que solo se lee una vez, en el primer render.
  // En producción eso funciona porque `ProtectedRoute` nunca monta la página
  // hasta que `cargandoSesionInicial` es `false` (usuario ya resuelto); si el
  // test montara `PerfilSection` directo bajo `AuthProvider`, el usuario aún
  // sería `null` en ese primer render y los campos quedarían vacíos para
  // siempre. Se replica el mismo wrapper que usa la app real.
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/configuracion"]}>
        <AuthProvider>
          <ProtectedRoute>
            <PerfilSection />
          </ProtectedRoute>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PerfilSection", () => {
  it("precarga nombre y correo del usuario en sesión", async () => {
    renderPerfilSection();
    expect(await screen.findByDisplayValue("Ana Pérez")).toBeInTheDocument();
    expect(screen.getByDisplayValue("ana@lsp.gov.co")).toBeInTheDocument();
  });

  it("no permite guardar el perfil con nombre o correo vacíos", async () => {
    renderPerfilSection();
    const usuario = userEvent.setup();
    const { actualizarPerfilPropio } = await import("../api/configuracionApi");

    await screen.findByDisplayValue("Ana Pérez");
    await usuario.clear(screen.getByLabelText(/nombre completo/i));
    await usuario.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/nombre y correo son obligatorios/i);
    expect(actualizarPerfilPropio).not.toHaveBeenCalled();
  });

  it("guarda el perfil y muestra confirmación de éxito", async () => {
    const { actualizarPerfilPropio } = await import("../api/configuracionApi");
    vi.mocked(actualizarPerfilPropio).mockResolvedValue({
      id: "u-1",
      nombre_completo: "Ana P. Gómez",
      correo: "ana@lsp.gov.co",
      roles: ["tecnico"],
      debe_cambiar_password: false,
      foto_url: null,
      foto_object_key: null,
    });

    renderPerfilSection();
    const usuario = userEvent.setup();

    const campoNombre = await screen.findByLabelText(/nombre completo/i);
    await usuario.clear(campoNombre);
    await usuario.type(campoNombre, "Ana P. Gómez");
    await usuario.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/perfil actualizado/i);
    expect(actualizarPerfilPropio).toHaveBeenCalledWith({
      nombre_completo: "Ana P. Gómez",
      correo: "ana@lsp.gov.co",
      foto_object_key: null,
    });
  });

  it("reenvía el object_key de la foto actual al guardar otro campo, sin borrarla", async () => {
    const { obtenerUsuarioActual } = await import("@/features/auth/api/authApi");
    vi.mocked(obtenerUsuarioActual).mockResolvedValue({
      id: "u-1",
      nombre_completo: "Ana Pérez",
      correo: "ana@lsp.gov.co",
      roles: ["tecnico"],
      debe_cambiar_password: false,
      foto_url: "https://minio.local/fotos-usuarios/existente.jpg?firma=abc",
      foto_object_key: "existente.jpg",
    });
    const { actualizarPerfilPropio } = await import("../api/configuracionApi");
    vi.mocked(actualizarPerfilPropio).mockResolvedValue({
      id: "u-1",
      nombre_completo: "Ana P. Gómez",
      correo: "ana@lsp.gov.co",
      roles: ["tecnico"],
      debe_cambiar_password: false,
      foto_url: "https://minio.local/fotos-usuarios/existente.jpg?firma=def",
      foto_object_key: "existente.jpg",
    });

    renderPerfilSection();
    const usuario = userEvent.setup();

    const campoNombre = await screen.findByLabelText(/nombre completo/i);
    await usuario.clear(campoNombre);
    await usuario.type(campoNombre, "Ana P. Gómez");
    await usuario.click(screen.getByRole("button", { name: /guardar cambios/i }));

    await screen.findByRole("status");
    expect(actualizarPerfilPropio).toHaveBeenCalledWith({
      nombre_completo: "Ana P. Gómez",
      correo: "ana@lsp.gov.co",
      foto_object_key: "existente.jpg",
    });
  });

  it("muestra el mensaje de error de la API cuando falla la actualización del perfil", async () => {
    const { actualizarPerfilPropio } = await import("../api/configuracionApi");
    vi.mocked(actualizarPerfilPropio).mockRejectedValue(
      new ApiError("correo_en_uso", "Ese correo ya está en uso.", 409),
    );

    renderPerfilSection();
    const usuario = userEvent.setup();

    await screen.findByDisplayValue("Ana Pérez");
    await usuario.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/ese correo ya está en uso/i);
  });

  it("no permite cambiar la contraseña si falta algún campo", async () => {
    renderPerfilSection();
    const usuario = userEvent.setup();
    const { cambiarPasswordPropio } = await import("../api/configuracionApi");

    await screen.findByDisplayValue("Ana Pérez");
    await usuario.click(screen.getByRole("button", { name: /cambiar contraseña/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/completa ambos campos de contraseña/i);
    expect(cambiarPasswordPropio).not.toHaveBeenCalled();
  });

  it("al cambiar la contraseña con éxito, cierra la sesión y redirige a login", async () => {
    const { cambiarPasswordPropio } = await import("../api/configuracionApi");
    const { logout } = await import("@/features/auth/api/authApi");
    vi.mocked(cambiarPasswordPropio).mockResolvedValue(undefined);

    renderPerfilSection();
    const usuario = userEvent.setup();

    await screen.findByDisplayValue("Ana Pérez");
    await usuario.type(screen.getByLabelText(/contraseña actual/i), "ClaveVieja123!");
    await usuario.type(screen.getByLabelText(/contraseña nueva/i), "ClaveNueva456!");
    await usuario.click(screen.getByRole("button", { name: /cambiar contraseña/i }));

    await waitFor(() => expect(logout).toHaveBeenCalled());
    expect(cambiarPasswordPropio).toHaveBeenCalledWith({
      password_actual: "ClaveVieja123!",
      password_nueva: "ClaveNueva456!",
    });
  });

  it("muestra los motivos de rechazo de la política de contraseña cuando la API los devuelve", async () => {
    const { cambiarPasswordPropio } = await import("../api/configuracionApi");
    vi.mocked(cambiarPasswordPropio).mockRejectedValue(
      new ApiError("password_invalida", "Contraseña inválida.", 422, {
        motivos: ["Debe tener al menos 12 caracteres.", "Debe incluir un símbolo."],
      }),
    );

    renderPerfilSection();
    const usuario = userEvent.setup();

    await screen.findByDisplayValue("Ana Pérez");
    await usuario.type(screen.getByLabelText(/contraseña actual/i), "ClaveVieja123!");
    await usuario.type(screen.getByLabelText(/contraseña nueva/i), "corta");
    await usuario.click(screen.getByRole("button", { name: /cambiar contraseña/i }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(/al menos 12 caracteres/i);
    expect(alerta).toHaveTextContent(/incluir un símbolo/i);
  });
});
