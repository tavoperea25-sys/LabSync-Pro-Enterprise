"""Puertos del módulo Calendario — ver docs/13-arquitectura.md sección 2."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.calendario.domain.entities import EventoCalendario


@dataclass
class FiltrosEventoCalendario:
    desde: datetime
    hasta: datetime
    tipo: str | None = None


class EventoCalendarioRepository(Protocol):
    def crear(self, evento: EventoCalendario) -> EventoCalendario: ...

    def obtener_por_id(self, evento_id: uuid.UUID) -> EventoCalendario | None: ...

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosEventoCalendario) -> list[EventoCalendario]:
        """Solo eventos manuales (persistidos) — RF-CAL2-03."""
        ...

    def actualizar(self, evento: EventoCalendario) -> EventoCalendario: ...

    def eliminar(self, evento_id: uuid.UUID) -> None: ...
