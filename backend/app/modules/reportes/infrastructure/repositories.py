"""Implementación SQLAlchemy del repositorio de Reportes."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.reportes.domain.entities import ReporteGenerado as ReporteDominio
from app.modules.reportes.infrastructure.models import ReporteGenerado


def _a_dominio(fila: ReporteGenerado) -> ReporteDominio:
    return ReporteDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        tipo=fila.tipo,
        formato=fila.formato,
        filtros=fila.filtros,
        estado=fila.estado,
        object_key=fila.object_key,
        nombre_archivo=fila.nombre_archivo,
        error=fila.error,
        solicitado_por_id=fila.solicitado_por_id,
        creado_en=fila.creado_en,
        completado_en=fila.completado_en,
    )


class ReporteRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, reporte: ReporteDominio) -> ReporteDominio:
        fila = ReporteGenerado(
            id=reporte.id,
            laboratorio_id=reporte.laboratorio_id,
            tipo=reporte.tipo,
            formato=reporte.formato,
            filtros=reporte.filtros,
            estado=reporte.estado,
            object_key=reporte.object_key,
            nombre_archivo=reporte.nombre_archivo,
            error=reporte.error,
            solicitado_por_id=reporte.solicitado_por_id,
            completado_en=reporte.completado_en,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def obtener_por_id(self, reporte_id: uuid.UUID) -> ReporteDominio | None:
        fila = self._db.get(ReporteGenerado, reporte_id)
        return _a_dominio(fila) if fila else None

    def listar(self, laboratorio_id: uuid.UUID, limite: int) -> list[ReporteDominio]:
        stmt = (
            select(ReporteGenerado)
            .order_by(ReporteGenerado.creado_en.desc())
            .limit(limite)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def actualizar(self, reporte: ReporteDominio) -> ReporteDominio:
        fila = self._db.get(ReporteGenerado, reporte.id)
        assert fila is not None
        fila.estado = reporte.estado
        fila.object_key = reporte.object_key
        fila.nombre_archivo = reporte.nombre_archivo
        fila.error = reporte.error
        fila.completado_en = reporte.completado_en
        self._db.flush()
        return _a_dominio(fila)

    def listar_pendientes(self, limite: int) -> list[ReporteDominio]:
        stmt = (
            select(ReporteGenerado)
            .where(ReporteGenerado.estado == "pendiente")
            .order_by(ReporteGenerado.creado_en)
            .limit(limite)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]
