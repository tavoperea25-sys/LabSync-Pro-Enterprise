"""Entidades del módulo Mantenimientos. Ver docs/14-base-de-datos.md y
docs/03-requerimientos-funcionales.md (RF-MANT-01 a RF-MANT-05 — Sprint 8)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

TIPOS_MANTENIMIENTO = ("preventivo", "correctivo", "predictivo", "calibracion_correctiva")
ESTADOS_MANTENIMIENTO = ("programado", "en_ejecucion", "completado", "cancelado")

# RN-MANT-01 — "configurable por tipo" (docs/07-reglas-de-negocio.md).
# Asignación por defecto (RF-CFG-03, módulo Configuración, Sprint 12/14):
# correctivo/calibración correctiva es el equipo REALMENTE caído ("fuera de
# servicio"), preventivo/predictivo es una intervención programada con el
# equipo aún parcialmente disponible ("en mantenimiento") — el Administrador
# puede sobrescribir esta asignación por laboratorio vía
# `configuraciones_laboratorio.mapeo_estados_mantenimiento_json`.
ESTADOS_OPERATIVOS_ABIERTOS = frozenset({"programado", "en_ejecucion"})
ESTADOS_OPERATIVOS_RESULTANTES = ("fuera_de_servicio", "en_mantenimiento")

_MAPEO_POR_DEFECTO: dict[str, str] = {
    "correctivo": "fuera_de_servicio",
    "calibracion_correctiva": "fuera_de_servicio",
    "preventivo": "en_mantenimiento",
    "predictivo": "en_mantenimiento",
}


def estado_operativo_para_tipo(tipo: str, mapeo: dict[str, str] | None = None) -> str:
    """`mapeo` es la configuración del laboratorio (puede venir incompleta o
    None) — cualquier tipo ausente en `mapeo` cae al valor por defecto, así
    un Administrador puede sobrescribir solo el tipo que le interesa."""
    if mapeo and tipo in mapeo:
        return mapeo[tipo]
    return _MAPEO_POR_DEFECTO.get(tipo, "en_mantenimiento")


@dataclass
class Mantenimiento:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
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
    informe_adjunto_id: uuid.UUID | None
    frecuencia_meses: int | None
    generado_de_id: uuid.UUID | None
    creado_en: datetime
    actualizado_en: datetime

    def esta_abierto(self) -> bool:
        return self.estado in ESTADOS_OPERATIVOS_ABIERTOS
