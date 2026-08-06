"""Formato de error estándar de la API. Ver docs/15-api-design.md sección 4."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

_logger = logging.getLogger(__name__)

# Códigos SQLSTATE de Postgres (estables entre drivers) — ver
# https://www.postgresql.org/docs/current/errcodes-appendix.html.
_SQLSTATE_VIOLACION_UNICIDAD = "23505"
_SQLSTATE_VIOLACION_CLAVE_FORANEA = "23503"


class ErrorDeDominio(Exception):
    """Excepción base para errores de reglas de negocio (docs/07-reglas-de-negocio.md)."""

    def __init__(self, codigo: str, mensaje: str, detalles: dict | None = None) -> None:
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles or {}
        super().__init__(mensaje)


class CredencialesInvalidas(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__("credenciales_invalidas", "Usuario o contraseña incorrectos.")


class CuentaBloqueada(ErrorDeDominio):
    def __init__(self, segundos_restantes: int) -> None:
        super().__init__(
            "cuenta_bloqueada",
            "Cuenta bloqueada temporalmente por demasiados intentos fallidos.",
            {"segundos_restantes": segundos_restantes},
        )


class TokenInvalido(ErrorDeDominio):
    def __init__(self, mensaje: str = "Token inválido o expirado.") -> None:
        super().__init__("token_invalido", mensaje)


class PermisoInsuficiente(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__("permiso_insuficiente", "No tienes permiso para realizar esta acción.")


class DebeCambiarPasswordPendiente(ErrorDeDominio):
    """RF-USR-04 — bloquea cualquier endpoint protegido mientras el usuario
    no haya cambiado su contraseña temporal. Ver
    `auth/presentation/dependencies.py::get_usuario_actual`."""

    def __init__(self) -> None:
        super().__init__(
            "debe_cambiar_password_pendiente",
            "Debes cambiar tu contraseña temporal antes de continuar.",
        )


class RecursoNoEncontrado(ErrorDeDominio):
    """404 — genérico, reutilizable por cualquier módulo (docs/15-api-design.md)."""

    def __init__(self, codigo: str = "recurso_no_encontrado", mensaje: str = "El recurso no existe.") -> None:
        super().__init__(codigo, mensaje)


class ConflictoDeNegocio(ErrorDeDominio):
    """409 — violación de una regla de negocio por conflicto (p. ej. código
    duplicado, edición concurrente). Distinto de 422: el dato en sí es
    válido, el conflicto es con el estado actual del sistema."""

    def __init__(self, codigo: str, mensaje: str, detalles: dict | None = None) -> None:
        super().__init__(codigo, mensaje, detalles)


def _envelope(codigo: str, mensaje: str, detalles: dict | None = None) -> dict:
    return {"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or {}}}


def registrar_manejadores_de_error(app: FastAPI) -> None:
    @app.exception_handler(CredencialesInvalidas)
    async def _credenciales_invalidas(_: Request, exc: CredencialesInvalidas) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(CuentaBloqueada)
    async def _cuenta_bloqueada(_: Request, exc: CuentaBloqueada) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(TokenInvalido)
    async def _token_invalido(_: Request, exc: TokenInvalido) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(PermisoInsuficiente)
    async def _permiso_insuficiente(_: Request, exc: PermisoInsuficiente) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(DebeCambiarPasswordPendiente)
    async def _debe_cambiar_password_pendiente(_: Request, exc: DebeCambiarPasswordPendiente) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(RecursoNoEncontrado)
    async def _recurso_no_encontrado(_: Request, exc: RecursoNoEncontrado) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(ConflictoDeNegocio)
    async def _conflicto_de_negocio(_: Request, exc: ConflictoDeNegocio) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(IntegrityError)
    async def _violacion_de_integridad(_: Request, exc: IntegrityError) -> JSONResponse:
        """Backstop para violaciones de restricciones de la base de datos que
        no fueron detectadas antes por una verificación explícita de la capa
        de aplicación (p. ej. una condición de carrera entre el chequeo de
        unicidad y el `INSERT`, o una referencia — `categoria_id`, `area_id`,
        etc. — que el servicio no valida antes de guardar). Sin este
        handler, un `IntegrityError` sin capturar llega como 500 genérico;
        aquí se distingue el caso esperado (UNIQUE/FOREIGN KEY) de cualquier
        otro (CHECK, NOT NULL) para dar una respuesta consistente con el
        resto del contrato de error de la API, sin ocultar el detalle real
        en los logs del servidor."""
        codigo_sql = getattr(exc.orig, "pgcode", None)
        restriccion = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        detalles = {"restriccion": restriccion} if restriccion else {}

        if codigo_sql == _SQLSTATE_VIOLACION_UNICIDAD:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=_envelope("registro_duplicado", "Ya existe un registro con esos datos.", detalles),
            )
        if codigo_sql == _SQLSTATE_VIOLACION_CLAVE_FORANEA:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=_envelope(
                    "referencia_invalida",
                    "La operación hace referencia a un recurso que no existe.",
                    detalles,
                ),
            )
        # CHECK, NOT NULL u otra violación no clasificada — no se oculta (el
        # detalle real de Postgres queda en el log del servidor), pero
        # tampoco se expone el mensaje interno de SQL al cliente.
        _logger.exception("Violación de integridad de datos no clasificada.")
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_envelope(
                "violacion_de_integridad_de_datos",
                "La operación viola una restricción de la base de datos.",
            ),
        )

    @app.exception_handler(ErrorDeDominio)
    async def _error_de_dominio(_: Request, exc: ErrorDeDominio) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(exc.codigo, exc.mensaje, exc.detalles),
        )
