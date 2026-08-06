"""Implementación SQLAlchemy del repositorio de Calibraciones."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.calibraciones.domain.entities import (
    UMBRAL_ALERTA_CALIBRACION_DIAS,
    EquipoConSemaforo,
    semaforo,
)
from app.modules.calibraciones.domain.entities import Calibracion as CalibracionDominio
from app.modules.calibraciones.infrastructure.models import Calibracion
from app.modules.configuracion.infrastructure.models import ConfiguracionLaboratorio
from app.modules.equipos.infrastructure.models import Equipo


def _a_dominio(fila: Calibracion) -> CalibracionDominio:
    return CalibracionDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        equipo_id=fila.equipo_id,
        fecha_calibracion=fila.fecha_calibracion,
        frecuencia_meses=fila.frecuencia_meses,
        proxima_fecha=fila.proxima_fecha,
        laboratorio_proveedor=fila.laboratorio_proveedor,
        numero_certificado=fila.numero_certificado,
        resultado=fila.resultado,
        incertidumbre=fila.incertidumbre,
        responsable_id=fila.responsable_id,
        certificado_adjunto_id=fila.certificado_adjunto_id,
        corrige_a_id=fila.corrige_a_id,
        motivo_correccion=fila.motivo_correccion,
        observaciones=fila.observaciones,
        creado_en=fila.creado_en,
    )


class CalibracionRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, calibracion: CalibracionDominio) -> CalibracionDominio:
        fila = Calibracion(
            id=calibracion.id,
            laboratorio_id=calibracion.laboratorio_id,
            equipo_id=calibracion.equipo_id,
            fecha_calibracion=calibracion.fecha_calibracion,
            frecuencia_meses=calibracion.frecuencia_meses,
            proxima_fecha=calibracion.proxima_fecha,
            laboratorio_proveedor=calibracion.laboratorio_proveedor,
            numero_certificado=calibracion.numero_certificado,
            resultado=calibracion.resultado,
            incertidumbre=calibracion.incertidumbre,
            responsable_id=calibracion.responsable_id,
            certificado_adjunto_id=calibracion.certificado_adjunto_id,
            corrige_a_id=calibracion.corrige_a_id,
            motivo_correccion=calibracion.motivo_correccion,
            observaciones=calibracion.observaciones,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def obtener_por_id(self, calibracion_id: uuid.UUID) -> CalibracionDominio | None:
        fila = self._db.get(Calibracion, calibracion_id)
        return _a_dominio(fila) if fila else None

    def listar_todas(self, laboratorio_id: uuid.UUID) -> list[CalibracionDominio]:
        stmt = select(Calibracion).order_by(Calibracion.fecha_calibracion.desc()).limit(5000)
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_por_equipo(self, equipo_id: uuid.UUID) -> list[CalibracionDominio]:
        stmt = (
            select(Calibracion)
            .where(Calibracion.equipo_id == equipo_id)
            .order_by(Calibracion.fecha_calibracion.desc(), Calibracion.creado_en.desc())
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def _umbral_calibracion(self, laboratorio_id: uuid.UUID) -> int:
        """RF-CFG-03 — umbral configurado por el laboratorio, o el valor por
        defecto si nunca configuró uno (fila creada perezosamente, ver
        alembic/versions/0010_configuracion.py)."""
        fila = self._db.get(ConfiguracionLaboratorio, laboratorio_id)
        return fila.umbral_alerta_calibracion_dias if fila else UMBRAL_ALERTA_CALIBRACION_DIAS

    def _ultima_por_equipo(
        self, laboratorio_id: uuid.UUID, fecha_corte: date | None = None
    ) -> list[EquipoConSemaforo]:
        # DISTINCT ON (Postgres) — la calibración más reciente por equipo,
        # priorizando fecha_calibracion y, en empate, la más reciente
        # registrada (una corrección puede compartir fecha con la original).
        # `fecha_corte` (RF-REP-04) reconstruye el estado "tal como se veía"
        # en una fecha pasada: solo mira calibraciones y equipos que ya
        # existían para entonces, y calcula el semáforo relativo a esa
        # fecha en vez de a hoy.
        umbral = self._umbral_calibracion(laboratorio_id)
        referencia = fecha_corte or date.today()
        ultima_por_equipo = (
            select(Calibracion)
            .where(Calibracion.fecha_calibracion <= referencia)
            .distinct(Calibracion.equipo_id)
            .order_by(
                Calibracion.equipo_id, Calibracion.fecha_calibracion.desc(), Calibracion.creado_en.desc()
            )
            .subquery()
        )
        stmt = (
            select(Equipo, ultima_por_equipo.c.id, ultima_por_equipo.c.proxima_fecha)
            .outerjoin(ultima_por_equipo, ultima_por_equipo.c.equipo_id == Equipo.id)
            .where(Equipo.eliminado_en.is_(None))
        )
        if fecha_corte is not None:
            stmt = stmt.where(Equipo.creado_en <= fecha_corte)
        filas: list[EquipoConSemaforo] = []
        for equipo, calibracion_id, proxima_fecha in self._db.execute(stmt).all():
            filas.append(
                EquipoConSemaforo(
                    equipo_id=equipo.id,
                    equipo_nombre=equipo.nombre,
                    equipo_codigo_interno=equipo.codigo_interno,
                    ultima_calibracion_id=calibracion_id,
                    proxima_fecha=proxima_fecha,
                    dias_restantes=(proxima_fecha - referencia).days if proxima_fecha else None,
                    semaforo=semaforo(proxima_fecha, referencia, umbral),
                )
            )
        return filas

    def listar_criticos(self, laboratorio_id: uuid.UUID) -> list[EquipoConSemaforo]:
        # Solo "críticos": rojo (vencido) primero por más antiguo, luego
        # amarillo (próximo) por más urgente, luego gris (nunca calibrado).
        # "verde" se excluye — no es información urgente para este listado.
        orden_semaforo = {"rojo": 0, "amarillo": 1, "gris": 2}
        criticos = [f for f in self._ultima_por_equipo(laboratorio_id) if f.semaforo != "verde"]
        criticos.sort(key=lambda f: (orden_semaforo[f.semaforo], f.proxima_fecha or date.max))
        return criticos

    def listar_estado_todos(self, laboratorio_id: uuid.UUID) -> list[EquipoConSemaforo]:
        """RF-REP-02 — a diferencia de `listar_criticos`, incluye "verde"."""
        return self._ultima_por_equipo(laboratorio_id)

    def listar_estado_a_fecha(self, laboratorio_id: uuid.UUID, fecha_corte: date) -> list[EquipoConSemaforo]:
        """RF-REP-04 — el estado tal como era en una fecha pasada."""
        return self._ultima_por_equipo(laboratorio_id, fecha_corte)

    def listar_proximas(self, laboratorio_id: uuid.UUID, desde: date, hasta: date) -> list[EquipoConSemaforo]:
        return [
            f
            for f in self._ultima_por_equipo(laboratorio_id)
            if f.proxima_fecha is not None and desde <= f.proxima_fecha <= hasta
        ]

    def buscar_texto(self, consulta: str, limite: int) -> list[CalibracionDominio]:
        stmt = (
            select(Calibracion)
            .where(
                text(
                    "to_tsvector('spanish', coalesce(numero_certificado,'') || ' ' || "
                    "coalesce(laboratorio_proveedor,'')) @@ plainto_tsquery('spanish', :consulta)"
                )
            )
            .params(consulta=consulta)
            .limit(limite)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]
