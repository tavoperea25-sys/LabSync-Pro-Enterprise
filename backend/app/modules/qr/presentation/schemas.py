"""DTOs del módulo QR."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EquipoPublicoOut(BaseModel):
    codigo_interno: str
    nombre: str
    estado_operativo: str
    marca: str | None
    modelo: str | None
    foto_url: str | None
    dado_de_baja: bool


class ReportarIncidenciaRequest(BaseModel):
    descripcion: str = Field(..., min_length=1, max_length=1000)
    contacto_nombre: str | None = Field(default=None, max_length=150)
    contacto_medio: str | None = Field(default=None, max_length=150)


class IncidenciaCreadaOut(BaseModel):
    id: str
    estado: str


class QrInfoOut(BaseModel):
    token: str
    url_publica: str


class IncidenciaQrOut(BaseModel):
    id: str
    equipo_id: str
    equipo_codigo_interno: str
    equipo_nombre: str
    descripcion: str
    contacto_nombre: str | None
    contacto_medio: str | None
    estado: str
    creado_en: datetime


class ActualizarEstadoIncidenciaRequest(BaseModel):
    estado: Literal["pendiente", "en_revision", "resuelta"]
