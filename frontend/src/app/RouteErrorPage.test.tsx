import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RouteErrorPage } from "./RouteErrorPage";

describe("RouteErrorPage", () => {
  it("muestra el mensaje en español, nunca el detalle técnico del error", () => {
    render(<RouteErrorPage />);

    expect(screen.getByText("Ocurrió un error inesperado")).toBeInTheDocument();
    expect(screen.queryByText(/error:|stack|TypeError|undefined is not/i)).not.toBeInTheDocument();
  });

  it("el botón recarga la página", async () => {
    const recargar = vi.fn();
    vi.stubGlobal("location", { ...window.location, reload: recargar });
    const usuario = userEvent.setup();

    render(<RouteErrorPage />);
    await usuario.click(screen.getByRole("button", { name: /recargar la página/i }));

    expect(recargar).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });
});
