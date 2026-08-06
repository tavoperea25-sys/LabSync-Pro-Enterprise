"""Entidad de dominio de Adjuntos — tabla polimórfica compartida entre
módulos (Calibraciones, y más adelante Mantenimientos). Ver
docs/14-base-de-datos.md ("adjuntos, reutilizada por Equipos/Mantenimientos")."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

# Conjunto cerrado de valores que de hecho escribe el código — solo
# Mantenimientos y Calibraciones usan `AdjuntoRepository` (ver
# `mantenimiento_service.py`/`calibracion_service.py`). Reflejado también en
# el CHECK constraint `ck_adjuntos_entidad_tipo` (alembic/versions/0016).
ENTIDADES_ADJUNTO = ("mantenimiento_evidencia", "mantenimiento_informe", "calibracion_certificado")


@dataclass
class Adjunto:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    entidad_tipo: str
    entidad_id: uuid.UUID
    object_key: str
    nombre_archivo: str
    tamano_bytes: int
    tipo_mime: str
    subido_por_id: uuid.UUID | None
    creado_en: datetime
