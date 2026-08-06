"""Modelos SQLAlchemy del módulo QR. Ver docs/14-base-de-datos.md y la nota
de RLS en alembic/versions/0004_qr.py."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class QrToken(Base):
    __tablename__ = "qr_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    equipo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipos.id"), nullable=False, unique=True
    )
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    revocado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creado_en: Mapped[datetime] = mapped_column(server_default="now()")


class IncidenciaQr(Base):
    __tablename__ = "incidencias_qr"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    equipo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipos.id"), nullable=False
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    contacto_nombre: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contacto_medio: Mapped[str | None] = mapped_column(String(150), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(server_default="now()")
