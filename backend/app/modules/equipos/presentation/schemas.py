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
    # Fase 2 de hojas de vida (docs/25-...md sección 2) — todos opcionales,
    # ningún campo técnico es obligatorio (docs/24-...md sección 3.8).
    proveedor_id: uuid.UUID | None = None
    fabricante_id: uuid.UUID | None = None
    capitulo: str | None = None
    grupo: str | None = None
    subgrupo: str | None = None
    ubicacion: str | None = None
    numero_inventario: str | None = None
    condicion_fisica: str | None = None
    clasificacion_riesgo: str | None = None
    criticidad: str | None = None
    forma_adquisicion: str | None = None
    garantia: bool | None = None
    garantia_inicio: date | None = None
    garantia_fin: date | None = None


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
    proveedor_id: uuid.UUID | None
    fabricante_id: uuid.UUID | None
    capitulo: str | None
    grupo: str | None
    subgrupo: str | None
    ubicacion: str | None
    numero_inventario: str | None
    condicion_fisica: str | None
    clasificacion_riesgo: str | None
    criticidad: str | None
    forma_adquisicion: str | None
    garantia: bool | None
    garantia_inicio: date | None
    garantia_fin: date | None
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


# ---- Catálogos de proveedores y fabricantes (Fase 2 de hojas de vida) ---------


class ProveedorOut(BaseModel):
    id: uuid.UUID
    nombre: str
    pais_ciudad: str | None
    direccion: str | None
    email: str | None
    telefono: str | None
    contacto: str | None


class ProveedorRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    pais_ciudad: str | None = None
    direccion: str | None = None
    email: str | None = None
    telefono: str | None = None
    contacto: str | None = None


class FabricanteOut(BaseModel):
    id: uuid.UUID
    nombre: str
    pais_ciudad: str | None
    direccion: str | None
    email: str | None
    telefono: str | None
    contacto: str | None


class FabricanteRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    pais_ciudad: str | None = None
    direccion: str | None = None
    email: str | None = None
    telefono: str | None = None
    contacto: str | None = None


# ---- Ficha técnica extendida, accesorios y manuales ---------------------------


class FichaTecnicaOut(BaseModel):
    voltaje: str | None
    corriente: str | None
    frecuencia: str | None
    corriente_ma: str | None
    variable_medicion: str | None
    rango_medicion: str | None
    rpm: str | None
    temperatura_trabajo: str | None
    humedad_trabajo: str | None
    peso: str | None
    dimensiones: str | None
    color: str | None
    numero_puertas: str | None
    clase_sistema: str | None
    alimentacion: str | None
    uso: str | None
    uso_especifico: str | None
    condiciones_ambientales: str | None
    datos_adicionales: dict
    # `None` cuando el equipo todavía no tiene fila en `equipo_ficha_tecnica`
    # (relación 1:1 opcional hasta el primer `PUT` — ver router).
    actualizado_en: datetime | None


class FichaTecnicaRequest(BaseModel):
    voltaje: str | None = None
    corriente: str | None = None
    frecuencia: str | None = None
    corriente_ma: str | None = None
    variable_medicion: str | None = None
    rango_medicion: str | None = None
    rpm: str | None = None
    temperatura_trabajo: str | None = None
    humedad_trabajo: str | None = None
    peso: str | None = None
    dimensiones: str | None = None
    color: str | None = None
    numero_puertas: str | None = None
    clase_sistema: str | None = None
    alimentacion: str | None = None
    uso: str | None = None
    uso_especifico: str | None = None
    condiciones_ambientales: str | None = None
    datos_adicionales: dict = Field(default_factory=dict)


class AccesorioOut(BaseModel):
    id: uuid.UUID
    cantidad: int | None
    descripcion: str
    observaciones: str | None


class AccesorioRequest(BaseModel):
    cantidad: int | None = None
    descripcion: str = Field(..., min_length=1)
    observaciones: str | None = None


class ManualOut(BaseModel):
    tipo: str
    disponible: bool
    idioma: str | None
    object_key: str | None
    url: str | None


class ManualRequest(BaseModel):
    disponible: bool = False
    idioma: str | None = None
    object_key: str | None = None
