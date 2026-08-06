"""Modelo SQLAlchemy de auditoría. Ver docs/14-base-de-datos.md.

No expone `onupdate` ni se usa desde ningún `UPDATE`/`DELETE` en el código
de aplicación — coherente con los GRANT de la migración 0003, que ya lo
impiden a nivel de base de datos (defensa en profundidad, RN-AUD-01)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    ip_origen: Mapped[str | None] = mapped_column(INET, nullable=True)
    modulo: Mapped[str] = mapped_column(String(50), nullable=False)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    entidad_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    valor_anterior: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    valor_nuevo: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(server_default="now()")
