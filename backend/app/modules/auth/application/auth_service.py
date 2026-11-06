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

# Revisión de seguridad módulo Auth, hallazgo 4 — antes, cuando el correo no
# existía, `login` retornaba sin llamar nunca a `verificar_password`
# (Argon2id, deliberadamente lento), a diferencia de la rama de contraseña
# incorrecta (correo sí existe) que sí lo hacía. Esa asimetría de tiempo de
# respuesta permite enumerar correos registrados. Se precalcula una sola vez
# al importar el módulo (costo de Argon2id pagado una vez, no por request) y
# se verifica contra ella cuando el usuario no existe, para que ambas ramas
# paguen el mismo costo.
_HASH_FICTICIO = hash_password("contraseña-ficticia-para-mitigar-enumeracion-por-tiempo")


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode()).hexdigest()


@dataclass
class ResultadoLogin:
    access_token: str
    refresh_token: str
    expira_en_segundos: int
    usuario: Usuario
    # Días para el `max_age` de la cookie de refresh — hallazgo 2: antes el
    # router decidía esto por su cuenta (hardcodeado) sin relación con lo
    # que de verdad se guardó en la sesión. Nunca se expone en `LoginResponse`
    # (el router mapea campos explícitos en `_a_respuesta`), así que no
    # cambia el contrato público de la API.
    duracion_dias_cookie: int


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
        recordarme: bool,
        ip_origen: str | None,
        user_agent: str | None,
    ) -> ResultadoLogin:
        if not self._laboratorios.existe_activo(laboratorio_id):
            # Mismo error genérico que credenciales inválidas — no revela
            # si el laboratorio existe (mitiga enumeración, docs/16-seguridad.md).
            raise CredencialesInvalidas()

        usuario = self._usuarios.buscar_por_correo(laboratorio_id, correo)
        if usuario is None:
            # Hallazgo 4 — paga el mismo costo de Argon2id que la rama de
            # contraseña incorrecta de abajo, para no revelar por tiempo de
            # respuesta si el correo existe.
            verificar_password(password, _HASH_FICTICIO)
            raise CredencialesInvalidas()

        ahora = datetime.now(UTC)
        if usuario.bloqueado_hasta is not None and usuario.esta_bloqueado(ahora):
            segundos_restantes = int((usuario.bloqueado_hasta - ahora).total_seconds())
            raise CuentaBloqueada(segundos_restantes)

        if not usuario.esta_activo() or not verificar_password(password, usuario.password_hash):
            self._registrar_intento_fallido(usuario)
            raise CredencialesInvalidas()

        self._usuarios.resetear_intentos_fallidos(usuario.id)

        # Hallazgo 2 — la duración elegida ("Recordarme" o no) se guarda en
        # la propia sesión en vez de que el router la calcule por su cuenta,
        # para que sobreviva a rotaciones sucesivas de refresh.
        dias = (
            self._settings.refresh_recordarme_dias
            if recordarme
            else self._settings.refresh_token_expira_dias
        )

        access_token = crear_access_token(
            usuario.id, usuario.laboratorio_id, usuario.roles, usuario.debe_cambiar_password
        )
        refresh_token, jti = crear_refresh_token(usuario.id, usuario.laboratorio_id)
        self._sesiones.crear(
            usuario_id=usuario.id,
            laboratorio_id=usuario.laboratorio_id,
            refresh_token_hash=_hash_jti(jti),
            expira_en=ahora + timedelta(days=dias),
            duracion_dias=dias,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

        return ResultadoLogin(
            access_token=access_token,
            refresh_token=refresh_token,
            expira_en_segundos=self._settings.access_token_expira_minutos * 60,
            usuario=usuario,
            duracion_dias_cookie=dias,
        )

    def _registrar_intento_fallido(self, usuario: Usuario) -> None:
        nuevos_intentos = usuario.intentos_fallidos + 1
        bloqueado_hasta = None
        if nuevos_intentos >= _UMBRAL_INTENTOS_FALLIDOS:
            ciclos_de_bloqueo = nuevos_intentos - _UMBRAL_INTENTOS_FALLIDOS + 1
            # Hallazgo 5 — sin techo, esto duplica sin límite (a los 20
            # intentos fallidos supera las 500 horas). `bloqueo_maximo_segundos`
            # (Settings, 15 min por defecto) tapa el crecimiento exponencial.
            segundos = min(
                _BLOQUEO_BASE_SEGUNDOS * (2 ** (ciclos_de_bloqueo - 1)),
                self._settings.bloqueo_maximo_segundos,
            )
            bloqueado_hasta = datetime.now(UTC) + timedelta(seconds=segundos)
        self._usuarios.registrar_intento_fallido(usuario.id, bloqueado_hasta)

    def refresh(
        self, refresh_token_plano: str, ip_origen: str | None, user_agent: str | None
    ) -> ResultadoLogin:
        try:
            claims = decodificar_refresh_token(refresh_token_plano)
        except pyjwt.PyJWTError as exc:
            raise TokenInvalido() from exc

        # Hallazgo 1 — `FOR UPDATE`: bloquea la fila hasta que esta
        # transacción termine, para que una segunda petición de refresh
        # concurrente con el mismo token (otra pestaña, otro dispositivo —
        # dentro de una misma pestaña ya se deduplica en httpClient.ts) vea
        # de forma confiable el resultado ya rotado de la primera en vez de
        # competir sobre una lectura sin bloqueo.
        sesion = self._sesiones.buscar_por_hash_para_refresh(_hash_jti(claims["jti"]))

        if sesion is None:
            raise TokenInvalido()

        if sesion.revocada:
            ahora = datetime.now(UTC)
            dentro_de_ventana_de_gracia = sesion.revocada_en is not None and (
                ahora - sesion.revocada_en
            ) <= timedelta(seconds=self._settings.refresh_ventana_gracia_segundos)
            if not dentro_de_ventana_de_gracia:
                # Reuso de un refresh token rotado hace rato (o nunca
                # rotado por una ruta normal — p. ej. tras un logout o una
                # revocación masiva previa, ninguna de las cuales marca
                # `revocada_en`): indicio de robo — se revocan TODAS las
                # sesiones del usuario (docs/16-seguridad.md).
                self._sesiones.revocar_todas_de_usuario(sesion.usuario_id)
                raise TokenInvalido("Sesión comprometida — todas las sesiones fueron cerradas.")
            # Dentro de la ventana de gracia: lo más probable es una carrera
            # de refresh concurrente legítima (dos pestañas/dispositivos),
            # no un robo — se continúa como una rotación normal en vez de
            # revocar todo.

        if sesion.expira_en < datetime.now(UTC):
            raise TokenInvalido("La sesión ha expirado.")

        usuario = self._usuarios.obtener_por_id(sesion.usuario_id)
        if usuario is None or not usuario.esta_activo():
            raise TokenInvalido()

        # Rotación: se revoca el token usado (si ya lo estaba por la
        # ventana de gracia de arriba, es un no-op) y se emite uno nuevo.
        self._sesiones.revocar_por_rotacion(sesion.id)
        access_token = crear_access_token(
            usuario.id, usuario.laboratorio_id, usuario.roles, usuario.debe_cambiar_password
        )
        nuevo_refresh, nuevo_jti = crear_refresh_token(usuario.id, usuario.laboratorio_id)
        # Hallazgo 2 — se preserva la duración elegida en el login original
        # (`sesion.duracion_dias`), no el default fijo de settings, para que
        # "Recordarme" sobreviva a esta y futuras rotaciones.
        self._sesiones.crear(
            usuario_id=usuario.id,
            laboratorio_id=usuario.laboratorio_id,
            refresh_token_hash=_hash_jti(nuevo_jti),
            expira_en=datetime.now(UTC) + timedelta(days=sesion.duracion_dias),
            duracion_dias=sesion.duracion_dias,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )

        return ResultadoLogin(
            access_token=access_token,
            refresh_token=nuevo_refresh,
            expira_en_segundos=self._settings.access_token_expira_minutos * 60,
            usuario=usuario,
            duracion_dias_cookie=sesion.duracion_dias,
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
