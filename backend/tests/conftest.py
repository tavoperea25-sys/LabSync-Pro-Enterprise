"""Fixtures compartidas. Requiere una base de datos PostgreSQL real
disponible (RLS no puede probarse contra SQLite) — ver README del backend
para levantarla vía `docker compose up postgres`.

IMPORTANTE: la variable de entorno debe fijarse ANTES de importar cualquier
módulo de `app`, porque `app.core.database` crea el engine a nivel de
módulo a partir de `get_settings()` (cacheada con `lru_cache`).
"""

from __future__ import annotations

import os
import uuid

os.environ["ENTORNO"] = "test"

# Dos roles distintos a propósito: las migraciones requieren privilegios
# elevados (crear el rol `labsync_app`, tablas, políticas RLS); los tests
# usan `labsync_app` — el MISMO rol restringido que usa la aplicación en
# runtime — porque de lo contrario los tests de aislamiento (RLS) pasarían
# en falso al conectar como superusuario (ver docs/16-seguridad.md y la
# nota en alembic/versions/0001_esquema_inicial_auth.py).
os.environ["DATABASE_URL_MIGRACIONES"] = os.environ.get(
    "TEST_DATABASE_URL_MIGRACIONES", "postgresql+psycopg2://labsync:labsync@localhost:5432/labsync_test"
)
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://labsync_app:labsync_app@localhost:5432/labsync_test",
)

# Mismo criterio: `MINIO_ENDPOINT_INTERNO` por defecto apunta al hostname de
# Docker (`minio`), que solo es resoluble dentro de la red de contenedores.
# Los tests corren en el host, así que se sobrescribe al puerto publicado en
# docker-compose — MinIO real, nunca mockeado (docs/16-seguridad.md, mismo
# razonamiento que "RLS no puede probarse contra SQLite" más arriba).
os.environ["MINIO_ENDPOINT_INTERNO"] = os.environ.get("TEST_MINIO_ENDPOINT_INTERNO", "localhost:9000")

import pytest  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from app.core.database import SessionLocal, engine, set_tenant_context
from app.core.rate_limit import limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import _asegurar_buckets  # noqa: E402
from app.modules.auth.infrastructure.models import (  # noqa: E402
    Laboratorio,
    Rol,
    Usuario,
    UsuarioRol,
)
from app.seeds.seed_roles_permisos import ejecutar as sembrar_roles_permisos  # noqa: E402

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def _migrar_base_de_datos():
    cfg = Config(os.path.join(_BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(_BACKEND_DIR, "alembic"))
    # alembic/env.py resuelve la URL real desde `database_url_migraciones`
    # (rol con privilegios elevados) — no desde este Config.
    command.upgrade(cfg, "head")
    sembrar_roles_permisos()
    yield
    command.downgrade(cfg, "base")
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _asegurar_buckets_minio():
    """`_asegurar_buckets` (app/main.py) normalmente corre en el evento
    `startup` de FastAPI — pero los fixtures `client` de los tests
    instancian `TestClient(app)` directamente (sin `with ... as client`),
    así que ese lifespan nunca se dispara y los buckets nunca se crean.
    En un MinIO efímero recién levantado (como el de CI) eso revienta con
    "NoSuchBucket" en el primer upload; en un MinIO local de larga vida los
    buckets ya existen de una corrida anterior, así que el problema queda
    enmascarado fuera de CI. Se llama a la misma función real que usa la
    app (no se duplica la lista de buckets) una sola vez por sesión."""
    _asegurar_buckets()


@pytest.fixture(autouse=True)
def _resetear_rate_limiter():
    """El storage del `Limiter` (app/core/rate_limit.py) es un singleton en
    memoria a nivel de proceso — sin resetearlo, las llamadas a `/login` de
    UN test se acumulan sobre las de TODOS los demás (el `TestClient` de
    cada test comparte la misma IP simulada), y un test sin ninguna relación
    con auth puede empezar a recibir 429 solo por orden de ejecución. En
    producción cada IP real tiene su propio balde, así que esto no es un
    problema fuera de tests — es la limitación conocida de probar rate
    limiting por-IP con un cliente de pruebas que no varía de IP."""
    limiter.reset()
    yield


@pytest.fixture
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def crear_laboratorio_con_admin(db: Session):
    """Factory fixture: crea un laboratorio + usuario administrador activo,
    devuelve (laboratorio_id, usuario_id, correo, password_plano)."""

    def _crear(nombre: str, slug: str, correo: str, password: str = "Passw0rd!Segura"):
        laboratorio = Laboratorio(id=uuid.uuid4(), nombre=nombre, slug=slug)
        db.add(laboratorio)
        db.flush()

        set_tenant_context(db, laboratorio.id)

        rol_admin = (
            db.query(Rol).filter_by(nombre="administrador", laboratorio_id=None).one()
        )
        usuario = Usuario(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio.id,
            correo=correo,
            password_hash=hash_password(password),
            nombre_completo=f"Admin {nombre}",
            estado="activo",
            debe_cambiar_password=False,
        )
        db.add(usuario)
        db.flush()
        db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol_admin.id, laboratorio_id=laboratorio.id))
        db.commit()
        return laboratorio.id, usuario.id, correo, password

    return _crear
