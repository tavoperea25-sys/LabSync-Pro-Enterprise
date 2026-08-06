"""Modelo SQLAlchemy de Mantenimientos. Ver docs/14-base-de-datos.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Mantenimiento(Base):
    __tablename__ = "mantenimientos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    equipo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipos.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="programado")
    fecha_programada: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_ejecutada: Mapped[date | None] = mapped_column(Date, nullable=True)
    tecnico_responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    repuestos_utilizados: Mapped[str | None] = mapped_column(Text, nullable=True)
    tiempo_inactividad_horas: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    costo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    informe_adjunto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("adjuntos.id"), nullable=True
    )
    frecuencia_meses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generado_de_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mantenimientos.id"), nullable=True
    )
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )
