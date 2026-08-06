"""Entidades del módulo Calendario. Ver docs/03-requerimientos-funcionales.md
(RF-CAL2-01 a 05 — Sprint 9)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

# Tipos que un usuario crea a mano (RF-CAL2-03). Los demás valores del ENUM
# lógico (docs/14-base-de-datos.md) — 'calibracion', 'mantenimiento',
# 'vencimiento_documental' — se sintetizan en `CalendarioService`, nunca se
# insertan como fila de `eventos_calendario` (ver docstring de la migración
# 0008 para el razonamiento completo).
TIPOS_EVENTO_MANUAL = ("auditoria", "capacitacion", "institucional")
TIPOS_EVENTO_SINTETIZADO = ("calibracion", "mantenimiento", "vencimiento_documental")
TIPOS_EVENTO = TIPOS_EVENTO_MANUAL + TIPOS_EVENTO_SINTETIZADO


@dataclass
class EventoCalendario:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    tipo: str
    titulo: str
    descripcion: str | None
    fecha: datetime
    origen_tipo: str | None
    origen_id: uuid.UUID | None
    creado_por_id: uuid.UUID | None
    creado_en: datetime
    actualizado_en: datetime

    def es_manual(self) -> bool:
        return self.tipo in TIPOS_EVENTO_MANUAL
