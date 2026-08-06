"""DTOs de la API de Mantenimientos. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.mantenimientos.domain.entities import TIPOS_MANTENIMIENTO


class UrlArchivoRequest(BaseModel):
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tipo_mime: str = Field(..., min_length=1, max_length=100)
    tamano_bytes: int = Field(..., gt=0)


class UrlArchivoOut(BaseModel):
    url_subida: str
    object_key: str


class ArchivoConfirmado(BaseModel):
    object_key: str
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tamano_bytes: int = Field(..., gt=0)
    tipo_mime: str = Field(..., min_length=1, max_length=100)


class MantenimientoRequest(BaseModel):
    equipo_id: uuid.UUID
    tipo: str = Field(..., description=f"Uno de: {', '.join(TIPOS_MANTENIMIENTO)}")
    fecha_programada: date | None = None
    tecnico_responsable_id: uuid.UUID | None = None
    descripcion: str | None = None
    frecuencia_meses: int | None = Field(default=None, gt=0)


class CerrarMantenimientoRequest(BaseModel):
    fecha_ejecutada: date
    repuestos_utilizados: str | None = None
    tiempo_inactividad_horas: Decimal | None = None
    costo: Decimal | None = None
    descripcion: str | None = None


class CancelarMantenimientoRequest(BaseModel):
    motivo: str = Field(..., min_length=1, max_length=1000)


class MantenimientoOut(BaseModel):
    id: uuid.UUID
    equipo_id: uuid.UUID
    tipo: str
    estado: str
    fecha_programada: date | None
    fecha_ejecutada: date | None
    tecnico_responsable_id: uuid.UUID | None
    descripcion: str | None
    repuestos_utilizados: str | None
    tiempo_inactividad_horas: Decimal | None
    costo: Decimal | None
    tiene_informe: bool
    frecuencia_meses: int | None
    generado_de_id: uuid.UUID | None
    creado_en: datetime
    actualizado_en: datetime


class PaginaMantenimientosOut(BaseModel):
    items: list[MantenimientoOut]
    total: int
    pagina: int
    tamano_pagina: int


class EvidenciaOut(BaseModel):
    id: uuid.UUID
    nombre_archivo: str
    tamano_bytes: int
    tipo_mime: str
    creado_en: datetime


class UrlDescargaOut(BaseModel):
    url: str


class InactividadOut(BaseModel):
    equipo_id: uuid.UUID
    desde: date
    hasta: date
    horas: Decimal
