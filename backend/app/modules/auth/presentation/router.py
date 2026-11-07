"""Endpoints de Autenticación. Ver docs/15-api-design.md sección 1.

Nota: a diferencia del resto del proyecto, este módulo NO usa
`from __future__ import annotations` — mismo motivo ya documentado en
`app/modules/qr/presentation/router.py`: slowapi (`@limiter.limit`, usado
aquí en `/login` y `/refresh`, RNF-SEG) envuelve el handler con un decorador
cuyo `__globals__` no incluye los símbolos de este archivo; con anotaciones
diferidas (strings), FastAPI no logra resolver `datos: LoginRequest` a la
clase real y lo trata como parámetro de query en vez de body."""

import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db, set_tenant_context
from app.core.errors import CredencialesInvalidas, ErrorDeDominio, TokenInvalido
from app.core.ip import ip_valida
from app.core.rate_limit import limiter
from app.modules.auth.application.auth_service import AuthService, ResultadoLogin
from app.modules.auth.domain.entities import Usuario
from app.modules.auth.infrastructure.repositories import (
    LaboratorioRepositorySQLAlchemy,
    SesionRepositorySQLAlchemy,
    UsuarioRepositorySQLAlchemy,
)
from app.modules.auth.presentation.dependencies import UsuarioContexto, get_usuario_actual_sin_bloqueo
from app.modules.auth.presentation.schemas import LoginRequest, LoginResponse, UsuarioOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_COOKIE_REFRESH = "refresh_token"
_almacenamiento_fotos = AlmacenamientoMinIO(get_settings().minio_bucket_fotos_usuarios)


def _resolver_foto(usuario: Usuario) -> str | None:
    if usuario.foto_object_key is None:
        return None
    return _almacenamiento_fotos.url_vista_previa(usuario.foto_object_key)


def _construir_service(db: Session) -> AuthService:
    return AuthService(
        usuarios=UsuarioRepositorySQLAlchemy(db),
        sesiones=SesionRepositorySQLAlchemy(db),
        laboratorios=LaboratorioRepositorySQLAlchemy(db),
    )


def _set_cookie_refresh(response: Response, refresh_token: str, dias: int) -> None:
    # `secure=True` es obligatorio en producción (docs/16-seguridad.md) —
    # un navegador (y el cliente de pruebas) descarta cookies "Secure" en
    # conexiones HTTP simples, que es como corren desarrollo y CI.
    settings = get_settings()
    response.set_cookie(
        key=_COOKIE_REFRESH,
        value=refresh_token,
        httponly=True,
        secure=settings.entorno == "produccion",
        samesite="strict",
        max_age=dias * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def _a_respuesta(resultado: ResultadoLogin) -> LoginResponse:
    return LoginResponse(
        access_token=resultado.access_token,
        expira_en=resultado.expira_en_segundos,
        usuario=UsuarioOut(
            id=resultado.usuario.id,
            nombre_completo=resultado.usuario.nombre_completo,
            correo=resultado.usuario.correo,
            roles=resultado.usuario.roles,
            debe_cambiar_password=resultado.usuario.debe_cambiar_password,
            foto_url=_resolver_foto(resultado.usuario),
            foto_object_key=resultado.usuario.foto_object_key,
        ),
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(lambda: get_settings().rate_limit_login)
def login(
    datos: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> LoginResponse:
    laboratorios = LaboratorioRepositorySQLAlchemy(db)
    laboratorio_id = laboratorios.resolver_id_por_slug(datos.laboratorio_slug)
    if laboratorio_id is None:
        raise CredencialesInvalidas()

    set_tenant_context(db, laboratorio_id)
    service = _construir_service(db)

    try:
        resultado = service.login(
            laboratorio_id=laboratorio_id,
            correo=datos.correo,
            password=datos.password,
            recordarme=datos.recordarme,
            ip_origen=ip_valida(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
        )
    except ErrorDeDominio:
        # Un login fallido también tiene efectos que deben persistir (el
        # contador de intentos fallidos y, eventualmente, el bloqueo
        # progresivo — RF-AUTH-06). Si no se hace commit aquí, `db.close()`
        # revierte esos cambios silenciosamente y el bloqueo nunca se activa
        # — ver tests/test_auth_flow.py::test_bloqueo_progresivo_tras_intentos_fallidos.
        db.commit()
        raise

    db.commit()

    _set_cookie_refresh(response, resultado.refresh_token, resultado.duracion_dias_cookie)
    return _a_respuesta(resultado)


@router.post("/refresh", response_model=LoginResponse)
@limiter.limit(lambda: get_settings().rate_limit_refresh)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    token_actual = request.cookies.get(_COOKIE_REFRESH)
    if not token_actual:
        raise TokenInvalido("No se encontró una sesión activa.")

    # El laboratorio se deriva del propio JWT de refresh (firmado), no de un
    # parámetro de la petición — ver nota en app/core/security.py.
    import jwt as pyjwt

    from app.core.security import decodificar_refresh_token

    try:
        claims = decodificar_refresh_token(token_actual)
    except pyjwt.PyJWTError as exc:
        raise TokenInvalido() from exc

    set_tenant_context(db, uuid.UUID(claims["laboratorio_id"]))
    service = _construir_service(db)

    try:
        resultado = service.refresh(
            refresh_token_plano=token_actual,
            ip_origen=ip_valida(request.client.host if request.client else None),
            user_agent=request.headers.get("user-agent"),
        )
    except ErrorDeDominio:
        # Igual que en login (ver comentario arriba): si se detecta un
        # reuso fuera de la ventana de gracia, `AuthService.refresh` ya
        # llamó a `revocar_todas_de_usuario` antes de lanzar `TokenInvalido`
        # — sin este commit, `db.close()` revertía esa revocación en
        # silencio y la defensa contra robo de token nunca persistía.
        db.commit()
        raise

    db.commit()

    _set_cookie_refresh(response, resultado.refresh_token, resultado.duracion_dias_cookie)
    return _a_respuesta(resultado)


@router.post("/logout", status_code=204, response_model=None)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    token_actual = request.cookies.get(_COOKIE_REFRESH)
    if token_actual:
        import jwt as pyjwt

        from app.core.security import decodificar_refresh_token

        try:
            claims = decodificar_refresh_token(token_actual)
            set_tenant_context(db, uuid.UUID(claims["laboratorio_id"]))
            _construir_service(db).logout(token_actual)
            db.commit()
        except pyjwt.PyJWTError:
            pass  # token ya inválido — no hay nada que revocar

    response.delete_cookie(_COOKIE_REFRESH, path="/api/v1/auth")


@router.get("/me", response_model=UsuarioOut)
def me(
    # `_sin_bloqueo` a propósito — RF-USR-04: un usuario con contraseña
    # pendiente de cambio necesita seguir pudiendo consultar quién es (para
    # que el frontend sepa que debe redirigirlo a cambiarla).
    usuario_ctx: UsuarioContexto = Depends(get_usuario_actual_sin_bloqueo),
    db: Session = Depends(get_db),
) -> UsuarioOut:
    usuario = UsuarioRepositorySQLAlchemy(db).obtener_por_id(usuario_ctx.id)
    if usuario is None:
        raise TokenInvalido()
    return UsuarioOut(
        id=usuario.id,
        nombre_completo=usuario.nombre_completo,
        correo=usuario.correo,
        roles=usuario.roles,
        debe_cambiar_password=usuario.debe_cambiar_password,
        foto_url=_resolver_foto(usuario),
        foto_object_key=usuario.foto_object_key,
    )
