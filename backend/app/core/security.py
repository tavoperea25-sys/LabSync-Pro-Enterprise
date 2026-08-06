"""Hashing de contraseñas (Argon2id) y emisión/verificación de JWT (RS256).

Ver docs/16-seguridad.md sección 1 y 4. En desarrollo, si no existe un par de
llaves RSA en disco, se genera uno automáticamente (RNF-PORT-02: `docker
compose up` debe levantar el entorno sin pasos manuales). En producción,
`jwt_private_key_path`/`jwt_public_key_path` deben apuntar a llaves reales
gestionadas fuera del repositorio — nunca se auto-generan silenciosamente
si el archivo de entorno indica `entorno=produccion`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_password_hasher = PasswordHasher()


def hash_password(password_plano: str) -> str:
    return _password_hasher.hash(password_plano)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password_plano)
    except VerifyMismatchError:
        return False


def _generar_par_de_llaves_dev(private_path: Path, public_path: Path) -> None:
    logger.warning(
        "No se encontró un par de llaves JWT en %s — generando uno de DESARROLLO. "
        "Nunca usar esta ruta de código en producción.",
        private_path,
    )
    private_path.parent.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path.write_bytes(private_bytes)
    public_path.write_bytes(public_bytes)


def _cargar_llaves() -> tuple[str, str]:
    settings = get_settings()
    private_path = Path(settings.jwt_private_key_path)
    public_path = Path(settings.jwt_public_key_path)

    if not private_path.exists() or not public_path.exists():
        if settings.entorno == "produccion":
            raise RuntimeError(
                "Llaves JWT no encontradas y el entorno es 'produccion' — "
                "no se auto-generan llaves en producción (docs/16-seguridad.md)."
            )
        _generar_par_de_llaves_dev(private_path, public_path)

    return private_path.read_text(), public_path.read_text()


_PRIVATE_KEY, _PUBLIC_KEY = _cargar_llaves()


def crear_access_token(
    usuario_id: uuid.UUID, laboratorio_id: uuid.UUID, roles: list[str], debe_cambiar_password: bool
) -> str:
    settings = get_settings()
    ahora = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "laboratorio_id": str(laboratorio_id),
        "roles": roles,
        # RF-USR-04 — se embebe en el token (mismo criterio que "roles": no
        # se re-consulta la BD en cada petición) en vez de re-leerlo fresco
        # cada vez. No hay riesgo de quedar obsoleto: la única forma de
        # pasar de True a False es cambiar la contraseña, y eso revoca todas
        # las sesiones (RN-USR-01) forzando un login nuevo con un token
        # nuevo — nunca puede quedar "true" viejo conviviendo con la
        # contraseña ya cambiada de forma útil para un atacante.
        "debe_cambiar_password": debe_cambiar_password,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.access_token_expira_minutos),
        "tipo": "access",
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm=settings.jwt_algoritmo)


def crear_refresh_token(usuario_id: uuid.UUID, laboratorio_id: uuid.UUID) -> tuple[str, str]:
    """Refresh token firmado (JWT) — no solo un UUID opaco.

    Se firma (RS256) para poder leer `laboratorio_id` de forma segura ANTES
    de tocar la base de datos, y así fijar el contexto de tenant (RLS) antes
    de la consulta a `sesiones` — evita el problema de "huevo y gallina" de
    resolver el tenant de una tabla que ya está protegida por RLS. El estado
    de revocación real sigue viviendo en la base de datos (`sesiones.revocada`),
    el JWT por sí solo nunca es suficiente para considerar la sesión válida.
    Ver docs/16-seguridad.md.
    """
    settings = get_settings()
    jti = str(uuid.uuid4())
    ahora = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "laboratorio_id": str(laboratorio_id),
        "jti": jti,
        "iat": ahora,
        "exp": ahora + timedelta(days=settings.refresh_token_expira_dias),
        "tipo": "refresh",
    }
    token = jwt.encode(payload, _PRIVATE_KEY, algorithm=settings.jwt_algoritmo)
    return token, jti


def decodificar_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(token, _PUBLIC_KEY, algorithms=[settings.jwt_algoritmo])
    if payload.get("tipo") != "access":
        raise jwt.InvalidTokenError("El token no es un access token válido.")
    return payload


def decodificar_refresh_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(token, _PUBLIC_KEY, algorithms=[settings.jwt_algoritmo])
    if payload.get("tipo") != "refresh":
        raise jwt.InvalidTokenError("El token no es un refresh token válido.")
    return payload
