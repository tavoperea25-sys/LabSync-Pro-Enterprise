"""Implementación SQLAlchemy del repositorio de Mantenimientos."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.modules.mantenimientos.domain.entities import ESTADOS_OPERATIVOS_ABIERTOS
from app.modules.mantenimientos.domain.entities import Mantenimiento as MantenimientoDominio
from app.modules.mantenimientos.domain.ports import FiltrosMantenimiento, PaginaMantenimientos
from app.modules.mantenimientos.infrastructure.models import Mantenimiento


def _a_dominio(fila: Mantenimiento) -> MantenimientoDominio:
    return MantenimientoDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        equipo_id=fila.equipo_id,
        tipo=fila.tipo,
        estado=fila.estado,
        fecha_programada=fila.fecha_programada,
        fecha_ejecutada=fila.fecha_ejecutada,
        tecnico_responsable_id=fila.tecnico_responsable_id,
        descripcion=fila.descripcion,
        repuestos_utilizados=fila.repuestos_utilizados,
        tiempo_inactividad_horas=fila.tiempo_inactividad_horas,
        costo=fila.costo,
        informe_adjunto_id=fila.informe_adjunto_id,
        frecuencia_meses=fila.frecuencia_meses,
        generado_de_id=fila.generado_de_id,
        creado_en=fila.creado_en,
        actualizado_en=fila.actualizado_en,
    )


class MantenimientoRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, mantenimiento: MantenimientoDominio) -> MantenimientoDominio:
        fila = Mantenimiento(
            id=mantenimiento.id,
            laboratorio_id=mantenimiento.laboratorio_id,
            equipo_id=mantenimiento.equipo_id,
            tipo=mantenimiento.tipo,
            estado=mantenimiento.estado,
            fecha_programada=mantenimiento.fecha_programada,
            fecha_ejecutada=mantenimiento.fecha_ejecutada,
            tecnico_responsable_id=mantenimiento.tecnico_responsable_id,
            descripcion=mantenimiento.descripcion,
            repuestos_utilizados=mantenimiento.repuestos_utilizados,
            tiempo_inactividad_horas=mantenimiento.tiempo_inactividad_horas,
            costo=mantenimiento.costo,
            informe_adjunto_id=mantenimiento.informe_adjunto_id,
            frecuencia_meses=mantenimiento.frecuencia_meses,
            generado_de_id=mantenimiento.generado_de_id,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def obtener_por_id(self, mantenimiento_id: uuid.UUID) -> MantenimientoDominio | None:
        fila = self._db.get(Mantenimiento, mantenimiento_id)
        return _a_dominio(fila) if fila else None

    @staticmethod
    def _con_filtros(filtros: FiltrosMantenimiento):  # type: ignore[no-untyped-def]
        stmt = select(Mantenimiento)
        if filtros.equipo_id is not None:
            stmt = stmt.where(Mantenimiento.equipo_id == filtros.equipo_id)
        if filtros.tecnico_responsable_id is not None:
            stmt = stmt.where(Mantenimiento.tecnico_responsable_id == filtros.tecnico_responsable_id)
        if filtros.estado is not None:
            stmt = stmt.where(Mantenimiento.estado == filtros.estado)
        if filtros.fecha_desde is not None:
            stmt = stmt.where(Mantenimiento.fecha_programada >= filtros.fecha_desde)
        if filtros.fecha_hasta is not None:
            stmt = stmt.where(Mantenimiento.fecha_programada <= filtros.fecha_hasta)
        return stmt

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosMantenimiento) -> PaginaMantenimientos:
        stmt = self._con_filtros(filtros)

        total = self._db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = (
            stmt.order_by(Mantenimiento.fecha_programada.desc().nullslast(), Mantenimiento.creado_en.desc())
            .offset((filtros.pagina - 1) * filtros.tamano_pagina)
            .limit(filtros.tamano_pagina)
        )
        items = [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

        return PaginaMantenimientos(
            items=items, total=total, pagina=filtros.pagina, tamano_pagina=filtros.tamano_pagina
        )

    def listar_todos(
        self, laboratorio_id: uuid.UUID, filtros: FiltrosMantenimiento
    ) -> list[MantenimientoDominio]:
        stmt = self._con_filtros(filtros).order_by(
            Mantenimiento.fecha_programada.desc().nullslast(), Mantenimiento.creado_en.desc()
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def contar_abiertos_por_equipo(self, equipo_id: uuid.UUID, excluir_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count()).select_from(Mantenimiento).where(
            Mantenimiento.equipo_id == equipo_id, Mantenimiento.estado.in_(ESTADOS_OPERATIVOS_ABIERTOS)
        )
        if excluir_id is not None:
            stmt = stmt.where(Mantenimiento.id != excluir_id)
        return self._db.execute(stmt).scalar_one()

    def contar_abiertos_por_tipo(self) -> dict[str, int]:
        stmt = (
            select(Mantenimiento.tipo, func.count())
            .where(Mantenimiento.estado.in_(ESTADOS_OPERATIVOS_ABIERTOS))
            .group_by(Mantenimiento.tipo)
        )
        return dict(self._db.execute(stmt).tuples().all())

    def actualizar(self, mantenimiento: MantenimientoDominio) -> MantenimientoDominio:
        fila = self._db.get(Mantenimiento, mantenimiento.id)
        assert fila is not None
        fila.estado = mantenimiento.estado
        fila.fecha_programada = mantenimiento.fecha_programada
        fila.fecha_ejecutada = mantenimiento.fecha_ejecutada
        fila.tecnico_responsable_id = mantenimiento.tecnico_responsable_id
        fila.descripcion = mantenimiento.descripcion
        fila.repuestos_utilizados = mantenimiento.repuestos_utilizados
        fila.tiempo_inactividad_horas = mantenimiento.tiempo_inactividad_horas
        fila.costo = mantenimiento.costo
        fila.informe_adjunto_id = mantenimiento.informe_adjunto_id
        fila.frecuencia_meses = mantenimiento.frecuencia_meses
        self._db.flush()
        return _a_dominio(fila)

    def sumar_inactividad(self, equipo_id: uuid.UUID, desde: date, hasta: date) -> Decimal:
        stmt = select(func.coalesce(func.sum(Mantenimiento.tiempo_inactividad_horas), 0)).where(
            Mantenimiento.equipo_id == equipo_id,
            Mantenimiento.estado == "completado",
            Mantenimiento.fecha_ejecutada.is_not(None),
            Mantenimiento.fecha_ejecutada >= desde,
            Mantenimiento.fecha_ejecutada <= hasta,
        )
        resultado = self._db.execute(stmt).scalar_one()
        return Decimal(resultado) if resultado is not None else Decimal(0)

    def listar_proximos_por_tecnico(self, tecnico_id: uuid.UUID, dia: date) -> list[MantenimientoDominio]:
        stmt = (
            select(Mantenimiento)
            .where(
                Mantenimiento.tecnico_responsable_id == tecnico_id,
                Mantenimiento.fecha_programada == dia,
                Mantenimiento.estado.in_(ESTADOS_OPERATIVOS_ABIERTOS),
            )
            .order_by(Mantenimiento.creado_en)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_proximos(self, laboratorio_id: uuid.UUID, dias_umbral: int) -> list[MantenimientoDominio]:
        limite = date.today() + timedelta(days=dias_umbral)
        stmt = select(Mantenimiento).where(
            Mantenimiento.estado == "programado",
            Mantenimiento.fecha_programada.is_not(None),
            Mantenimiento.fecha_programada <= limite,
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def buscar_texto(self, consulta: str, limite: int) -> list[MantenimientoDominio]:
        stmt = (
            select(Mantenimiento)
            .where(
                text(
                    "to_tsvector('spanish', coalesce(descripcion,'') || ' ' || "
                    "coalesce(repuestos_utilizados,'')) @@ plainto_tsquery('spanish', :consulta)"
                )
            )
            .params(consulta=consulta)
            .limit(limite)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]
