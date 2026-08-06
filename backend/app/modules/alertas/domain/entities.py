"""Entidades del módulo Alertas. Ver docs/14-base-de-datos.md y
docs/03-requerimientos-funcionales.md (RF-ALT-01 a RF-ALT-06 — Sprint 8)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

TIPOS_ALERTA = ("critica", "preventiva")
ORIGENES_ALERTA = ("calibracion", "documento", "mantenimiento", "equipo")
ESTADOS_ALERTA = ("activa", "resuelta")

CANALES_NOTIFICACION = ("websocket", "email", "push")
ESTADOS_NOTIFICACION = ("pendiente", "enviado", "fallido")


@dataclass
class Alerta:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    tipo: str
    origen_tipo: str
    origen_id: uuid.UUID
    mensaje: str
    estado: str
    leida_en: datetime | None
    resuelta_por_id: uuid.UUID | None
    resuelta_en: datetime | None
    creado_en: datetime

    def esta_activa(self) -> bool:
        return self.estado == "activa"


@dataclass
class NotificacionPendiente:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    alerta_id: uuid.UUID
    canal: str
    payload: dict
    estado: str
    intentos: int
    procesado_en: datetime | None
    creado_en: datetime
