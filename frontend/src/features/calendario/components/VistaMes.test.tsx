import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { EventoCalendario } from "../types";
import { VistaMes } from "./VistaMes";

function evento(overrides: Partial<EventoCalendario> & Pick<EventoCalendario, "id" | "fecha" | "titulo">): EventoCalendario {
  return {
    tipo: "institucional",
    descripcion: null,
    origen_tipo: null,
    origen_id: null,
    editable: true,
    ...overrides,
  };
}

function renderVistaMes(fechaDeReferencia: Date, eventos: EventoCalendario[]) {
  return render(
    <MemoryRouter>
      <VistaMes
        fechaDeReferencia={fechaDeReferencia}
        eventos={eventos}
        onEditar={vi.fn()}
        onCrearEnFecha={vi.fn()}
      />
    </MemoryRouter>,
  );
}

describe("VistaMes (M10 — filtrado de eventos memoizado)", () => {
  it("render inicial: muestra los eventos del mes en la celda del día correcto", () => {
    const junio2026 = new Date(2026, 5, 15);
    const eventoJunio = evento({
      id: "e1",
      titulo: "Auditoría interna",
      fecha: new Date(2026, 5, 10, 9, 0).toISOString(),
    });

    renderVistaMes(junio2026, [eventoJunio]);

    expect(screen.getByText(/auditoría interna/i)).toBeInTheDocument();
  });

  it("cambio de mes: los eventos del mes anterior desaparecen y aparecen los del nuevo mes", () => {
    const junio2026 = new Date(2026, 5, 15);
    const eventoJunio = evento({
      id: "e-junio",
      titulo: "Capacitación de junio",
      fecha: new Date(2026, 5, 10, 9, 0).toISOString(),
    });

    const { rerender } = render(
      <MemoryRouter>
        <VistaMes
          fechaDeReferencia={junio2026}
          eventos={[eventoJunio]}
          onEditar={vi.fn()}
          onCrearEnFecha={vi.fn()}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText(/capacitación de junio/i)).toBeInTheDocument();

    // Al navegar de mes, CalendarioPage vuelve a consultar el rango y pasa un
    // arreglo de `eventos` nuevo (scopeado al mes visible) — se simula igual
    // aquí, en vez de reutilizar el mismo arreglo con un mes distinto.
    const julio2026 = new Date(2026, 6, 15);
    const eventoJulio = evento({
      id: "e-julio",
      titulo: "Capacitación de julio",
      fecha: new Date(2026, 6, 10, 9, 0).toISOString(),
    });

    rerender(
      <MemoryRouter>
        <VistaMes
          fechaDeReferencia={julio2026}
          eventos={[eventoJulio]}
          onEditar={vi.fn()}
          onCrearEnFecha={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.queryByText(/capacitación de junio/i)).not.toBeInTheDocument();
    expect(screen.getByText(/capacitación de julio/i)).toBeInTheDocument();
  });

  it("cambio de filtros: al reducir el arreglo de eventos recibido, solo desaparecen los eventos filtrados", () => {
    const junio2026 = new Date(2026, 5, 15);
    const eventoCalibracion = evento({
      id: "e-calibracion",
      tipo: "calibracion",
      titulo: "Calibración de balanza",
      fecha: new Date(2026, 5, 10, 9, 0).toISOString(),
    });
    const eventoMantenimiento = evento({
      id: "e-mantenimiento",
      tipo: "mantenimiento",
      titulo: "Mantenimiento de centrífuga",
      fecha: new Date(2026, 5, 10, 11, 0).toISOString(),
    });

    const { rerender } = renderVistaMes(junio2026, [eventoCalibracion, eventoMantenimiento]);
    expect(screen.getByText(/calibración de balanza/i)).toBeInTheDocument();
    expect(screen.getByText(/mantenimiento de centrífuga/i)).toBeInTheDocument();

    // Simula el filtro "Tipo: Calibración" aplicado en CalendarioPage — la
    // consulta vuelve a ejecutarse y `eventos` llega ya reducido.
    rerender(
      <MemoryRouter>
        <VistaMes
          fechaDeReferencia={junio2026}
          eventos={[eventoCalibracion]}
          onEditar={vi.fn()}
          onCrearEnFecha={vi.fn()}
        />
      </MemoryRouter>,
    );

    expect(screen.getByText(/calibración de balanza/i)).toBeInTheDocument();
    expect(screen.queryByText(/mantenimiento de centrífuga/i)).not.toBeInTheDocument();
  });

  it("un día con más eventos que el máximo visible sigue mostrando el resumen '+N más'", () => {
    const junio2026 = new Date(2026, 5, 15);
    const eventosDelDia = ["Uno", "Dos", "Tres", "Cuatro"].map((titulo, i) =>
      evento({
        id: `e${i}`,
        titulo,
        fecha: new Date(2026, 5, 10, 8 + i, 0).toISOString(),
      }),
    );

    renderVistaMes(junio2026, eventosDelDia);

    expect(screen.getByText(/uno/i)).toBeInTheDocument();
    expect(screen.getByText(/dos/i)).toBeInTheDocument();
    expect(screen.getByText(/tres/i)).toBeInTheDocument();
    expect(screen.queryByText(/cuatro/i)).not.toBeInTheDocument();
    expect(screen.getByText("+1 más")).toBeInTheDocument();
  });
});
