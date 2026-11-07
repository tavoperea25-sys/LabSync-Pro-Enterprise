import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import { QrPublicPage } from "./QrPublicPage";

const EQUIPO_DE_PRUEBA = {
  id: "eq-1",
  codigo_interno: "EQ-001",
  nombre: "Centrífuga de prueba",
  estado_operativo: "operativo" as const,
  dado_de_baja: false,
  marca: "",
  modelo: "",
  foto_url: null,
};

vi.mock("../hooks/useQrPublico", () => ({
  useEquipoPorQr: vi.fn(() => ({ data: EQUIPO_DE_PRUEBA, isLoading: false, isError: false })),
  useReportarIncidencia: vi.fn(() => ({ mutateAsync: vi.fn(), isSuccess: false })),
}));

function renderPagina() {
  return render(
    <MemoryRouter initialEntries={["/qr/token-de-prueba"]}>
      <QrPublicPage />
    </MemoryRouter>,
  );
}

describe("QrPublicPage", () => {
  it("muestra el mensaje en español de zod cuando la descripción de la incidencia está vacía", async () => {
    renderPagina();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: /enviar reporte/i }));

    expect(await screen.findByText("Describe brevemente la incidencia.")).toBeInTheDocument();
  });
});
