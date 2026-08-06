"""DTOs de la API de Calibraciones. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.calibraciones.domain.entities import RESULTADOS_CALIBRACION


class UrlCertificadoRequest(BaseModel):
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tipo_mime: str = Field(..., min_length=1, max_length=100)
    tamano_bytes: int = Field(..., gt=0)


class UrlCertificadoOut(BaseModel):
    url_subida: str
    object_key: str


class ArchivoCertificadoConfirmado(BaseModel):
    object_key: str
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tamano_bytes: int = Field(..., gt=0)
    tipo_mime: str = Field(..., min_length=1, max_length=100)


class CalibracionRequest(BaseModel):
    equipo_id: uuid.UUID
    fecha_calibracion: date
    frecuencia_meses: int = Field(..., gt=0)
    laboratorio_proveedor: str | None = Field(default=None, max_length=200)
    numero_certificado: str | None = Field(default=None, max_length=100)
    resultado: str = Field(..., description=f"Uno de: {', '.join(RESULTADOS_CALIBRACION)}")
    incertidumbre: Decimal | None = None
    observaciones: str | None = None
    certificado: ArchivoCertificadoConfirmado | None = None


class CorregirCalibracionRequest(CalibracionRequest):
    motivo: str = Field(..., min_length=1, max_length=1000)


class CalibracionOut(BaseModel):
    id: uuid.UUID
    equipo_id: uuid.UUID
    fecha_calibracion: date
    frecuencia_meses: int
    proxima_fecha: date
    laboratorio_proveedor: str | None
    numero_certificado: str | None
    resultado: str
    incertidumbre: Decimal | None
    responsable_id: uuid.UUID | None
    corrige_a_id: uuid.UUID | None
    motivo_correccion: str | None
    observaciones: str | None
    tiene_certificado: bool
    semaforo: str
    dias_restantes: int | None
    creado_en: datetime


class UrlDescargaOut(BaseModel):
    url: str


class EquipoConSemaforoOut(BaseModel):
    equipo_id: uuid.UUID
    equipo_nombre: str
    equipo_codigo_interno: str
    ultima_calibracion_id: uuid.UUID | None
    proxima_fecha: date | None
    dias_restantes: int | None
    semaforo: str
