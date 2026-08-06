"""Implementación SQLAlchemy de los repositorios de Alertas."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.alertas.domain.entities import Alerta as AlertaDominio
from app.modules.alertas.domain.entities import NotificacionPendiente as NotificacionDominio
from app.modules.alertas.domain.ports import FiltrosAlerta, PaginaAlertas
from app.modules.alertas.infrastructure.models import Alerta, NotificacionPendiente


def _a_dominio(fila: Alerta) -> AlertaDominio:
    return AlertaDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        tipo=fila.tipo,
        origen_tipo=fila.origen_tipo,
        origen_id=fila.origen_id,
        mensaje=fila.mensaje,
        estado=fila.estado,
        leida_en=fila.leida_en,
        resuelta_por_id=fila.resuelta_por_id,
        resuelta_en=fila.resuelta_en,
        creado_en=fila.creado_en,
    )


def _notificacion_a_dominio(fila: NotificacionPendiente) -> NotificacionDominio:
    return NotificacionDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        alerta_id=fila.alerta_id,
        canal=fila.canal,
        payload=fila.payload,
        estado=fila.estado,
        intentos=fila.intentos,
        procesado_en=fila.procesado_en,
        creado_en=fila.creado_en,
    )


class AlertaRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, alerta: AlertaDominio) -> AlertaDominio:
        fila = Alerta(
            id=alerta.id,
            laboratorio_id=alerta.laboratorio_id,
            tipo=alerta.tipo,
            origen_tipo=alerta.origen_tipo,
            origen_id=alerta.origen_id,
            mensaje=alerta.mensaje,
            estado=alerta.estado,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def obtener_por_id(self, alerta_id: uuid.UUID) -> AlertaDominio | None:
        fila = self._db.get(Alerta, alerta_id)
        return _a_dominio(fila) if fila else None

    def existe_activa(self, origen_tipo: str, origen_id: uuid.UUID, tipo: str) -> bool:
        stmt = select(Alerta.id).where(
            Alerta.origen_tipo == origen_tipo,
            Alerta.origen_id == origen_id,
            Alerta.tipo == tipo,
            Alerta.estado == "activa",
        )
        return self._db.execute(stmt).scalar_one_or_none() is not None

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosAlerta) -> PaginaAlertas:
        stmt = select(Alerta)
        if filtros.estado is not None:
            stmt = stmt.where(Alerta.estado == filtros.estado)
        if filtros.tipo is not None:
            stmt = stmt.where(Alerta.tipo == filtros.tipo)

        total = self._db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = (
            stmt.order_by(Alerta.creado_en.desc())
            .offset((filtros.pagina - 1) * filtros.tamano_pagina)
            .limit(filtros.tamano_pagina)
        )
        items = [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

        return PaginaAlertas(
            items=items, total=total, pagina=filtros.pagina, tamano_pagina=filtros.tamano_pagina
        )

    def contar_activas(self, laboratorio_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Alerta).where(Alerta.estado == "activa")
        return self._db.execute(stmt).scalar_one()

    def actualizar(self, alerta: AlertaDominio) -> AlertaDominio:
        fila = self._db.get(Alerta, alerta.id)
        assert fila is not None
        fila.estado = alerta.estado
        fila.leida_en = alerta.leida_en
        fila.resuelta_por_id = alerta.resuelta_por_id
        fila.resuelta_en = alerta.resuelta_en
        self._db.flush()
        return _a_dominio(fila)

    def resolver_por_origen(
        self, origen_tipo: str, origen_id: uuid.UUID, resuelta_por_id: uuid.UUID | None
    ) -> int:
        resultado = self._db.execute(
            update(Alerta)
            .where(
                Alerta.origen_tipo == origen_tipo,
                Alerta.origen_id == origen_id,
                Alerta.estado == "activa",
            )
            .values(estado="resuelta", resuelta_por_id=resuelta_por_id, resuelta_en=datetime.utcnow())
        )
        return resultado.rowcount


class NotificacionRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def encolar(self, notificacion: NotificacionDominio) -> NotificacionDominio:
        fila = NotificacionPendiente(
            id=notificacion.id,
            laboratorio_id=notificacion.laboratorio_id,
            alerta_id=notificacion.alerta_id,
            canal=notificacion.canal,
            payload=notificacion.payload,
            estado=notificacion.estado,
            intentos=notificacion.intentos,
        )
        self._db.add(fila)
        self._db.flush()
        return _notificacion_a_dominio(fila)

    def listar_pendientes(self, limite: int) -> list[NotificacionDominio]:
        stmt = (
            select(NotificacionPendiente)
            .where(NotificacionPendiente.estado == "pendiente")
            .order_by(NotificacionPendiente.creado_en)
            .limit(limite)
        )
        return [_notificacion_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def marcar_enviada(self, notificacion_id: uuid.UUID) -> None:
        self._db.execute(
            update(NotificacionPendiente)
            .where(NotificacionPendiente.id == notificacion_id)
            .values(estado="enviado", procesado_en=datetime.utcnow())
        )

    def marcar_fallida(self, notificacion_id: uuid.UUID) -> None:
        self._db.execute(
            update(NotificacionPendiente)
            .where(NotificacionPendiente.id == notificacion_id)
            .values(
                estado="fallido",
                intentos=NotificacionPendiente.intentos + 1,
                procesado_en=datetime.utcnow(),
            )
        )
