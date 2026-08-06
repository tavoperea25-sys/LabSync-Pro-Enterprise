"""Implementación SQLAlchemy del repositorio de Adjuntos."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.adjuntos.domain.entities import Adjunto as AdjuntoDominio
from app.modules.adjuntos.infrastructure.models import Adjunto


def _a_dominio(fila: Adjunto) -> AdjuntoDominio:
    return AdjuntoDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        entidad_tipo=fila.entidad_tipo,
        entidad_id=fila.entidad_id,
        object_key=fila.object_key,
        nombre_archivo=fila.nombre_archivo,
        tamano_bytes=fila.tamano_bytes,
        tipo_mime=fila.tipo_mime,
        subido_por_id=fila.subido_por_id,
        creado_en=fila.creado_en,
    )


class AdjuntoRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, adjunto: AdjuntoDominio) -> AdjuntoDominio:
        fila = Adjunto(
            id=adjunto.id,
            laboratorio_id=adjunto.laboratorio_id,
            entidad_tipo=adjunto.entidad_tipo,
            entidad_id=adjunto.entidad_id,
            object_key=adjunto.object_key,
            nombre_archivo=adjunto.nombre_archivo,
            tamano_bytes=adjunto.tamano_bytes,
            tipo_mime=adjunto.tipo_mime,
            subido_por_id=adjunto.subido_por_id,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def obtener_por_id(self, adjunto_id: uuid.UUID) -> AdjuntoDominio | None:
        fila = self._db.get(Adjunto, adjunto_id)
        return _a_dominio(fila) if fila else None

    def listar_por_entidad(self, entidad_tipo: str, entidad_id: uuid.UUID) -> list[AdjuntoDominio]:
        stmt = (
            select(Adjunto)
            .where(Adjunto.entidad_tipo == entidad_tipo, Adjunto.entidad_id == entidad_id)
            .order_by(Adjunto.creado_en)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]
