"""Modelo SQLAlchemy de Calibraciones. Ver docs/14-base-de-datos.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Calibracion(Base):
    __tablename__ = "calibraciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    equipo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("equipos.id"), nullable=False)
    fecha_calibracion: Mapped[date] = mapped_column(Date, nullable=False)
    frecuencia_meses: Mapped[int] = mapped_column(Integer, nullable=False)
    proxima_fecha: Mapped[date] = mapped_column(Date, nullable=False)
    laboratorio_proveedor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    numero_certificado: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resultado: Mapped[str] = mapped_column(String(20), nullable=False)
    incertidumbre: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    certificado_adjunto_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("adjuntos.id"), nullable=True
    )
    corrige_a_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calibraciones.id"), nullable=True
    )
    motivo_correccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
