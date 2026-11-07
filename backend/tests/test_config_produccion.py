"""Revisión de seguridad módulo Auth, hallazgo 3 — `Settings` debe negarse a
arrancar si `ENTORNO=produccion` y algún secreto sigue en su valor de
desarrollo por defecto. Complementa el cambio en docker-compose.yml
(`${VAR:?mensaje}`, una barrera a nivel de contenedor) con una segunda
barrera a nivel de aplicación."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Mismos valores que `_SECRETOS_DEV_POR_DEFECTO` en app/core/config.py — se
# pasan explícitamente (en vez de confiar en los defaults de la clase o en
# variables de entorno del proceso de test) para que esta prueba no dependa
# de qué haya en el entorno donde corre pytest (conftest.py fija
# DATABASE_URL/DATABASE_URL_MIGRACIONES a la base de datos de test, distinta
# del default de desarrollo).
_SECRETOS_DEV = {
    "database_url": "postgresql+psycopg2://labsync_app:labsync_app@localhost:5432/labsync",
    "database_url_migraciones": "postgresql+psycopg2://labsync:labsync@localhost:5432/labsync",
    "minio_access_key": "labsync",
    "minio_secret_key": "labsync123",
}


def test_settings_produccion_con_secretos_por_defecto_falla():
    with pytest.raises(ValidationError, match="valor de desarrollo"):
        Settings(entorno="produccion", _env_file=None, **_SECRETOS_DEV)


def test_settings_produccion_con_secretos_cambiados_no_falla():
    Settings(
        entorno="produccion",
        database_url="postgresql+psycopg2://real:clave-real@prod-db:5432/labsync",
        database_url_migraciones="postgresql+psycopg2://real_migrador:clave-real@prod-db:5432/labsync",
        minio_access_key="clave-de-produccion-real",
        minio_secret_key="secreto-de-produccion-real",
        _env_file=None,
    )


def test_settings_desarrollo_no_valida_secretos():
    # Sin ENTORNO=produccion (el default), nunca debe fallar aunque todo
    # quede en los valores de desarrollo — es el comportamiento normal de
    # desarrollo local.
    Settings(_env_file=None, **_SECRETOS_DEV)
