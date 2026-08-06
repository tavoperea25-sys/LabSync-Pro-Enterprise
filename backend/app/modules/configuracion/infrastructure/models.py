"""Modelo SQLAlchemy de Configuración. Ver docs/14-base-de-datos.md."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ConfiguracionLaboratorio(Base):
    __tablename__ = "configuraciones_laboratorio"

    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), primary_key=True
    )
    umbral_alerta_calibracion_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    umbral_alerta_mantenimiento_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    umbral_alerta_documento_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    dias_retencion_papelera_documentos: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    politica_password_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    mapeo_estados_mantenimiento_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
