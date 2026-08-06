"""Entidades de dominio del módulo Equipos. Ver docs/03-requerimientos-funcionales.md
Módulo 3 y docs/07-reglas-de-negocio.md (RN-EQ-*)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

ESTADOS_OPERATIVOS = ("operativo", "fuera_de_servicio", "en_mantenimiento", "de_baja")


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
    eliminado_en: datetime | None
    creado_en: datetime
    actualizado_en: datetime

    def esta_activo(self) -> bool:
        return self.eliminado_en is None
