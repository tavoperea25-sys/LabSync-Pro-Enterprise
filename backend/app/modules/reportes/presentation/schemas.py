"""Schemas Pydantic del módulo Reportes. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class GenerarReporteRequest(BaseModel):
    tipo: str
    formato: str
    filtros: dict[str, Any] = {}


class ReporteOut(BaseModel):
    id: uuid.UUID
    tipo: str
    formato: str
    filtros: dict[str, Any] | None
    estado: str
    nombre_archivo: str | None
    error: str | None
    creado_en: datetime
    completado_en: datetime | None


class UrlDescargaOut(BaseModel):
    url: str


class TipoReporteOut(BaseModel):
    tipo: str
    etiqueta: str
    formatos_disponibles: list[str]
