"""Entidad de dominio de Auditoría. Ver docs/03-requerimientos-funcionales.md
Módulo 11 y docs/07-reglas-de-negocio.md (RN-AUD-*)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class LogAuditoria:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    usuario_id: uuid.UUID | None
    ip_origen: str | None
    modulo: str
    accion: str
    entidad_tipo: str
    entidad_id: uuid.UUID | None
    valor_anterior: dict[str, Any] | None
    valor_nuevo: dict[str, Any] | None
    creado_en: datetime
