"""Entidades de dominio del módulo Auth — sin dependencia de FastAPI ni SQLAlchemy.

Ver docs/13-arquitectura.md sección 2 (el dominio depende de puertos, no de
infraestructura) y docs/07-reglas-de-negocio.md (RN-USR-*).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Usuario:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    correo: str
    password_hash: str
    nombre_completo: str
    estado: str  # 'activo' | 'inactivo' | 'pendiente_activacion'
    debe_cambiar_password: bool
    intentos_fallidos: int
    bloqueado_hasta: datetime | None
    roles: list[str] = field(default_factory=list)
    foto_object_key: str | None = None

    def esta_activo(self) -> bool:
        return self.estado == "activo"

    def esta_bloqueado(self, ahora: datetime) -> bool:
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > ahora


@dataclass
class SesionActiva:
    id: uuid.UUID
    usuario_id: uuid.UUID
    laboratorio_id: uuid.UUID
    refresh_token_hash: str
    expira_en: datetime
    revocada: bool
    ip_origen: str | None
    user_agent: str | None
    creado_en: datetime


@dataclass
class Rol:
    id: uuid.UUID
    nombre: str
    es_sistema: bool


@dataclass
class Laboratorio:
    id: uuid.UUID
    nombre: str
    slug: str
    logo_object_key: str | None
