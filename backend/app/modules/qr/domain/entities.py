"""Entidades de dominio del módulo QR. Ver docs/03-requerimientos-funcionales.md
Módulo 13 y docs/07-reglas-de-negocio.md (RN-QR-*)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

ESTADOS_INCIDENCIA = ("pendiente", "en_revision", "resuelta")


@dataclass
class QrToken:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    equipo_id: uuid.UUID
    token: str
    revocado: bool


@dataclass
class IncidenciaQr:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    equipo_id: uuid.UUID
    descripcion: str
    contacto_nombre: str | None
    contacto_medio: str | None
    estado: str
    creado_en: datetime


@dataclass
class IncidenciaQrConEquipo:
    """RF-QR-03 — 'visible luego en el módulo de Mantenimientos como
    solicitud pendiente de triage': la incidencia enriquecida con los
    campos del equipo que la lista de triage necesita mostrar, sin obligar
    al llamador a resolver cada equipo por separado."""

    id: uuid.UUID
    equipo_id: uuid.UUID
    equipo_codigo_interno: str
    equipo_nombre: str
    descripcion: str
    contacto_nombre: str | None
    contacto_medio: str | None
    estado: str
    creado_en: datetime
