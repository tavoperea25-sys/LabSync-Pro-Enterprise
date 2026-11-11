"""Entidades de dominio del módulo Equipos. Ver docs/03-requerimientos-funcionales.md
Módulo 3 y docs/07-reglas-de-negocio.md (RN-EQ-*)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

ESTADOS_OPERATIVOS = ("operativo", "fuera_de_servicio", "en_mantenimiento", "de_baja")

# Fase 2 de hojas de vida (docs/25-diseno-tecnico-hojas-de-vida.md sección 2,
# migración 0019) — "condición física" es distinta de `estado_operativo`
# (docs/24-...md sección 3.4): un equipo puede estar en condición "Regular"
# y operativo al mismo tiempo.
CONDICIONES_FISICAS = ("bueno", "regular", "malo")
CLASIFICACIONES_RIESGO = ("I", "IIA", "IIB", "III")
CRITICIDADES = ("baja", "media", "alta")
FORMAS_ADQUISICION = ("compra", "donacion", "comodato")
# migración 0020 — 'sin_clasificar' es el valor de backfill del único manual
# que existía antes de esta fase (docs/25-...md sección 2.1).
TIPOS_MANUAL = (
    "manual_operacion",
    "manual_instalacion",
    "manual_servicio",
    "manual_partes",
    "sin_clasificar",
)
IDIOMAS_MANUAL = ("espanol", "ingles", "otro")


@dataclass
class Equipo:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
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
    # RF-EQ-01 — "fotografía". Guarda el object_key de MinIO, no una URL
    # resuelta (mismo criterio que `Laboratorio.logo_object_key`): la URL
    # real se firma bajo demanda y expira, así que persistir una URL
    # quedaría obsoleta. El nombre de la columna en base de datos
    # (`foto_url`, desde la migración 0002) no cambia para evitar una
    # migración de renombrado sin beneficio real — se mapea en el repositorio.
    foto_object_key: str | None
    manual_object_key: str | None
    # Fase 2 de hojas de vida — ficha técnica extendida (migración 0019).
    # Catálogos normalizados; `fabricante`/`proveedor` (texto, arriba) se
    # mantienen sin cambios, nunca se borran (docs/25-...md sección 2.1).
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
    eliminado_en: datetime | None
    creado_en: datetime
    actualizado_en: datetime

    def esta_activo(self) -> bool:
        return self.eliminado_en is None


@dataclass
class EquipoFichaTecnica:
    """1:1 con `Equipo` (PK = equipo_id) — datos técnicos variables de la
    ficha (docs/25-...md sección 2, migración 0019). Todos los campos son
    `str | None` a propósito, incluso los que parecen numéricos (voltaje,
    RPM...): el formato físico acepta "N/A" en varios de ellos, y ningún
    campo técnico es obligatorio (docs/24-...md sección 3.8)."""

    equipo_id: uuid.UUID
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
    creado_en: datetime
    actualizado_en: datetime


@dataclass
class EquipoAccesorio:
    id: uuid.UUID
    equipo_id: uuid.UUID
    cantidad: int | None
    descripcion: str
    observaciones: str | None
    creado_en: datetime


@dataclass
class EquipoManual:
    id: uuid.UUID
    equipo_id: uuid.UUID
    tipo: str
    disponible: bool
    idioma: str | None
    object_key: str | None
    creado_en: datetime
    actualizado_en: datetime
