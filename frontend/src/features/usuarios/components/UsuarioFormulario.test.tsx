import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/httpClient";

import { UsuarioFormulario } from "./UsuarioFormulario";

vi.mock("../hooks/useUsuarios", () => ({
  useRoles: vi.fn(() => ({
    data: [
      { id: "rol-tecnico", nombre: "tecnico", es_sistema: true },
      { id: "rol-calidad", nombre: "calidad", es_sistema: true },
    ],
  })),
}));

function renderFormulario(onGuardar: (datos: unknown) => Promise<void>) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <UsuarioFormulario guardando={false} onGuardar={onGuardar} onCancelar={vi.fn()} />
    </QueryClientProvider>,
  );
}

describe("UsuarioFormulario", () => {
  it("muestra las etiquetas de rol traducidas para cada rol disponible", () => {
    renderFormulario(vi.fn());
    expect(screen.getByLabelText("Técnico")).toBeInTheDocument();
    expect(screen.getByLabelText("Calidad")).toBeInTheDocument();
  });

  it("no permite crear el usuario si falta nombre, correo o contraseña", async () => {
    const onGuardar = vi.fn();
    renderFormulario(onGuardar);
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: /crear usuario/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /nombre, correo y contraseña son obligatorios/i,
    );
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("exige al menos un rol aunque los demás campos estén completos", async () => {
    const onGuardar = vi.fn();
    renderFormulario(onGuardar);
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/nombre completo/i), "Carlos Ruiz");
    await usuario.type(screen.getByLabelText(/correo/i), "carlos@lsp.gov.co");
    await usuario.type(screen.getByLabelText(/contraseña temporal/i), "Temporal123!");
    await usuario.click(screen.getByRole("button", { name: /crear usuario/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/selecciona al menos un rol/i);
    expect(onGuardar).not.toHaveBeenCalled();
  });

  it("envía los datos con los roles seleccionados cuando el formulario es válido", async () => {
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    renderFormulario(onGuardar);
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/nombre completo/i), "Carlos Ruiz");
    await usuario.type(screen.getByLabelText(/correo/i), "carlos@lsp.gov.co");
    await usuario.type(screen.getByLabelText(/contraseña temporal/i), "Temporal123!");
    await usuario.click(screen.getByLabelText("Técnico"));
    await usuario.click(screen.getByLabelText("Calidad"));
    await usuario.click(screen.getByRole("button", { name: /crear usuario/i }));

    expect(onGuardar).toHaveBeenCalledWith({
      nombre_completo: "Carlos Ruiz",
      correo: "carlos@lsp.gov.co",
      password: "Temporal123!",
      rol_ids: ["rol-tecnico", "rol-calidad"],
    });
  });

  it("des-selecciona un rol si se hace clic de nuevo sobre su checkbox", async () => {
    const onGuardar = vi.fn().mockResolvedValue(undefined);
    renderFormulario(onGuardar);
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/nombre completo/i), "Carlos Ruiz");
    await usuario.type(screen.getByLabelText(/correo/i), "carlos@lsp.gov.co");
    await usuario.type(screen.getByLabelText(/contraseña temporal/i), "Temporal123!");
    await usuario.click(screen.getByLabelText("Técnico"));
    await usuario.click(screen.getByLabelText("Calidad"));
    await usuario.click(screen.getByLabelText("Técnico")); // deselecciona
    await usuario.click(screen.getByRole("button", { name: /crear usuario/i }));

    expect(onGuardar).toHaveBeenCalledWith(expect.objectContaining({ rol_ids: ["rol-calidad"] }));
  });

  it("muestra el mensaje de error de la API cuando falla la creación", async () => {
    const onGuardar = vi.fn().mockRejectedValue(new ApiError("correo_en_uso", "Ese correo ya está en uso.", 409));
    renderFormulario(onGuardar);
    const usuario = userEvent.setup();

    await usuario.type(screen.getByLabelText(/nombre completo/i), "Carlos Ruiz");
    await usuario.type(screen.getByLabelText(/correo/i), "carlos@lsp.gov.co");
    await usuario.type(screen.getByLabelText(/contraseña temporal/i), "Temporal123!");
    await usuario.click(screen.getByLabelText("Técnico"));
    await usuario.click(screen.getByRole("button", { name: /crear usuario/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/ese correo ya está en uso/i);
  });
});
