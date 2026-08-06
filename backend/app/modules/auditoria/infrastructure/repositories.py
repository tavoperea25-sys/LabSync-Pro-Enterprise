"""Repositorio de Auditoría — el único punto de escritura de logs_auditoria
en todo el backend (RN-AUD-02: una acción de negocio, un registro)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modules.auditoria.domain.entities import LogAuditoria as LogDominio
from app.modules.auditoria.domain.ports import FiltrosAuditoria, PaginaAuditoria
from app.modules.auditoria.infrastructure.models import LogAuditoria


def _json_seguro(valor: dict[str, Any] | None) -> dict[str, Any] | None:
    """UUID/date/datetime no son serializables por el driver JSONB
    directamente — se normalizan a string antes de insertar."""
    if valor is None:
        return None
    return json.loads(json.dumps(valor, default=str))


def _a_dominio(fila: LogAuditoria) -> LogDominio:
    return LogDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        usuario_id=fila.usuario_id,
        ip_origen=fila.ip_origen,
        modulo=fila.modulo,
        accion=fila.accion,
        entidad_tipo=fila.entidad_tipo,
        entidad_id=fila.entidad_id,
        valor_anterior=fila.valor_anterior,
        valor_nuevo=fila.valor_nuevo,
        creado_en=fila.creado_en,
    )


class AuditoriaRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def registrar(
        self,
        laboratorio_id: uuid.UUID,
        usuario_id: uuid.UUID | None,
        ip_origen: str | None,
        modulo: str,
        accion: str,
        entidad_tipo: str,
        entidad_id: uuid.UUID | None,
        valor_anterior: dict[str, Any] | None = None,
        valor_nuevo: dict[str, Any] | None = None,
    ) -> None:
        self._db.add(
            LogAuditoria(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                usuario_id=usuario_id,
                ip_origen=ip_origen,
                modulo=modulo,
                accion=accion,
                entidad_tipo=entidad_tipo,
                entidad_id=entidad_id,
                valor_anterior=_json_seguro(valor_anterior),
                valor_nuevo=_json_seguro(valor_nuevo),
                creado_en=datetime.utcnow(),
            )
        )
        # flush (no commit): la escritura de auditoría vive en la MISMA
        # transacción que la acción de negocio que la origina — si esa
        # transacción falla y hace rollback, no debe quedar un registro de
        # auditoría "huérfano" de algo que en realidad no ocurrió (RN-AUD-02).
        self._db.flush()

    def listar_por_entidad(self, entidad_tipo: str, entidad_id: uuid.UUID) -> list[LogDominio]:
        stmt = (
            select(LogAuditoria)
            .where(LogAuditoria.entidad_tipo == entidad_tipo, LogAuditoria.entidad_id == entidad_id)
            .order_by(LogAuditoria.creado_en.desc())
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    @staticmethod
    def _con_filtros(filtros: FiltrosAuditoria):  # type: ignore[no-untyped-def]
        stmt = select(LogAuditoria)
        if filtros.usuario_id is not None:
            stmt = stmt.where(LogAuditoria.usuario_id == filtros.usuario_id)
        if filtros.modulo is not None:
            stmt = stmt.where(LogAuditoria.modulo == filtros.modulo)
        if filtros.accion is not None:
            stmt = stmt.where(LogAuditoria.accion == filtros.accion)
        if filtros.desde is not None:
            stmt = stmt.where(LogAuditoria.creado_en >= filtros.desde)
        if filtros.hasta is not None:
            stmt = stmt.where(LogAuditoria.creado_en <= filtros.hasta)
        return stmt

    def listar_filtrado(self, filtros: FiltrosAuditoria, limite: int) -> list[LogDominio]:
        stmt = self._con_filtros(filtros).order_by(LogAuditoria.creado_en.desc()).limit(limite)
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_filtrado_paginado(
        self, filtros: FiltrosAuditoria, pagina: int, tamano_pagina: int
    ) -> PaginaAuditoria:
        stmt = self._con_filtros(filtros)
        total = self._db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        # `creado_en` no es única — dos logs pueden compartir el mismo
        # timestamp (dos acciones en la misma transacción, p. ej. C1/C6).
        # Se desempata por `id` para que el orden entre páginas sea estable,
        # a diferencia del `order_by` de Equipos (creado_en solo) que
        # heredó ese mismo punto ciego antes de esta fase.
        stmt = (
            stmt.order_by(LogAuditoria.creado_en.desc(), LogAuditoria.id.desc())
            .offset((pagina - 1) * tamano_pagina)
            .limit(tamano_pagina)
        )
        filas = self._db.execute(stmt).scalars().all()

        return PaginaAuditoria(
            items=[_a_dominio(f) for f in filas], total=total, pagina=pagina, tamano_pagina=tamano_pagina
        )

    def listar_modulos_distintos(self) -> list[str]:
        stmt = select(LogAuditoria.modulo).distinct().order_by(LogAuditoria.modulo)
        return list(self._db.execute(stmt).scalars())

    def listar_acciones_distintas(self) -> list[str]:
        stmt = select(LogAuditoria.accion).distinct().order_by(LogAuditoria.accion)
        return list(self._db.execute(stmt).scalars())

    def buscar_texto(self, consulta: str, limite: int) -> list[LogDominio]:
        stmt = (
            select(LogAuditoria)
            .where(
                text(
                    "to_tsvector('spanish', coalesce(modulo,'') || ' ' || coalesce(accion,'') || ' ' || "
                    "coalesce(entidad_tipo,'')) @@ plainto_tsquery('spanish', :consulta)"
                )
            )
            .params(consulta=consulta)
            .order_by(LogAuditoria.creado_en.desc())
            .limit(limite)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]
