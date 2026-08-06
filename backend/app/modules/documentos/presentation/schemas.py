"""DTOs de la API de Documentos. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class UrlSubidaRequest(BaseModel):
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tipo_mime: str = Field(..., min_length=1, max_length=100)
    tamano_bytes: int = Field(..., gt=0)


class UrlSubidaOut(BaseModel):
    url_subida: str
    object_key: str


class ArchivoConfirmado(BaseModel):
    """Datos que el frontend reporta tras completar el PUT a MinIO — el
    backend confía en lo declarado al pedir la URL de subida, ya que es el
    mismo cliente autenticado que hizo ambas llamadas."""

    object_key: str
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tamano_bytes: int = Field(..., gt=0)
    tipo_mime: str = Field(..., min_length=1, max_length=100)


class DocumentoRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    carpeta_id: uuid.UUID | None = None
    categoria: str | None = None
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None
    archivo: ArchivoConfirmado


class DocumentoActualizarRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    carpeta_id: uuid.UUID | None = Field(default=None)
    mover_a_carpeta: bool = Field(
        default=False,
        description="True si `carpeta_id` (incluido null, para mover a la raíz) debe aplicarse.",
    )
    categoria: str | None = Field(default=None)
    fecha_emision: date | None = Field(default=None)
    fecha_vencimiento: date | None = Field(default=None)
    actualizar_metadatos: bool = Field(
        default=False,
        description="True si categoria/fecha_emision/fecha_vencimiento (incluido null) deben aplicarse.",
    )


class RechazarRequest(BaseModel):
    comentario: str = Field(..., min_length=1, max_length=1000)


class VersionOut(BaseModel):
    id: uuid.UUID
    numero_version: int
    nombre_archivo: str
    tamano_bytes: int
    tipo_mime: str
    subido_por_id: uuid.UUID | None
    aprobado_por_id: uuid.UUID | None
    aprobado_en: datetime | None
    creado_en: datetime


class EtiquetaOut(BaseModel):
    id: uuid.UUID
    nombre: str


class RechazoOut(BaseModel):
    comentario: str
    usuario_id: uuid.UUID | None
    creado_en: datetime


class DocumentoOut(BaseModel):
    id: uuid.UUID
    carpeta_id: uuid.UUID | None
    nombre: str
    categoria: str | None
    estado: str
    estado_efectivo: str
    fecha_emision: date | None
    fecha_vencimiento: date | None
    responsable_aprobacion_id: uuid.UUID | None
    version_vigente_id: uuid.UUID | None
    creado_en: datetime
    actualizado_en: datetime


class DocumentoDetalleOut(DocumentoOut):
    versiones: list[VersionOut]
    etiquetas: list[EtiquetaOut]
    es_favorito: bool
    ultimo_rechazo: RechazoOut | None


class PaginaDocumentosOut(BaseModel):
    items: list[DocumentoOut]
    total: int
    pagina: int
    tamano_pagina: int


class UrlDescargaOut(BaseModel):
    url: str


class VistaPreviaOut(BaseModel):
    url: str | None
    nombre_archivo: str
    tipo_mime: str
    tamano_bytes: int


class FavoritoOut(BaseModel):
    es_favorito: bool


class EtiquetaRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=60)


class CarpetaOut(BaseModel):
    id: uuid.UUID
    nombre: str
    carpeta_padre_id: uuid.UUID | None
    creado_en: datetime


class CarpetaRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    carpeta_padre_id: uuid.UUID | None = None


class CarpetaActualizarRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
