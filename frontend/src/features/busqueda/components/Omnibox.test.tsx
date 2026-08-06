import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ResultadoBusqueda } from "../types";
import { Omnibox } from "./Omnibox";

const navegarMock = vi.fn();
vi.mock("react-router-dom", async (importarOriginal) => {
  const real = await importarOriginal<typeof import("react-router-dom")>();
  return { ...real, useNavigate: () => navegarMock };
});

vi.mock("../api/busquedaApi", () => ({
  buscar: vi.fn(),
}));

const RESULTADOS: ResultadoBusqueda[] = [
  { tipo: "equipo", id: "eq-1", titulo: "Balanza analítica", subtitulo: "Metrología", ruta: "/equipos/eq-1" },
  { tipo: "documento", id: "doc-1", titulo: "Manual de calidad", subtitulo: null, ruta: "/documentos/doc-1" },
];

function renderOmnibox() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Omnibox />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Omnibox", () => {
  afterEach(() => {
    navegarMock.mockClear();
  });

  it("el botón disparador es accesible por nombre incluso sin texto visible completo", () => {
    renderOmnibox();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeInTheDocument();
  });

  it("se abre con Ctrl+K y se cierra con Escape", async () => {
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.keyboard("{Control>}k{/Control}");
    expect(await screen.findByRole("dialog", { name: /búsqueda global/i })).toBeInTheDocument();

    await usuario.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("también se abre haciendo clic en el botón de búsqueda", async () => {
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("pide un mínimo de 2 caracteres antes de buscar", async () => {
    const { buscar } = await import("../api/busquedaApi");
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    await usuario.type(campo, "a");

    expect(await screen.findByText(/escribe al menos 2 caracteres/i)).toBeInTheDocument();
    expect(buscar).not.toHaveBeenCalled();
  });

  it("agrupa los resultados por tipo y navega al seleccionar uno con clic", async () => {
    const { buscar } = await import("../api/busquedaApi");
    vi.mocked(buscar).mockResolvedValue(RESULTADOS);
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    await usuario.type(campo, "balanza");

    expect(await screen.findByText("Equipos")).toBeInTheDocument();
    expect(screen.getByText("Documentos")).toBeInTheDocument();

    await usuario.click(screen.getByText("Balanza analítica"));
    expect(navegarMock).toHaveBeenCalledWith("/equipos/eq-1");
    // Al navegar, el diálogo se cierra.
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("permite navegar los resultados con flechas y confirmar con Enter", async () => {
    const { buscar } = await import("../api/busquedaApi");
    vi.mocked(buscar).mockResolvedValue(RESULTADOS);
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    await usuario.type(campo, "manual");
    await screen.findByText("Balanza analítica");

    // El primer resultado ("equipo") empieza activo por defecto; una flecha
    // abajo mueve la selección al segundo ("documento").
    await usuario.keyboard("{ArrowDown}");
    await usuario.keyboard("{Enter}");

    expect(navegarMock).toHaveBeenCalledWith("/documentos/doc-1");
  });

  it("muestra 'Sin resultados' cuando la búsqueda no encuentra nada", async () => {
    const { buscar } = await import("../api/busquedaApi");
    vi.mocked(buscar).mockResolvedValue([]);
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    await usuario.type(campo, "inexistente");

    expect(await screen.findByText(/sin resultados/i)).toBeInTheDocument();
  });

  it("el botón disparador expone aria-haspopup/aria-expanded/aria-controls hacia el diálogo", async () => {
    renderOmnibox();
    const usuario = userEvent.setup();
    const boton = screen.getByRole("button", { name: "Buscar" });

    expect(boton).toHaveAttribute("aria-haspopup", "dialog");
    expect(boton).toHaveAttribute("aria-expanded", "false");

    await usuario.click(boton);
    const dialogo = await screen.findByRole("dialog");

    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(boton).toHaveAttribute("aria-controls", dialogo.id);
  });

  it("el foco entra al campo de búsqueda al abrir y vuelve al botón disparador al cerrar con Escape", async () => {
    renderOmnibox();
    const usuario = userEvent.setup();
    const boton = screen.getByRole("button", { name: "Buscar" });

    await usuario.click(boton);
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    expect(campo).toHaveFocus();

    await usuario.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(boton).toHaveFocus();
  });

  it("devuelve el foco al botón disparador al cerrar haciendo clic fuera del diálogo", async () => {
    renderOmnibox();
    const usuario = userEvent.setup();
    const boton = screen.getByRole("button", { name: "Buscar" });

    await usuario.click(boton);
    await screen.findByRole("dialog");
    await usuario.click(screen.getByRole("button", { name: "Cerrar búsqueda" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(boton).toHaveFocus();
  });

  it("devuelve el foco al botón disparador al seleccionar un resultado y navegar", async () => {
    const { buscar } = await import("../api/busquedaApi");
    vi.mocked(buscar).mockResolvedValue(RESULTADOS);
    renderOmnibox();
    const usuario = userEvent.setup();
    const boton = screen.getByRole("button", { name: "Buscar" });

    await usuario.click(boton);
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    await usuario.type(campo, "balanza");
    await usuario.click(await screen.findByText("Balanza analítica"));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(boton).toHaveFocus();
  });

  it("Tab en el último elemento del diálogo vuelve a atrapar el foco en el primero", async () => {
    const { buscar } = await import("../api/busquedaApi");
    vi.mocked(buscar).mockResolvedValue(RESULTADOS);
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    await usuario.type(campo, "balanza");
    const primerResultado = await screen.findByText("Balanza analítica");
    const segundoResultado = screen.getByText("Manual de calidad");

    // input -> primer resultado -> segundo (último) resultado
    await usuario.tab();
    expect(primerResultado.closest("button")).toHaveFocus();
    await usuario.tab();
    expect(segundoResultado.closest("button")).toHaveFocus();

    // Tab en el último elemento envuelve de vuelta al campo de búsqueda,
    // nunca escapa hacia el botón disparador ni el resto de la página.
    await usuario.tab();
    expect(campo).toHaveFocus();
  });

  it("Shift+Tab en el campo de búsqueda (primer elemento) atrapa el foco en el último", async () => {
    const { buscar } = await import("../api/busquedaApi");
    vi.mocked(buscar).mockResolvedValue(RESULTADOS);
    renderOmnibox();
    const usuario = userEvent.setup();

    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    const campo = await screen.findByRole("combobox", { name: "Buscar" });
    await usuario.type(campo, "balanza");
    const segundoResultado = await screen.findByText("Manual de calidad");
    campo.focus();

    await usuario.tab({ shift: true });
    expect(segundoResultado.closest("button")).toHaveFocus();
  });
});
