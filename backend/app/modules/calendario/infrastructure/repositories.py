"""Implementación SQLAlchemy del repositorio de Calendario."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.calendario.domain.entities import EventoCalendario as EventoDominio
from app.modules.calendario.domain.ports import FiltrosEventoCalendario
from app.modules.calendario.infrastructure.models import EventoCalendario


def _a_dominio(fila: EventoCalendario) -> EventoDominio:
    return EventoDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        tipo=fila.tipo,
        titulo=fila.titulo,
        descripcion=fila.descripcion,
        fecha=fila.fecha,
        origen_tipo=fila.origen_tipo,
        origen_id=fila.origen_id,
        creado_por_id=fila.creado_por_id,
        creado_en=fila.creado_en,
        actualizado_en=fila.actualizado_en,
    )


class EventoCalendarioRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, evento: EventoDominio) -> EventoDominio:
        fila = EventoCalendario(
            id=evento.id,
            laboratorio_id=evento.laboratorio_id,
            tipo=evento.tipo,
            titulo=evento.titulo,
            descripcion=evento.descripcion,
            fecha=evento.fecha,
            origen_tipo=evento.origen_tipo,
            origen_id=evento.origen_id,
            creado_por_id=evento.creado_por_id,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def obtener_por_id(self, evento_id: uuid.UUID) -> EventoDominio | None:
        fila = self._db.get(EventoCalendario, evento_id)
        return _a_dominio(fila) if fila else None

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosEventoCalendario) -> list[EventoDominio]:
        stmt = select(EventoCalendario).where(
            EventoCalendario.fecha >= filtros.desde, EventoCalendario.fecha <= filtros.hasta
        )
        if filtros.tipo is not None:
            stmt = stmt.where(EventoCalendario.tipo == filtros.tipo)
        stmt = stmt.order_by(EventoCalendario.fecha)
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def actualizar(self, evento: EventoDominio) -> EventoDominio:
        fila = self._db.get(EventoCalendario, evento.id)
        assert fila is not None
        fila.titulo = evento.titulo
        fila.descripcion = evento.descripcion
        fila.fecha = evento.fecha
        self._db.flush()
        return _a_dominio(fila)

    def eliminar(self, evento_id: uuid.UUID) -> None:
        fila = self._db.get(EventoCalendario, evento_id)
        if fila is not None:
            self._db.delete(fila)
            self._db.flush()
