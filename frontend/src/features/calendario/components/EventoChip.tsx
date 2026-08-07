import { useNavigate } from "react-router";

import { COLOR_POR_TIPO, ETIQUETAS_TIPO_EVENTO, type EventoCalendario } from "../types";

function formatearHora(iso: string): string {
  return new Date(iso).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
}

export function EventoChip({
  evento,
  onEditar,
}: {
  evento: EventoCalendario;
  onEditar?: (evento: EventoCalendario) => void;
}) {
  const navigate = useNavigate();
  const color = COLOR_POR_TIPO[evento.tipo];

  function alHacerClic() {
    if (evento.editable && onEditar) {
      onEditar(evento);
    } else if (evento.origen_id && (evento.origen_tipo === "equipo" || evento.origen_tipo === "documento")) {
      navigate(evento.origen_tipo === "equipo" ? `/equipos/${evento.origen_id}` : `/documentos/${evento.origen_id}`);
    }
  }

  return (
    <button
      type="button"
      onClick={alHacerClic}
      title={`${ETIQUETAS_TIPO_EVENTO[evento.tipo]}: ${evento.titulo}`}
      className="flex w-full items-center gap-1.5 truncate rounded px-1.5 py-0.5 text-left text-xs font-medium text-white transition-opacity hover:opacity-90"
      style={{ backgroundColor: color }}
    >
      <span className="truncate">
        {formatearHora(evento.fecha)} · {evento.titulo}
      </span>
    </button>
  );
}
