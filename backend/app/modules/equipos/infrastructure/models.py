"""Modelos SQLAlchemy del módulo Equipos. Ver docs/14-base-de-datos.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class CategoriaEquipo(Base):
    __tablename__ = "categorias_equipo"
    __table_args__ = (UniqueConstraint("laboratorio_id", "nombre", name="uq_categorias_lab_nombre"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    frecuencia_calibracion_default_meses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # RN-EQ-03 — si es True, un equipo de esta categoría no puede pasar a
    # "operativo" mientras su última calibración esté vencida.
    bloquea_activacion_si_calibracion_vencida: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class Area(Base):
    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("laboratorio_id", "nombre", name="uq_areas_lab_nombre"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)


class Equipo(Base):
    __tablename__ = "equipos"
    __table_args__ = (UniqueConstraint("laboratorio_id", "codigo_interno", name="uq_equipos_lab_codigo"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    codigo_interno: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categorias_equipo.id"), nullable=True
    )
    marca: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    numero_serie: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fabricante: Mapped[str | None] = mapped_column(String(150), nullable=True)
    proveedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    fecha_adquisicion: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado_operativo: Mapped[str] = mapped_column(String(30), nullable=False, default="operativo")
    area_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas.id"), nullable=True
    )
    responsable_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True
    )
    foto_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # RF-EQ-01 — "manual de usuario (archivo)". Mismo criterio que foto_url:
    # se guarda el object_key de MinIO, no una URL resuelta.
    manual_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )
