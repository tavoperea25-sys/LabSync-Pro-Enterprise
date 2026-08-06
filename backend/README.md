# LabSync Pro — Backend

FastAPI + SQLAlchemy 2.0 + PostgreSQL (RLS multi-tenant). Ver `docs/13-arquitectura.md`, `docs/14-base-de-datos.md`, `docs/16-seguridad.md`.

## Desarrollo local (recomendado: vía Docker Compose desde la raíz del repo)

```bash
docker compose up --build
```

Esto levanta `postgres`, `backend` y `frontend`. El backend auto-genera un par de llaves JWT de desarrollo en `.keys/` si no existen (ver `app/core/security.py`) — no requiere pasos manuales.

## Desarrollo local sin Docker

```bash
python -m venv .venv && source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements-dev.txt
cp .env.example .env  # y ajustar DATABASE_URL a tu Postgres local

alembic upgrade head
python -m app.seeds.seed_roles_permisos
python -m app.seeds.seed_dev_tenant   # crea laboratorio 'demo' + admin de prueba

uvicorn app.main:app --reload
```

Credenciales del tenant de desarrollo tras `seed_dev_tenant`:
- `laboratorio_slug`: `demo`
- correo: `admin@demo.labsync.dev`
- password: `CambiarEn123!`

## Alta de un laboratorio real (producción)

`seed_dev_tenant` es solo para desarrollo (bloqueado si `ENTORNO=produccion`, siembra datos de ejemplo). Para dar de alta un laboratorio real, ver `app/scripts/crear_laboratorio.py` (Sprint 13 — onboarding manual v1, `docs/17-roadmap.md` Fase 5):

```bash
python -m app.scripts.crear_laboratorio \
  --nombre "Nombre del laboratorio" \
  --slug identificador-corto \
  --admin-nombre "Nombre del administrador inicial" \
  --admin-correo admin@ejemplo.org
```

Imprime una contraseña temporal una sola vez si no se pasa `--admin-password` explícitamente.

## Pruebas

Requieren una base de datos PostgreSQL real (Row Level Security no puede probarse contra SQLite) **y** un MinIO real (mismo criterio: el almacenamiento de archivos tampoco se prueba con mocks — ver `tests/conftest.py` y `tests/test_documentos_sprint5.py`):

```bash
docker compose up -d postgres minio
createdb -h localhost -U labsync labsync_test   # o usar TEST_DATABASE_URL para apuntar a otra

pytest --cov=app
```

`tests/conftest.py` apunta `MINIO_ENDPOINT_INTERNO` a `localhost:9000` por defecto (el puerto que publica `docker-compose.yml`); `MINIO_ENDPOINT_PUBLICO` no se sobreescribe porque su default en `app/core/config.py` ya es el mismo `localhost:9000` — si se corre MinIO en otro puerto, hay que fijar **ambas** variables (`TEST_MINIO_ENDPOINT_INTERNO` y `MINIO_ENDPOINT_PUBLICO`) para que apunten al mismo lugar, o las operaciones server-to-server (p. ej. copiar un documento) fallarán con `NoSuchKey` aunque la subida haya funcionado.

Archivos de test que requieren MinIO real (suben/leen bytes reales vía URL prefirmada): `test_documentos_sprint5.py`, `test_documentos_sprint6.py`, `test_equipos_foto_sprint24.py`, `test_usuarios_foto_sprint25.py`, `test_equipos_manual_sprint26.py`, `test_busqueda_sprint9.py`.

El gate crítico de aislamiento multi-tenant vive en `tests/test_tenant_isolation.py` — ver `docs/19-checklist.md`, sección Seguridad. Ninguna funcionalidad de negocio nueva se agrega sin que este archivo siga en verde.

## Lint y type-check

```bash
ruff check .
mypy app
```

## Estructura

Ver `docs/13-arquitectura.md` sección 10. Cada módulo de negocio (`app/modules/<modulo>/`) sigue Clean Architecture: `domain` (sin dependencias externas) → `application` (casos de uso) → `infrastructure` (SQLAlchemy) → `presentation` (FastAPI).
