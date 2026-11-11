"""Modelos SQLAlchemy del módulo Equipos. Ver docs/14-base-de-datos.md."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


class Proveedor(Base):
    """Fase 2 de hojas de vida (docs/25-...md sección 2, migración 0018).
    `UNIQUE(id, laboratorio_id)` y el índice único funcional por nombre
    normalizado viven solo en la migración (no se declaran aquí como
    `UniqueConstraint` de SQLAlchemy porque el segundo es una expresión
    `lower(trim(...))`, no una columna)."""

    __tablename__ = "proveedores"

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    pais_ciudad: Mapped[str | None] = mapped_column(String(150), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contacto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )


class Fabricante(Base):
    """Mismo diseño que `Proveedor` — ver su docstring."""

    __tablename__ = "fabricantes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    pais_ciudad: Mapped[str | None] = mapped_column(String(150), nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contacto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )


class Equipo(Base):
    __tablename__ = "equipos"
    __table_args__ = (
        UniqueConstraint("laboratorio_id", "codigo_interno", name="uq_equipos_lab_codigo"),
        UniqueConstraint("id", "laboratorio_id", name="uq_equipos_id_laboratorio"),
        # FK compuestas (no simples): Postgres evalúa las FK sin pasar por
        # RLS, así que una FK simple permitiría vincular un proveedor o
        # fabricante de OTRO laboratorio. `ondelete="RESTRICT"` explícito —
        # nunca `SET NULL` sin lista de columnas, porque anularía también
        # `laboratorio_id` (docs/25-...md, ajuste pedido por Gustavo).
        ForeignKeyConstraint(
            ["proveedor_id", "laboratorio_id"],
            ["proveedores.id", "proveedores.laboratorio_id"],
            name="fk_equipos_proveedor_lab",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["fabricante_id", "laboratorio_id"],
            ["fabricantes.id", "fabricantes.laboratorio_id"],
            name="fk_equipos_fabricante_lab",
            ondelete="RESTRICT",
        ),
    )

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
    # Fase 2 de hojas de vida (docs/25-...md sección 2, migraciones 0018/0019).
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    fabricante_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    capitulo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grupo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    subgrupo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    numero_inventario: Mapped[str | None] = mapped_column(String(100), nullable=True)
    condicion_fisica: Mapped[str | None] = mapped_column(String(20), nullable=True)
    clasificacion_riesgo: Mapped[str | None] = mapped_column(String(10), nullable=True)
    criticidad: Mapped[str | None] = mapped_column(String(20), nullable=True)
    forma_adquisicion: Mapped[str | None] = mapped_column(String(20), nullable=True)
    garantia: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    garantia_inicio: Mapped[date | None] = mapped_column(Date, nullable=True)
    garantia_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    eliminado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )


class EquipoFichaTecnica(Base):
    """1:1 con `Equipo` — PK = `equipo_id` (docs/25-...md sección 2,
    migración 0019). Todos los campos técnicos son `Text` nullable — ver el
    docstring de la entidad de dominio homónima para el porqué."""

    __tablename__ = "equipo_ficha_tecnica"
    __table_args__ = (
        ForeignKeyConstraint(
            ["equipo_id", "laboratorio_id"],
            ["equipos.id", "equipos.laboratorio_id"],
            name="fk_equipo_ficha_tecnica_equipo_lab",
            ondelete="RESTRICT",
        ),
    )

    equipo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    voltaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    corriente: Mapped[str | None] = mapped_column(Text, nullable=True)
    frecuencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    corriente_ma: Mapped[str | None] = mapped_column(Text, nullable=True)
    variable_medicion: Mapped[str | None] = mapped_column(Text, nullable=True)
    rango_medicion: Mapped[str | None] = mapped_column(Text, nullable=True)
    rpm: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperatura_trabajo: Mapped[str | None] = mapped_column(Text, nullable=True)
    humedad_trabajo: Mapped[str | None] = mapped_column(Text, nullable=True)
    peso: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensiones: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_puertas: Mapped[str | None] = mapped_column(Text, nullable=True)
    clase_sistema: Mapped[str | None] = mapped_column(Text, nullable=True)
    alimentacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    uso: Mapped[str | None] = mapped_column(Text, nullable=True)
    uso_especifico: Mapped[str | None] = mapped_column(Text, nullable=True)
    condiciones_ambientales: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_adicionales: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )


class EquipoAccesorio(Base):
    __tablename__ = "equipo_accesorios"
    __table_args__ = (
        ForeignKeyConstraint(
            ["equipo_id", "laboratorio_id"],
            ["equipos.id", "equipos.laboratorio_id"],
            name="fk_equipo_accesorios_equipo_lab",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    equipo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cantidad: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class EquipoManual(Base):
    __tablename__ = "equipo_manuales"
    __table_args__ = (
        UniqueConstraint("equipo_id", "tipo", name="uq_equipo_manuales_equipo_tipo"),
        ForeignKeyConstraint(
            ["equipo_id", "laboratorio_id"],
            ["equipos.id", "equipos.laboratorio_id"],
            name="fk_equipo_manuales_equipo_lab",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    equipo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    disponible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idioma: Mapped[str | None] = mapped_column(String(20), nullable=True)
    object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate=datetime.utcnow
    )
