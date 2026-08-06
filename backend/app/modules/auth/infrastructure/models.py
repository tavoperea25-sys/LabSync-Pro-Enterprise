"""Modelos SQLAlchemy — el único lugar que conoce el esquema real de Postgres.

Corresponde a docs/14-base-de-datos.md. Nota de implementación: se añaden
`intentos_fallidos` y `bloqueado_hasta` en `usuarios`, no listados
explícitamente en el ERD del blueprint, como soporte necesario de RF-AUTH-06
(bloqueo progresivo) — extensión menor y consistente con el resto del modelo.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Laboratorio(Base):
    __tablename__ = "laboratorios"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    logo_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    es_sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    permisos: Mapped[list[Permiso]] = relationship(
        secondary="roles_permisos", back_populates="roles"
    )


class Permiso(Base):
    __tablename__ = "permisos"

    id: Mapped[uuid.UUID] = _uuid_pk()
    clave: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    roles: Mapped[list[Rol]] = relationship(secondary="roles_permisos", back_populates="permisos")


class RolPermiso(Base):
    __tablename__ = "roles_permisos"

    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True
    )
    permiso_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permisos.id"), primary_key=True
    )


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (UniqueConstraint("laboratorio_id", "correo", name="uq_usuarios_lab_correo"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    correo: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nombre_completo: Mapped[str] = mapped_column(String(200), nullable=False)
    # RF-CFG-01 — mismo patrón que `Laboratorio.logo_object_key`: se guarda
    # el object_key de MinIO, la URL prefirmada se resuelve bajo demanda.
    foto_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="pendiente_activacion")
    debe_cambiar_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mfa_habilitado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_login_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    roles: Mapped[list[Rol]] = relationship(secondary="usuarios_roles")


class UsuarioRol(Base):
    __tablename__ = "usuarios_roles"

    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), primary_key=True
    )
    rol_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True
    )
    # Denormalizado deliberadamente para permitir una política RLS directa
    # sin JOIN (ver docs/14-base-de-datos.md nota de implementación).
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )


class Sesion(Base):
    __tablename__ = "sesiones"

    id: Mapped[uuid.UUID] = _uuid_pk()
    laboratorio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("laboratorios.id"), nullable=False
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ip_origen: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
