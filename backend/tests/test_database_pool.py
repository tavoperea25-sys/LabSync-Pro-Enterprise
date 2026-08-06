"""Fase 2 / M2 (planificación 2026-08-04, docs/22) — el engine de runtime
(`app/core/database.py`) ahora fija explícitamente el tuning del pool en vez
de depender de los defaults implícitos de SQLAlchemy. No es una prueba de
comportamiento bajo carga (eso requeriría un entorno de concurrencia real);
es la validación funcional pedida: que el engine realmente se construye con
los parámetros configurados, para que un futuro cambio que vuelva a
`create_engine(url, pool_pre_ping=True)` sin el resto de argumentos se
detecte aquí en vez de pasar desapercibido."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.database import engine


def test_engine_usa_el_pool_configurado_en_settings() -> None:
    settings = get_settings()
    pool = engine.pool

    assert pool.size() == settings.db_pool_size
    assert pool._max_overflow == settings.db_max_overflow
    assert pool._timeout == settings.db_pool_timeout
    assert pool._recycle == settings.db_pool_recycle_segundos
    assert pool._pre_ping is True


def test_valores_por_defecto_caben_dos_procesos_dentro_del_limite_de_postgres() -> None:
    """Documenta la cuenta que justifica los valores por defecto (ver
    comentario en `core/config.py`): 2 procesos (API + worker) con su propio
    pool, en el peor caso cada uno usando `pool_size + max_overflow`
    conexiones a la vez, más 1 conexión cruda de `ws_gateway.py` (LISTEN,
    fuera del pool) — todo eso debe quedar cómodamente por debajo del
    `max_connections` por defecto de Postgres (100), con margen para
    `psql`/Alembic. Si alguien sube `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` lo
    suficiente como para romper ese margen, este test debe fallar y forzar
    a revisar la cuenta conscientemente."""
    settings = get_settings()
    conexiones_por_proceso = settings.db_pool_size + settings.db_max_overflow
    procesos_con_pool = 2  # API (1 proceso uvicorn) + worker (contenedor separado)
    conexion_listen_ws_gateway = 1
    margen_minimo_para_psql_y_alembic = 20

    total_peor_caso = conexiones_por_proceso * procesos_con_pool + conexion_listen_ws_gateway
    postgres_max_connections_por_defecto = 100

    assert total_peor_caso + margen_minimo_para_psql_y_alembic <= postgres_max_connections_por_defecto
