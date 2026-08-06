"""Casos de uso del módulo Auth. Ver docs/03-requerimientos-funcionales.md Módulo 1
y docs/07-reglas-de-negocio.md.

Esta capa no conoce FastAPI ni SQLAlchemy directamente — solo los puertos de
domain/ports.py, inyectados por la capa de presentación.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt as pyjwt

from app.core.config import get_settings
from app.core.errors import CredencialesInvalidas, CuentaBloqueada, TokenInvalido
from app.core.security import (
    crear_access_token,
    crear_refresh_token,
    decodificar_refresh_token,
    hash_password,
    verificar_password,
)
from app.modules.auth.domain.entities import Usuario
from app.modules.auth.domain.ports import LaboratorioRepository, SesionRepository, UsuarioRepository

_UMBRAL_INTENTOS_FALLIDOS = 5
_BLOQUEO_BASE_SEGUNDOS = 60


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()


@dataclass
class ResultadoLogin:
    access_token: str
    refresh_token: str
    expira_en_segundos: int
    usuario: Usuario


class AuthService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        sesiones: SesionRepository,
        laboratorios: LaboratorioRepository,
    ) -> None:
        self._usuarios = usuarios
        self._sesiones = sesiones
        self._laboratorios = laboratorios
        self._settings = get_settings()

    def login(
        self,
        laboratorio_id: uuid.UUID,
        correo: str,
        password: str,
        ip_origen: str | None,
        user_agent: str | None,
    ) -> ResultadoLogin:
        if not self._laboratorios.existe_activo(laboratorio_id):
            # Mismo error genérico que credenciales inválidas — no revela
            # si el laboratorio existe (mitiga enumeración, docs/16-seguridad.md).
            raise CredencialesInvalidas()

        usuario = self._usuarios.buscar_por_correo(laboratorio_id, correo)
        if usuario is None:
            raise CredencialesInvalidas()

        ahora = datetime.now(UTC)
        if usuario.bloqueado_hasta is not None and usuario.esta_bloqueado(ahora):
            segundos_restantes = int((usuario.bloqueado_hasta - ahora).total_seconds())
            raise CuentaBloqueada(segundos_restantes)

        if not usuario.esta_activo() or not verificar_password(password, usuario.password_hash):
            self._registrar_intento_fallido(usuario)
            raise CredencialesInvalidas()

        self._usuarios.resetear_intentos_fallidos(usuario.id)

        access_token = crear_access_token(
            usuario.id, usuario.laboratorio_id, usuario.roles, usuario.debe_cambiar_password
        )
        refresh_token, jti = crear_refresh_token(usuario.id, usuario.laboratorio_id)
        self._sesiones.crear(
            usuario_id=usuario.id,
            laboratorio_id=usuario.laboratorio_id,
            refresh_token_hash=_hash_jti(jti),
            expira_en=ahora + timedelta(days=self._settings.refresh_token_expira_dias),
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

        return ResultadoLogin(
            access_token=access_token,
            refresh_token=refresh_token,
            expira_en_segundos=self._settings.access_token_expira_minutos * 60,
            usuario=usuario,
        )

    def _registrar_intento_fallido(self, usuario: Usuario) -> None:
        nuevos_intentos = usuario.intentos_fallidos + 1
        bloqueado_hasta = None
        if nuevos_intentos >= _UMBRAL_INTENTOS_FALLIDOS:
            ciclos_de_bloqueo = nuevos_intentos - _UMBRAL_INTENTOS_FALLIDOS + 1
            segundos = _BLOQUEO_BASE_SEGUNDOS * (2 ** (ciclos_de_bloqueo - 1))
            bloqueado_hasta = datetime.now(UTC) + timedelta(seconds=segundos)
        self._usuarios.registrar_intento_fallido(usuario.id, bloqueado_hasta)

    def refresh(
        self, refresh_token_plano: str, ip_origen: str | None, user_agent: str | None
    ) -> ResultadoLogin:
        try:
            claims = decodificar_refresh_token(refresh_token_plano)
        except pyjwt.PyJWTError as exc:
            raise TokenInvalido() from exc

        sesion = self._sesiones.buscar_por_hash(_hash_jti(claims["jti"]))

        if sesion is None:
            raise TokenInvalido()

        if sesion.revocada:
            # Reuso de un refresh token ya rotado: indicio de robo — se
            # revocan TODAS las sesiones del usuario (docs/16-seguridad.md).
            self._sesiones.revocar_todas_de_usuario(sesion.usuario_id)
            raise TokenInvalido("Sesión comprometida — todas las sesiones fueron cerradas.")

        if sesion.expira_en < datetime.now(UTC):
            raise TokenInvalido("La sesión ha expirado.")

        usuario = self._usuarios.obtener_por_id(sesion.usuario_id)
        if usuario is None or not usuario.esta_activo():
            raise TokenInvalido()

        # Rotación: se revoca el token usado y se emite uno nuevo.
        self._sesiones.revocar(sesion.id)
        access_token = crear_access_token(
            usuario.id, usuario.laboratorio_id, usuario.roles, usuario.debe_cambiar_password
        )
        nuevo_refresh, nuevo_jti = crear_refresh_token(usuario.id, usuario.laboratorio_id)
        self._sesiones.crear(
            usuario_id=usuario.id,
            laboratorio_id=usuario.laboratorio_id,
            refresh_token_hash=_hash_jti(nuevo_jti),
            expira_en=datetime.now(UTC) + timedelta(days=self._settings.refresh_token_expira_dias),
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

        return ResultadoLogin(
            access_token=access_token,
            refresh_token=nuevo_refresh,
            expira_en_segundos=self._settings.access_token_expira_minutos * 60,
            usuario=usuario,
        )

    def logout(self, refresh_token_plano: str) -> None:
        try:
            claims = decodificar_refresh_token(refresh_token_plano)
        except pyjwt.PyJWTError:
            return
        sesion = self._sesiones.buscar_por_hash(_hash_jti(claims["jti"]))
        if sesion is not None:
            self._sesiones.revocar(sesion.id)


def crear_usuario_con_password(nombre_completo: str, correo: str, password_plano: str) -> str:
    """Utilidad de dominio para altas de usuario (usada por seeds y por el
    futuro módulo de Usuarios, docs/03-requerimientos-funcionales.md Módulo 10)."""
    return hash_password(password_plano)
