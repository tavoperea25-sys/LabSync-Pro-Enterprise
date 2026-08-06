"""Schemas Pydantic del módulo Configuración. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ConfiguracionOut(BaseModel):
    umbral_alerta_calibracion_dias: int
    umbral_alerta_mantenimiento_dias: int
    umbral_alerta_documento_dias: int
    dias_retencion_papelera_documentos: int
    politica_password: dict[str, Any] | None
    mapeo_estados_mantenimiento: dict[str, str] | None


class ActualizarUmbralesRequest(BaseModel):
    umbral_alerta_calibracion_dias: int = Field(..., gt=0)
    umbral_alerta_mantenimiento_dias: int = Field(..., gt=0)
    umbral_alerta_documento_dias: int = Field(..., gt=0)
    dias_retencion_papelera_documentos: int = Field(..., gt=0)


class ActualizarPoliticaPasswordRequest(BaseModel):
    politica_password: dict[str, Any] | None


class ActualizarMapeoEstadosMantenimientoRequest(BaseModel):
    mapeo_estados_mantenimiento: dict[str, str] | None


class InstitucionOut(BaseModel):
    id: uuid.UUID
    nombre: str
    slug: str
    logo_url: str | None
    # `logo_url` es una URL prefirmada de descarga (expira) — el frontend
    # necesita el object_key estable para poder "no tocar el logo actual"
    # al reenviar un PATCH que solo cambia el nombre.
    logo_object_key: str | None


class ActualizarInstitucionRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    logo_object_key: str | None = None


class SolicitarLogoRequest(BaseModel):
    nombre_archivo: str = Field(..., min_length=1)
    tipo_mime: str = Field(..., min_length=1)
    tamano_bytes: int = Field(..., gt=0)


class UrlSubidaLogoOut(BaseModel):
    url_subida: str
    object_key: str
