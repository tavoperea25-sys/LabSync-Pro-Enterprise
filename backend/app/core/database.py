"""Sesión de base de datos con contexto de tenant para Row Level Security.

Ver docs/13-arquitectura.md sección 3 y docs/14-base-de-datos.md sección 3.
`laboratorio_id` SIEMPRE se establece a partir del JWT ya validado (o, en el
flujo de login, del identificador de laboratorio provisto explícitamente en
la petición) — nunca se acepta un `laboratorio_id` de un parámetro de query
sin pasar antes por esa resolución.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

from sqlalchemy import Engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()


class Base(DeclarativeBase):
    pass


def _crear_engine() -> Engine:
    from sqlalchemy import create_engine

    return create_engine(
        _settings.database_url,
        # `pool_pre_ping` no se expone por variable de entorno a propósito:
        # es una garantía de correctitud para un engine de vida larga como
        # este (un `SELECT 1` barato antes de reusar una conexión, evita
        # reutilizar una ya cerrada por el otro extremo), no un parámetro de
        # tuning — no hay ningún entorno legítimo del proyecto donde
        # convenga desactivarlo.
        pool_pre_ping=True,
        # Ver la justificación completa (por qué estos números, cuántos
        # procesos los usan) en `app/core/config.py` junto a cada campo.
        pool_size=_settings.db_pool_size,
        max_overflow=_settings.db_max_overflow,
        pool_timeout=_settings.db_pool_timeout,
        pool_recycle=_settings.db_pool_recycle_segundos,
    )


engine = _crear_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def set_tenant_context(db: Session, laboratorio_id: uuid.UUID | None) -> None:
    """Fija `app.current_tenant_id` para la transacción actual.

    Con `SET LOCAL`, el valor se revierte automáticamente al finalizar la
    transacción — nunca puede "filtrarse" a otra petición que reutilice la
    misma conexión desde el pool.
    """
    valor = str(laboratorio_id) if laboratorio_id else ""
    db.execute(text("SET LOCAL app.current_tenant_id = :valor"), {"valor": valor})


def get_db() -> Generator[Session, None, None]:
    """Dependency de FastAPI: sesión SIN contexto de tenant todavía.

    Los routers que operan dentro de un tenant deben llamar a
    `set_tenant_context` explícitamente (normalmente vía la dependency
    `get_tenant_db` del módulo de auth) antes de ejecutar cualquier query
    sobre una tabla con RLS.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
