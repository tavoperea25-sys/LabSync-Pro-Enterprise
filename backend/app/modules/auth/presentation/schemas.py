"""DTOs de la API — nunca se exponen los modelos SQLAlchemy directamente.
Ver docs/15-api-design.md sección 1."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    laboratorio_slug: str = Field(..., description="Identificador corto del laboratorio (tenant).")
    correo: EmailStr
    password: str
    recordarme: bool = False


class UsuarioOut(BaseModel):
    id: uuid.UUID
    nombre_completo: str
    correo: str
    roles: list[str]
    debe_cambiar_password: bool
    foto_url: str | None
    # object_key estable (no expira) — mismo criterio que
    # `InstitucionOut.logo_object_key`: el frontend lo necesita para poder
    # "no tocar la foto actual" al reenviar un PATCH de otro campo.
    foto_object_key: str | None


class LoginResponse(BaseModel):
    access_token: str
    expira_en: int
    usuario: UsuarioOut


# ---- Administración de usuarios (Sprint 10, RF-USR-*) ----------------------


class RolOut(BaseModel):
    id: uuid.UUID
    nombre: str
    es_sistema: bool


class UsuarioAdminOut(BaseModel):
    id: uuid.UUID
    nombre_completo: str
    correo: str
    estado: str
    debe_cambiar_password: bool
    roles: list[str]
    foto_url: str | None
    foto_object_key: str | None


class PaginaUsuariosOut(BaseModel):
    items: list[UsuarioAdminOut]
    total: int
    pagina: int
    tamano_pagina: int


class CrearUsuarioRequest(BaseModel):
    nombre_completo: str = Field(..., min_length=1, max_length=200)
    correo: EmailStr
    password: str = Field(..., min_length=1)
    rol_ids: list[uuid.UUID] = Field(..., min_length=1)


class ActualizarUsuarioRequest(BaseModel):
    nombre_completo: str = Field(..., min_length=1, max_length=200)


class ActualizarPerfilPropioRequest(BaseModel):
    nombre_completo: str = Field(..., min_length=1, max_length=200)
    correo: EmailStr
    foto_object_key: str | None = None


class UrlFotoUsuarioRequest(BaseModel):
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    tipo_mime: str = Field(..., min_length=1, max_length=100)
    tamano_bytes: int = Field(..., gt=0)


class UrlFotoUsuarioOut(BaseModel):
    url_subida: str
    object_key: str


class CambiarPasswordPropioRequest(BaseModel):
    password_actual: str = Field(..., min_length=1)
    password_nueva: str = Field(..., min_length=1)


class AsignarRolesRequest(BaseModel):
    rol_ids: list[uuid.UUID] = Field(..., min_length=1)


class SesionOut(BaseModel):
    id: uuid.UUID
    ip_origen: str | None
    user_agent: str | None
    creado_en: datetime
    expira_en: datetime
