from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel


class KpisOut(BaseModel):
    equipos_total: int
    equipos_operativos: int
    equipos_fuera_de_servicio: int
    equipos_en_mantenimiento: int
    equipos_de_baja: int
    equipos_porcentaje_operativo: float

    calibraciones_proximas_30_dias: int
    calibraciones_semaforo: str

    documentos_vencidos: int
    documentos_por_vencer: int
    documentos_en_revision: int

    mantenimientos_preventivos_proximos: int
    mantenimientos_correctivos_abiertos: int

    cumplimiento_documental_pct: float | None


class EquipoCriticoOut(BaseModel):
    equipo_id: uuid.UUID
    equipo_nombre: str
    equipo_codigo_interno: str
    area_nombre: str | None
    estado_operativo: str
    ultima_calibracion_fecha: date | None
    proxima_calibracion_fecha: date | None
    semaforo_calibracion: str | None
    responsable_nombre: str | None


class ActividadRecienteOut(BaseModel):
    usuario_nombre: str | None
    accion: str
    modulo: str
    entidad_tipo: str
    creado_en: datetime
