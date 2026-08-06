import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AlertasSection } from "./AlertasSection";

vi.mock("../api/configuracionApi", () => ({
  obtenerConfiguracion: vi.fn(),
  actualizarUmbrales: vi.fn(),
  actualizarPoliticaPassword: vi.fn(),
  actualizarMapeoEstadosMantenimiento: vi.fn(),
}));

function renderAlertasSection() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <AlertasSection />
    </QueryClientProvider>,
  );
}

async function mockConfiguracion(overrides: Partial<Record<string, unknown>> = {}) {
  const { obtenerConfiguracion } = await import("../api/configuracionApi");
  vi.mocked(obtenerConfiguracion).mockResolvedValue({
    umbral_alerta_calibracion_dias: 30,
    umbral_alerta_mantenimiento_dias: 15,
    umbral_alerta_documento_dias: 30,
    dias_retencion_papelera_documentos: 30,
    politica_password: null,
    mapeo_estados_mantenimiento: null,
    ...overrides,
  });
}

describe("AlertasSection", () => {
  it("precarga los umbrales guardados", async () => {
    await mockConfiguracion({ umbral_alerta_calibracion_dias: 45 });
    renderAlertasSection();

    expect(await screen.findByLabelText(/calibraciones \(días\)/i)).toHaveValue(45);
  });

  it("rechaza umbrales en cero o negativos sin llamar a la API", async () => {
    await mockConfiguracion();
    const { actualizarUmbrales } = await import("../api/configuracionApi");
    renderAlertasSection();
    const usuario = userEvent.setup();

    const campoCalibracion = await screen.findByLabelText(/calibraciones \(días\)/i);
    await usuario.clear(campoCalibracion);
    await usuario.type(campoCalibracion, "0");
    await usuario.click(screen.getByRole("button", { name: /guardar umbrales/i }));

    expect(await screen.findByText(/número entero positivo/i)).toBeInTheDocument();
    expect(actualizarUmbrales).not.toHaveBeenCalled();
  });

  it("marca aria-invalid y asocia el mensaje de error solo al campo inválido (M9)", async () => {
    await mockConfiguracion();
    renderAlertasSection();
    const usuario = userEvent.setup();

    const campoCalibracion = await screen.findByLabelText(/calibraciones \(días\)/i);
    const campoMantenimiento = screen.getByLabelText(/mantenimientos \(días\)/i);
    // Antes de enviar, ningún campo debe exponer un estado inválido incorrecto.
    expect(campoCalibracion).toHaveAttribute("aria-invalid", "false");
    expect(campoMantenimiento).toHaveAttribute("aria-invalid", "false");

    await usuario.clear(campoCalibracion);
    await usuario.type(campoCalibracion, "0");
    await usuario.click(screen.getByRole("button", { name: /guardar umbrales/i }));

    // Solo el campo inválido queda marcado — el mensaje está asociado
    // semánticamente a él vía aria-describedby (toHaveAccessibleDescription
    // resuelve la cadena aria-describedby real, no solo el texto visible).
    expect(campoCalibracion).toHaveAttribute("aria-invalid", "true");
    expect(campoCalibracion).toHaveAccessibleDescription(/número entero positivo/i);
    expect(campoMantenimiento).toHaveAttribute("aria-invalid", "false");
    expect(campoMantenimiento).not.toHaveAccessibleDescription(/número entero positivo/i);
  });

  it("guarda umbrales válidos y muestra confirmación", async () => {
    await mockConfiguracion();
    const { actualizarUmbrales } = await import("../api/configuracionApi");
    vi.mocked(actualizarUmbrales).mockResolvedValue({
      umbral_alerta_calibracion_dias: 60,
      umbral_alerta_mantenimiento_dias: 15,
      umbral_alerta_documento_dias: 30,
      dias_retencion_papelera_documentos: 30,
      politica_password: null,
      mapeo_estados_mantenimiento: null,
    });
    renderAlertasSection();
    const usuario = userEvent.setup();

    const campoCalibracion = await screen.findByLabelText(/calibraciones \(días\)/i);
    await usuario.clear(campoCalibracion);
    await usuario.type(campoCalibracion, "60");
    await usuario.click(screen.getByRole("button", { name: /guardar umbrales/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/umbrales actualizados/i);
    expect(actualizarUmbrales).toHaveBeenCalledWith({
      umbral_alerta_calibracion_dias: 60,
      umbral_alerta_mantenimiento_dias: 15,
      umbral_alerta_documento_dias: 30,
      dias_retencion_papelera_documentos: 30,
    });
  });

  it("la política de contraseña personalizada está oculta hasta activar el checkbox", async () => {
    await mockConfiguracion();
    renderAlertasSection();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/calibraciones \(días\)/i);
    expect(screen.queryByLabelText(/longitud mínima/i)).not.toBeInTheDocument();

    await usuario.click(screen.getByLabelText(/usar una política personalizada/i));
    expect(screen.getByLabelText(/longitud mínima/i)).toBeInTheDocument();
  });

  it("precarga la política personalizada existente cuando el laboratorio ya tiene una", async () => {
    await mockConfiguracion({
      politica_password: { longitud_minima: 14, requiere_simbolo: false },
    });
    renderAlertasSection();

    expect(await screen.findByLabelText(/usar una política personalizada/i)).toBeChecked();
    expect(screen.getByLabelText(/longitud mínima/i)).toHaveValue(14);
    expect(screen.getByLabelText(/requiere símbolo/i)).not.toBeChecked();
    // Los campos no definidos por el laboratorio caen a la política por
    // defecto en vez de quedar en `undefined`/desmarcados por accidente.
    expect(screen.getByLabelText(/requiere mayúscula/i)).toBeChecked();
  });

  it("envía null como política al guardar sin personalización activada", async () => {
    await mockConfiguracion();
    const { actualizarPoliticaPassword } = await import("../api/configuracionApi");
    vi.mocked(actualizarPoliticaPassword).mockResolvedValue({
      umbral_alerta_calibracion_dias: 30,
      umbral_alerta_mantenimiento_dias: 15,
      umbral_alerta_documento_dias: 30,
      dias_retencion_papelera_documentos: 30,
      politica_password: null,
      mapeo_estados_mantenimiento: null,
    });
    renderAlertasSection();
    const usuario = userEvent.setup();

    await screen.findByLabelText(/calibraciones \(días\)/i);
    await usuario.click(screen.getByRole("button", { name: /guardar política/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/política de contraseña actualizada/i);
    expect(actualizarPoliticaPassword).toHaveBeenCalledWith(null);
  });

  it("precarga el mapeo de estados por defecto cuando el laboratorio no configuró uno", async () => {
    await mockConfiguracion();
    renderAlertasSection();

    // "Preventivo" -> "En mantenimiento" es el valor por defecto (RN-MANT-01).
    expect(await screen.findByLabelText(/preventivo/i)).toHaveValue("en_mantenimiento");
    expect(screen.getByLabelText(/^correctivo$/i)).toHaveValue("fuera_de_servicio");
  });

  it("permite cambiar el estado resultante de un tipo de mantenimiento y guardarlo", async () => {
    await mockConfiguracion();
    const { actualizarMapeoEstadosMantenimiento } = await import("../api/configuracionApi");
    vi.mocked(actualizarMapeoEstadosMantenimiento).mockResolvedValue({
      umbral_alerta_calibracion_dias: 30,
      umbral_alerta_mantenimiento_dias: 15,
      umbral_alerta_documento_dias: 30,
      dias_retencion_papelera_documentos: 30,
      politica_password: null,
      mapeo_estados_mantenimiento: { preventivo: "fuera_de_servicio" },
    });
    renderAlertasSection();
    const usuario = userEvent.setup();

    const selectPreventivo = await screen.findByLabelText(/preventivo/i);
    await usuario.selectOptions(selectPreventivo, "fuera_de_servicio");
    await usuario.click(screen.getByRole("button", { name: /guardar estados/i }));

    expect(await screen.findByRole("status")).toHaveTextContent(/configuración de estados actualizada/i);
    expect(actualizarMapeoEstadosMantenimiento).toHaveBeenCalledWith(
      expect.objectContaining({ preventivo: "fuera_de_servicio" }),
    );
  });
});
