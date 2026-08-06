"""Entidades del Dashboard — agregaciones de solo lectura sobre Equipos,
Calibraciones, Documentos, Mantenimientos y Auditoría. Este módulo no tiene
tabla propia: todo se calcula a partir de los repositorios de los módulos
de negocio (ver `application/dashboard_service.py`)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

SEMAFOROS_CALIBRACION = ("normal", "atencion", "critico")


@dataclass
class ResumenDashboard:
    equipos_total: int
    equipos_operativos: int
    equipos_en_mantenimiento: int
    equipos_fuera_de_servicio: int
    equipos_de_baja: int
    equipos_porcentaje_operativo: float

    calibraciones_proximas_30_dias: int
    calibraciones_semaforo: str  # uno de SEMAFOROS_CALIBRACION

    documentos_vencidos: int
    documentos_por_vencer: int
    documentos_en_revision: int

    mantenimientos_preventivos_proximos: int
    mantenimientos_correctivos_abiertos: int

    # None si el laboratorio no tiene ningún documento activo todavía —
    # un porcentaje sobre cero documentos no es información real, es ruido.
    cumplimiento_documental_pct: float | None


@dataclass
class EquipoCritico:
    """Una fila de la tabla "Equipos que requieren atención": equipos cuyo
    estado operativo no es "operativo", o cuya calibración está vencida
    o próxima a vencer (semáforo rojo/amarillo)."""

    equipo_id: uuid.UUID
    equipo_nombre: str
    equipo_codigo_interno: str
    area_nombre: str | None
    estado_operativo: str
    ultima_calibracion_fecha: date | None
    proxima_calibracion_fecha: date | None
    semaforo_calibracion: str | None
    responsable_nombre: str | None


@dataclass
class ActividadReciente:
    """Una fila del timeline de "Historial de actividad" — proyección de
    auditoría legible para el Dashboard (RN-AUD-01/02: la fuente sigue
    siendo el log de auditoría inmutable, esto es solo una vista)."""

    usuario_nombre: str | None  # None => acción del sistema (worker), no de una persona
    accion: str
    modulo: str
    entidad_tipo: str
    creado_en: datetime
