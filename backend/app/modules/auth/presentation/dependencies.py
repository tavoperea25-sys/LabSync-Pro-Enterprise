"""Dependencies de FastAPI reutilizables por CUALQUIER módulo protegido, no solo Auth.

`get_usuario_actual` es el punto único donde: (1) se valida el JWT de acceso,
(2) se deriva `laboratorio_id` del token — nunca de la petición — y (3) se
fija el contexto de tenant en la sesión de base de datos antes de que el
router ejecute cualquier query. Ver docs/13-arquitectura.md sección 4.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass

import jwt as pyjwt
from fastapi import Depends, Header
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db, set_tenant_context
from app.core.errors import DebeCambiarPasswordPendiente, PermisoInsuficiente, TokenInvalido
from app.core.security import decodificar_access_token
from app.modules.auth.infrastructure.models import Permiso, Rol, RolPermiso


@dataclass
class UsuarioContexto:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    roles: list[str]
    debe_cambiar_password: bool = False


def _usuario_desde_token(authorization: str | None, db: Session) -> UsuarioContexto:
    if not authorization or not authorization.startswith("Bearer "):
        raise TokenInvalido("Cabecera Authorization ausente o mal formada.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = decodificar_access_token(token)
    except pyjwt.PyJWTError as exc:
        raise TokenInvalido() from exc

    laboratorio_id = uuid.UUID(claims["laboratorio_id"])
    set_tenant_context(db, laboratorio_id)

    return UsuarioContexto(
        id=uuid.UUID(claims["sub"]),
        laboratorio_id=laboratorio_id,
        roles=list(claims.get("roles", [])),
        debe_cambiar_password=bool(claims.get("debe_cambiar_password", False)),
    )


def get_usuario_actual(
    authorization: str | None = Header(default=None, description="Bearer <access_token>"),
    db: Session = Depends(get_db),
) -> UsuarioContexto:
    """RF-USR-04 — bloquea CUALQUIER endpoint que dependa de esta función
    (incluido, transitivamente, todo lo que pasa por `requiere_permiso`)
    mientras el usuario tenga una contraseña temporal pendiente de cambiar.
    Los únicos dos endpoints que un usuario en ese estado todavía necesita
    usar (`GET /auth/me` y `POST /usuarios/me/cambiar-password`) usan
    `get_usuario_actual_sin_bloqueo` en su lugar — ver ese endpoint."""
    usuario = _usuario_desde_token(authorization, db)
    if usuario.debe_cambiar_password:
        raise DebeCambiarPasswordPendiente()
    return usuario


def get_usuario_actual_sin_bloqueo(
    authorization: str | None = Header(default=None, description="Bearer <access_token>"),
    db: Session = Depends(get_db),
) -> UsuarioContexto:
    """Variante de `get_usuario_actual` que NO bloquea por
    `debe_cambiar_password` — exclusiva de los endpoints que un usuario con
    contraseña pendiente todavía debe poder usar para salir de ese estado."""
    return _usuario_desde_token(authorization, db)


def tiene_permiso(db: Session, roles: list[str], clave_permiso: str) -> bool:
    """Verificación puntual contra la matriz roles→permisos, reutilizable
    fuera de una dependency de FastAPI — ver `busqueda/presentation/router.py`,
    que la usa para filtrar resultados por categoría (RF-SEARCH-05) en vez
    de bloquear todo el endpoint con un único permiso."""
    if not roles:
        return False
    stmt = (
        select(func.count())
        .select_from(Rol)
        .join(RolPermiso, RolPermiso.rol_id == Rol.id)
        .join(Permiso, Permiso.id == RolPermiso.permiso_id)
        .where(Rol.nombre.in_(roles), Permiso.clave == clave_permiso)
    )
    return db.execute(stmt).scalar_one() > 0


def requiere_permiso(clave_permiso: str) -> Callable[..., UsuarioContexto]:
    """Factory de dependency para autorización granular (docs/16-seguridad.md
    sección 2). Verifica `clave_permiso` contra la matriz real
    roles→permisos (docs/14-base-de-datos.md) — nunca contra el nombre del
    rol directamente, para que la matriz pueda ajustarse (Sprint 12,
    RF-CFG) sin tocar cada endpoint que la usa."""

    def _dependencia(
        usuario: UsuarioContexto = Depends(get_usuario_actual), db: Session = Depends(get_db)
    ) -> UsuarioContexto:
        if not tiene_permiso(db, usuario.roles, clave_permiso):
            raise PermisoInsuficiente()
        return usuario

    return _dependencia
