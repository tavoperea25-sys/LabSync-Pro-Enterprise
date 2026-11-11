import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";

vi.mock("@/features/auth/api/authApi", () => ({
  obtenerUsuarioActual: vi.fn().mockRejectedValue(new Error("sin sesión")),
}));

describe("App", () => {
  it("sin sesión, redirige al login al arrancar (migración al data router sin cambio de comportamiento)", async () => {
    render(<App />);

    expect(await screen.findByRole("heading", { name: /inicia sesión/i })).toBeInTheDocument();
  });
});
