"""Schemas Pydantic del módulo Auditoría. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LogAuditoriaOut(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID | None
    ip_origen: str | None
    modulo: str
    accion: str
    entidad_tipo: str
    entidad_id: uuid.UUID | None
    valor_anterior: dict[str, Any] | None
    valor_nuevo: dict[str, Any] | None
    creado_en: datetime


class ValoresFiltroOut(BaseModel):
    modulos: list[str]
    acciones: list[str]


class PaginaAuditoriaOut(BaseModel):
    items: list[LogAuditoriaOut]
    total: int
    pagina: int
    tamano_pagina: int
