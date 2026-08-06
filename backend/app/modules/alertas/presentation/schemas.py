"""Schemas Pydantic del módulo Alertas. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AlertaOut(BaseModel):
    id: uuid.UUID
    tipo: str
    origen_tipo: str
    origen_id: uuid.UUID
    mensaje: str
    estado: str
    leida_en: datetime | None
    resuelta_por_id: uuid.UUID | None
    resuelta_en: datetime | None
    creado_en: datetime


class ContadorActivasOut(BaseModel):
    activas: int


class PaginaAlertasOut(BaseModel):
    items: list[AlertaOut]
    total: int
    pagina: int
    tamano_pagina: int


class EvaluarOut(BaseModel):
    generadas: int
