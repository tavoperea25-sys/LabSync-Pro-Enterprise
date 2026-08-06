"""DTOs de la API de Equipos. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.equipos.domain.entities import ESTADOS_OPERATIVOS


class EquipoRequest(BaseModel):
    codigo_interno: str = Field(..., min_length=1, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=200)
    estado_operativo: str = Field(default="operativo")
    categoria_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    responsable_id: uuid.UUID | None = None
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    fabricante: str | None = None
    proveedor: str | None = None
    fecha_adquisicion: date | None = None
    observaciones: str | None = None
    foto_object_key: str | None = None
    manual_object_key: str | None = None


class EquipoOut(BaseModel):
    id: uuid.UUID
    codigo_interno: str
    nombre: str
    estado_operativo: str
    categoria_id: uuid.UUID | None
    area_id: uuid.UUID | None
    responsable_id: uuid.UUID | None
    marca: str | None
    modelo: str | None
    numero_serie: str | None
    fabricante: str | None
    proveedor: str | None
    fecha_adquisicion: date | None
    observaciones: str | None
    foto_url: str | None
    # `foto_url` es una URL prefirmada de vista previa (expira) — el
    # frontend necesita el object_key estable para poder "no tocar la foto
    # actual" al reenviar un PATCH que solo cambia otro campo (mismo
    # criterio que `InstitucionOut.logo_object_key`, Sprint 12).
    foto_object_key: str | None
    # `manual_url` es una URL prefirmada de descarga (expira); `manual_object_key`
    # es el object_key estable, mismo criterio que la foto.
    manual_url: str | None
    manual_object_key: str | None
    creado_en: datetime
    actualizado_en: datetime


class UrlFotoRequest(BaseModel):
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tipo_mime: str = Field(..., min_length=1, max_length=100)
    tamano_bytes: int = Field(..., gt=0)


class UrlFotoOut(BaseModel):
    url_subida: str
    object_key: str


class UrlManualRequest(BaseModel):
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tipo_mime: str = Field(..., min_length=1, max_length=100)
    tamano_bytes: int = Field(..., gt=0)


class UrlManualOut(BaseModel):
    url_subida: str
    object_key: str


class PaginaEquiposOut(BaseModel):
    items: list[EquipoOut]
    total: int
    pagina: int
    tamano_pagina: int


class CategoriaEquipoOut(BaseModel):
    id: uuid.UUID
    nombre: str
    frecuencia_calibracion_default_meses: int | None
    bloquea_activacion_si_calibracion_vencida: bool


class CategoriaEquipoRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    frecuencia_calibracion_default_meses: int | None = None
    bloquea_activacion_si_calibracion_vencida: bool = False


class AreaOut(BaseModel):
    id: uuid.UUID
    nombre: str


class AreaRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)


class HistorialEntradaOut(BaseModel):
    id: uuid.UUID
    usuario_id: uuid.UUID | None
    accion: str
    valor_anterior: dict | None
    valor_nuevo: dict | None
    creado_en: datetime


ESTADOS_OPERATIVOS_VALIDOS = ESTADOS_OPERATIVOS
