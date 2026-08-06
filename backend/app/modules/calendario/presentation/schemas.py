"""Schemas Pydantic del módulo Calendario. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.calendario.domain.entities import TIPOS_EVENTO_MANUAL


class EventoCalendarioRequest(BaseModel):
    tipo: str = Field(..., description=f"Uno de: {', '.join(TIPOS_EVENTO_MANUAL)}")
    titulo: str = Field(..., min_length=1, max_length=255)
    fecha: datetime
    descripcion: str | None = None


class EventoCalendarioOut(BaseModel):
    id: uuid.UUID
    tipo: str
    titulo: str
    descripcion: str | None
    fecha: datetime
    origen_tipo: str | None
    origen_id: uuid.UUID | None
    editable: bool
