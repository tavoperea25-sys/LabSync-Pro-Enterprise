"""Implementación SQLAlchemy del módulo QR."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.equipos.infrastructure.models import Equipo
from app.modules.qr.domain.entities import IncidenciaQr as IncidenciaDominio
from app.modules.qr.domain.entities import IncidenciaQrConEquipo
from app.modules.qr.domain.entities import QrToken as QrTokenDominio
from app.modules.qr.infrastructure.models import IncidenciaQr, QrToken


def _token_a_dominio(fila: QrToken) -> QrTokenDominio:
    return QrTokenDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        equipo_id=fila.equipo_id,
        token=fila.token,
        revocado=fila.revocado,
    )


class QrTokenRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID, token: str) -> QrTokenDominio:
        fila = QrToken(id=uuid.uuid4(), laboratorio_id=laboratorio_id, equipo_id=equipo_id, token=token)
        self._db.add(fila)
        self._db.flush()
        return _token_a_dominio(fila)

    def obtener_por_token(self, token: str) -> QrTokenDominio | None:
        # Sin filtro de tenant a propósito — ver docstring de la migración
        # 0004_qr.py. Esta tabla no lleva RLS.
        fila = self._db.execute(select(QrToken).where(QrToken.token == token)).scalar_one_or_none()
        return _token_a_dominio(fila) if fila else None

    def obtener_por_equipo(self, equipo_id: uuid.UUID) -> QrTokenDominio | None:
        fila = self._db.execute(
            select(QrToken).where(QrToken.equipo_id == equipo_id)
        ).scalar_one_or_none()
        return _token_a_dominio(fila) if fila else None


def _incidencia_a_dominio(fila: IncidenciaQr) -> IncidenciaDominio:
    return IncidenciaDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        equipo_id=fila.equipo_id,
        descripcion=fila.descripcion,
        contacto_nombre=fila.contacto_nombre,
        contacto_medio=fila.contacto_medio,
        estado=fila.estado,
        creado_en=fila.creado_en,
    )


class IncidenciaQrRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(
        self,
        laboratorio_id: uuid.UUID,
        equipo_id: uuid.UUID,
        descripcion: str,
        contacto_nombre: str | None,
        contacto_medio: str | None,
    ) -> IncidenciaDominio:
        fila = IncidenciaQr(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            equipo_id=equipo_id,
            descripcion=descripcion,
            contacto_nombre=contacto_nombre,
            contacto_medio=contacto_medio,
            estado="pendiente",
        )
        self._db.add(fila)
        self._db.flush()
        return _incidencia_a_dominio(fila)

    def listar_con_equipo(self, laboratorio_id: uuid.UUID) -> list[IncidenciaQrConEquipo]:
        """RF-QR-03 — orden más reciente primero, igual que el listado de
        Mantenimientos (`MantenimientoRepositorySQLAlchemy.listar_todos`)
        donde esta lista se muestra."""
        stmt = (
            select(IncidenciaQr, Equipo.codigo_interno, Equipo.nombre)
            .join(Equipo, Equipo.id == IncidenciaQr.equipo_id)
            .where(IncidenciaQr.laboratorio_id == laboratorio_id)
            .order_by(IncidenciaQr.creado_en.desc())
        )
        filas = self._db.execute(stmt).all()
        return [
            IncidenciaQrConEquipo(
                id=incidencia.id,
                equipo_id=incidencia.equipo_id,
                equipo_codigo_interno=codigo_interno,
                equipo_nombre=nombre,
                descripcion=incidencia.descripcion,
                contacto_nombre=incidencia.contacto_nombre,
                contacto_medio=incidencia.contacto_medio,
                estado=incidencia.estado,
                creado_en=incidencia.creado_en,
            )
            for incidencia, codigo_interno, nombre in filas
        ]

    def obtener_por_id(self, incidencia_id: uuid.UUID) -> IncidenciaDominio | None:
        fila = self._db.get(IncidenciaQr, incidencia_id)
        return _incidencia_a_dominio(fila) if fila else None

    def actualizar_estado(self, incidencia_id: uuid.UUID, nuevo_estado: str) -> IncidenciaDominio:
        fila = self._db.get(IncidenciaQr, incidencia_id)
        assert fila is not None  # el servicio ya validó existencia vía obtener_por_id
        fila.estado = nuevo_estado
        self._db.flush()
        return _incidencia_a_dominio(fila)
