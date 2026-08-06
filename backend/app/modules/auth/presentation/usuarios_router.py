"""Endpoints de administración de Usuarios y Roles — RF-USR-01 a 07
(Sprint 10). Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db
from app.core.ip import ip_valida
from app.core.pagination import TAMANO_PAGINA_MAXIMO, TAMANO_PAGINA_POR_DEFECTO
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.application.usuario_service import (
    ActorContexto,
    DatosActualizarUsuario,
    DatosUsuario,
    UsuarioService,
)
from app.modules.auth.domain.entities import SesionActiva, Usuario
from app.modules.auth.infrastructure.repositories import (
    RolRepositorySQLAlchemy,
    SesionRepositorySQLAlchemy,
    UsuarioRepositorySQLAlchemy,
)
from app.modules.auth.presentation.dependencies import (
    UsuarioContexto,
    get_usuario_actual_sin_bloqueo,
    requiere_permiso,
)
from app.modules.auth.presentation.schemas import (
    ActualizarPerfilPropioRequest,
    ActualizarUsuarioRequest,
    AsignarRolesRequest,
    CambiarPasswordPropioRequest,
    CrearUsuarioRequest,
    PaginaUsuariosOut,
    RolOut,
    SesionOut,
    UrlFotoUsuarioOut,
    UrlFotoUsuarioRequest,
    UsuarioAdminOut,
)
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy

router = APIRouter(prefix="/api/v1", tags=["usuarios"])

_almacenamiento_fotos = AlmacenamientoMinIO(get_settings().minio_bucket_fotos_usuarios)


def _service(db: Session) -> UsuarioService:
    return UsuarioService(
        UsuarioRepositorySQLAlchemy(db),
        RolRepositorySQLAlchemy(db),
        SesionRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        ConfiguracionRepositorySQLAlchemy(db),
        _almacenamiento_fotos,
    )


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_out(usuario: Usuario, service: UsuarioService) -> UsuarioAdminOut:
    return UsuarioAdminOut(
        id=usuario.id,
        nombre_completo=usuario.nombre_completo,
        correo=usuario.correo,
        estado=usuario.estado,
        debe_cambiar_password=usuario.debe_cambiar_password,
        roles=usuario.roles,
        foto_url=service.url_foto(usuario),
        foto_object_key=usuario.foto_object_key,
    )


def _sesion_a_out(sesion: SesionActiva) -> SesionOut:
    return SesionOut(
        id=sesion.id,
        ip_origen=sesion.ip_origen,
        user_agent=sesion.user_agent,
        creado_en=sesion.creado_en,
        expira_en=sesion.expira_en,
    )


@router.get("/roles", response_model=list[RolOut])
def listar_roles(
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> list[RolOut]:
    roles = RolRepositorySQLAlchemy(db).listar()
    return [RolOut(id=r.id, nombre=r.nombre, es_sistema=r.es_sistema) for r in roles]


@router.get("/usuarios", response_model=PaginaUsuariosOut)
def listar_usuarios(
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=TAMANO_PAGINA_POR_DEFECTO, ge=1, le=TAMANO_PAGINA_MAXIMO),
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> PaginaUsuariosOut:
    service = _service(db)
    resultado = service.listar_paginado(pagina, tamano_pagina)
    return PaginaUsuariosOut(
        items=[_a_out(u, service) for u in resultado.items],
        total=resultado.total,
        pagina=resultado.pagina,
        tamano_pagina=resultado.tamano_pagina,
    )


@router.post("/usuarios", response_model=UsuarioAdminOut, status_code=201)
def crear_usuario(
    datos: CrearUsuarioRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> UsuarioAdminOut:
    service = _service(db)
    creado = service.crear(
        usuario.laboratorio_id,
        _actor(request, usuario),
        DatosUsuario(nombre_completo=datos.nombre_completo, correo=datos.correo, password=datos.password),
        datos.rol_ids,
    )
    db.commit()
    return _a_out(creado, service)


@router.post("/usuarios/me/upload-url/foto", response_model=UrlFotoUsuarioOut)
def solicitar_url_foto_perfil(
    datos: UrlFotoUsuarioRequest,
    db: Session = Depends(get_db),
    # `_sin_bloqueo` — igual criterio que `actualizar_mi_perfil`: subir una
    # foto no es el cambio de contraseña que RF-USR-04 exige, no hay razón
    # para bloquearlo mientras tanto.
    _usuario: UsuarioContexto = Depends(get_usuario_actual_sin_bloqueo),
) -> UrlFotoUsuarioOut:
    url, object_key = _service(db).solicitar_url_foto(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlFotoUsuarioOut(url_subida=url, object_key=object_key)


@router.patch("/usuarios/me", response_model=UsuarioAdminOut)
def actualizar_mi_perfil(
    datos: ActualizarPerfilPropioRequest,
    request: Request,
    db: Session = Depends(get_db),
    # `_sin_bloqueo` a propósito — RF-USR-04 fuerza el CAMBIO DE CONTRASEÑA,
    # no el resto de la cuenta: un usuario con contraseña temporal pendiente
    # sigue pudiendo corregir su nombre/correo (comportamiento ya cubierto
    # por test_configuracion_sprint12.py desde el Sprint 12).
    usuario: UsuarioContexto = Depends(get_usuario_actual_sin_bloqueo),
) -> UsuarioAdminOut:
    """RF-CFG-01 — cualquier usuario autenticado edita su propio perfil, sin
    requerir el permiso `usuarios.administrar` (ese es para editar a OTROS)."""
    service = _service(db)
    actualizado = service.actualizar_perfil_propio(
        usuario.id, _actor(request, usuario), datos.nombre_completo, datos.correo, datos.foto_object_key
    )
    db.commit()
    return _a_out(actualizado, service)


@router.post("/usuarios/me/cambiar-password", status_code=204, response_model=None)
def cambiar_mi_password(
    datos: CambiarPasswordPropioRequest,
    request: Request,
    db: Session = Depends(get_db),
    # `_sin_bloqueo` a propósito — RF-USR-04: este es precisamente el
    # endpoint que un usuario con contraseña pendiente de cambio debe poder
    # usar para salir de ese estado; bloquearlo aquí también dejaría al
    # usuario sin ninguna forma de continuar.
    usuario: UsuarioContexto = Depends(get_usuario_actual_sin_bloqueo),
) -> None:
    _service(db).cambiar_password_propio(
        usuario.id, _actor(request, usuario), datos.password_actual, datos.password_nueva
    )
    db.commit()


@router.get("/usuarios/{usuario_id}", response_model=UsuarioAdminOut)
def obtener_usuario(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> UsuarioAdminOut:
    service = _service(db)
    return _a_out(service.obtener(usuario_id), service)


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioAdminOut)
def actualizar_usuario(
    usuario_id: uuid.UUID,
    datos: ActualizarUsuarioRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> UsuarioAdminOut:
    service = _service(db)
    actualizado = service.actualizar(
        usuario_id, _actor(request, usuario), DatosActualizarUsuario(nombre_completo=datos.nombre_completo)
    )
    db.commit()
    return _a_out(actualizado, service)


@router.post("/usuarios/{usuario_id}/desactivar", response_model=UsuarioAdminOut)
def desactivar_usuario(
    usuario_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> UsuarioAdminOut:
    service = _service(db)
    actualizado = service.desactivar(usuario_id, _actor(request, usuario))
    db.commit()
    return _a_out(actualizado, service)


@router.post("/usuarios/{usuario_id}/activar", response_model=UsuarioAdminOut)
def activar_usuario(
    usuario_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> UsuarioAdminOut:
    service = _service(db)
    actualizado = service.activar(usuario_id, _actor(request, usuario))
    db.commit()
    return _a_out(actualizado, service)


@router.put("/usuarios/{usuario_id}/roles", response_model=UsuarioAdminOut)
def asignar_roles(
    usuario_id: uuid.UUID,
    datos: AsignarRolesRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> UsuarioAdminOut:
    service = _service(db)
    actualizado = service.asignar_roles(usuario_id, _actor(request, usuario), datos.rol_ids)
    db.commit()
    return _a_out(actualizado, service)


@router.get("/usuarios/{usuario_id}/sesiones", response_model=list[SesionOut])
def listar_sesiones(
    usuario_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> list[SesionOut]:
    return [_sesion_a_out(s) for s in _service(db).listar_sesiones(usuario_id)]


@router.delete("/usuarios/{usuario_id}/sesiones/{sesion_id}", status_code=204, response_model=None)
def cerrar_sesion(
    usuario_id: uuid.UUID,
    sesion_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("usuarios.administrar")),
) -> None:
    _service(db).cerrar_sesion(usuario_id, sesion_id, _actor(request, usuario))
    db.commit()
