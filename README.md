# LabSync Pro Enterprise

**Gestión inteligente para laboratorios modernos.**

Plataforma de gestión de hojas de vida de equipos, documentación, calibraciones, mantenimientos y trazabilidad para laboratorios clínicos, desarrollada para el **Laboratorio de Salud Pública del Cesar** (Gobernación del Cesar, Colombia).

> **Estado:** Release Candidate 1 (RC1) — ver [Estado del proyecto](#estado-del-proyecto).

<!-- TODO: badge de CI una vez el repositorio tenga remoto en GitHub
[![CI](https://github.com/<org>/<repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<org>/<repo>/actions/workflows/ci.yml)
-->

---

## Tabla de contenidos

- [Descripción](#descripción)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Backend](#backend)
- [Frontend](#frontend)
- [Base de datos](#base-de-datos)
- [Almacenamiento de archivos (MinIO)](#almacenamiento-de-archivos-minio)
- [Docker](#docker)
- [Instalación](#instalación)
- [Variables de entorno](#variables-de-entorno)
- [Ejecución local](#ejecución-local)
- [Tests](#tests)
- [Integración continua (CI)](#integración-continua-ci)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Documentación](#documentación)
- [Roadmap](#roadmap)
- [Estado del proyecto](#estado-del-proyecto)
- [Capturas](#capturas)
- [Autores](#autores)
- [Licencia](#licencia)

---

## Descripción

LabSync Pro Enterprise centraliza la gestión operativa de un laboratorio clínico: inventario de equipos con código QR, calibraciones y su vencimiento, mantenimientos preventivos/correctivos, gestor documental con control de versiones y aprobación, alertas automáticas, auditoría de acciones, y reportes exportables. Es un sistema **multi-tenant**: varios laboratorios pueden operar sobre la misma instalación con aislamiento estricto de datos entre ellos.

## Arquitectura

Monolito modular en dos aplicaciones independientes (backend y frontend) más un proceso worker, orquestados vía Docker Compose:

```
┌─────────────┐      ┌─────────────┐      ┌──────────────┐
│  Frontend   │──────▶   Backend   │──────▶  PostgreSQL  │
│  (React)    │ REST │  (FastAPI)  │      │  (RLS multi-  │
└─────────────┘      └──────┬──────┘      │   tenant)     │
                             │             └──────────────┘
                      ┌──────┴──────┐
                      │   Worker    │──────▶  outbox / alertas
                      │  (Python)   │        (LISTEN/NOTIFY)
                      └──────┬──────┘
                             │
                      ┌──────┴──────┐
                      │    MinIO    │  documentos, evidencias,
                      │  (objetos)  │  fotos, certificados
                      └─────────────┘
```

El backend sigue **Clean Architecture** por módulo de negocio (`domain` → `application` → `infrastructure` → `presentation`), y el aislamiento entre laboratorios se implementa con **Row-Level Security** de PostgreSQL, no con lógica de aplicación. Detalle completo en [`docs/13-arquitectura.md`](docs/13-arquitectura.md).

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Python 3.12 |
| Frontend | React 19, TypeScript, Vite, TanStack Query, React Router, Tailwind CSS |
| Base de datos | PostgreSQL 16 (Row-Level Security multi-tenant) |
| Almacenamiento de objetos | MinIO (S3-compatible), URLs prefirmadas |
| Autenticación | JWT (RS256), Argon2id, rotación de refresh tokens |
| Testing | pytest + pytest-cov (backend), Vitest + Testing Library (frontend) |
| CI | GitHub Actions |
| Contenedores | Docker, Docker Compose |

## Backend

FastAPI + SQLAlchemy 2.0 sobre PostgreSQL con Row-Level Security multi-tenant. Cada módulo de negocio (`backend/app/modules/<modulo>/`) está organizado en capas: `domain` (sin dependencias externas, define los puertos), `application` (casos de uso), `infrastructure` (implementación con SQLAlchemy), `presentation` (routers FastAPI). Autenticación JWT asimétrica (RS256), hashing de contraseñas con Argon2id, rotación de refresh tokens con detección de reuso. Ver [`backend/README.md`](backend/README.md) para comandos de desarrollo, y [`docs/15-api-design.md`](docs/15-api-design.md) para el contrato de la API.

## Frontend

React 19 + TypeScript + Vite, organizado por features (`frontend/src/features/<modulo>/`), con TanStack Query para el estado del servidor, React Hook Form + Zod para formularios, y un sistema de componentes propio con estilo shadcn/ui sobre Tailwind CSS. Ver [`frontend/README.md`](frontend/README.md).

## Base de datos

PostgreSQL 16. El aislamiento entre laboratorios (tenants) se implementa con **Row-Level Security a nivel de fila** (`ENABLE`/`FORCE ROW LEVEL SECURITY` + políticas `USING`/`WITH CHECK`), reforzado con un rol de aplicación no-superusuario dedicado (Postgres ignora RLS para superusuarios). Migraciones versionadas con Alembic. Detalle completo del modelo de datos en [`docs/14-base-de-datos.md`](docs/14-base-de-datos.md).

## Almacenamiento de archivos (MinIO)

Todos los archivos (documentos, evidencias de mantenimiento, certificados de calibración, fotos de equipos/usuarios) se suben y descargan mediante **URLs prefirmadas** — el backend nunca transporta el binario, solo firma URLs de acceso temporal directo entre el navegador y MinIO. Cifrado en reposo (SSE-S3) a nivel de bucket. Detalle en [`docs/13-arquitectura.md`](docs/13-arquitectura.md) sección 5.

## Docker

`docker-compose.yml` en la raíz orquesta los 5 servicios (`postgres`, `minio`, `backend`, `worker`, `frontend`) con healthchecks y dependencias explícitas entre ellos. Es el flujo de desarrollo recomendado — ver [Ejecución local](#ejecución-local).

## Instalación

### Requisitos previos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose (recomendado), **o**
- Python 3.12+ y Node.js 22+ si prefieres correr backend/frontend sin contenedores.

### Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd login
```

## Variables de entorno

| Archivo | Propósito |
|---|---|
| `.env.example` (raíz) | Credenciales de `postgres`/`minio` que lee `docker-compose.yml`. Copiar a `.env` solo si necesitas cambiar los valores por defecto de desarrollo. |
| `backend/.env.example` | Configuración del backend (base de datos, JWT, MinIO, CORS, rate limiting). Copiar a `backend/.env`. |
| `frontend/.env.example` | Configuración del frontend (proxy de la API en desarrollo). Copiar a `frontend/.env`. |

**Nota de coherencia:** si cambias `MINIO_ROOT_USER`/`MINIO_ROOT_PASSWORD` en el `.env` de la raíz, actualiza también `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY` en `backend/.env` — son las credenciales con las que el backend se autentica contra ese mismo MinIO.

Ninguna variable de entorno con valores reales se versiona — todos los `.env` reales están excluidos vía `.gitignore`, solo sus `.env.example` correspondientes.

## Ejecución local

### Con Docker (recomendado)

```bash
docker compose up --build
```

Levanta los 5 servicios. Frontend en `http://localhost:5173`, API en `http://localhost:8000`, consola de MinIO en `http://localhost:9001`. El backend auto-genera un par de llaves JWT de desarrollo en `backend/.keys/` si no existen — no requiere pasos manuales adicionales.

#### Si ya tenías el volumen de MinIO de antes de 2026-11-06

`docker-compose.yml` corre el servicio `minio` con la imagen `bitnamilegacy/minio` (ver el comentario junto a `image:` en ese archivo) en vez de la oficial `minio/minio`, eliminada de Docker Hub. Esta imagen corre como UID 1001 por defecto — si tu volumen `labsync_minio_data` ya existía (creado por `minio/minio`, dueño `root`), el contenedor nuevo no podrá escribirlo y vas a ver `FATAL Unable to initialize backend: file access denied` en `docker logs <proyecto>-minio-1`. Se arregla una sola vez, sin tocar los datos:

```bash
docker compose stop minio
docker run --rm -v <proyecto>_labsync_minio_data:/data busybox chown -R 1001:0 /data
docker compose up -d minio
```

(`<proyecto>` es el nombre del directorio del repositorio — Docker Compose lo usa como prefijo del volumen; confirmalo con `docker volume ls`). Verificá que no perdiste nada comparando la cantidad de objetos de cada bucket antes y después (consola de MinIO en `http://localhost:9001`, o `mc ls --recursive local/<bucket> | wc -l`).

### Sin Docker

Ver las instrucciones detalladas en [`backend/README.md`](backend/README.md#desarrollo-local-sin-docker) y [`frontend/README.md`](frontend/README.md#desarrollo-sin-docker).

### Credenciales de desarrollo

Tras sembrar el tenant de desarrollo (ver `backend/README.md`):
- Laboratorio: `demo`
- Correo: `admin@demo.labsync.dev`
- Contraseña: `CambiarEn123!`

## Tests

```bash
# Backend — requiere Postgres y MinIO reales (ver backend/README.md)
cd backend && pytest --cov=app

# Frontend
cd frontend && npm test
```

Ambas suites corren contra infraestructura real (Postgres/MinIO), sin mockear la capa de aislamiento multi-tenant ni el almacenamiento de archivos — decisión documentada en `backend/tests/conftest.py`.

## Integración continua (CI)

GitHub Actions (`.github/workflows/ci.yml`) ejecuta, en cada push/PR, dos jobs independientes:

- **`backend`**: `ruff check .` → `mypy app` → arranque de MinIO real → `pytest --cov=app`.
- **`frontend`**: `npm run lint` → `npm run typecheck` → `npm test` → `npm run build`.

## Estructura del proyecto

```
.
├── backend/                  # FastAPI + SQLAlchemy — API y worker
│   ├── app/
│   │   ├── core/              # configuración, seguridad, DB, storage
│   │   ├── modules/<modulo>/  # domain / application / infrastructure / presentation
│   │   └── worker/            # proceso de outbox y alertas
│   ├── alembic/versions/      # migraciones
│   └── tests/
├── frontend/                 # React + TypeScript + Vite
│   └── src/
│       ├── features/<modulo>/
│       └── shared/
├── design/
│   └── login-prototype/       # prototipo estático de referencia visual del login
├── docs/                      # blueprint funcional/técnico del proyecto
├── .github/                   # workflows de CI, plantillas de issues/PR
├── docker-compose.yml
└── README.md
```

## Documentación

El blueprint completo del proyecto (visión, requerimientos, arquitectura, base de datos, API, seguridad, roadmap, sprints) vive en [`docs/`](docs/), indexado en [`docs/README.md`](docs/README.md). Documentos técnicos destacados:

- [`docs/13-arquitectura.md`](docs/13-arquitectura.md) — arquitectura completa
- [`docs/14-base-de-datos.md`](docs/14-base-de-datos.md) — modelo de datos y RLS
- [`docs/15-api-design.md`](docs/15-api-design.md) — contrato de la API
- [`docs/16-seguridad.md`](docs/16-seguridad.md) — autenticación, autorización, aislamiento multi-tenant
- [`docs/17-roadmap.md`](docs/17-roadmap.md) — fases del proyecto

## Roadmap

El proyecto se planificó en fases incrementales (ver [`docs/17-roadmap.md`](docs/17-roadmap.md) y [`docs/18-sprints.md`](docs/18-sprints.md) para el detalle completo). A alto nivel: fundación del producto (auth, equipos, documentos) → módulos operativos (calibraciones, mantenimientos, alertas) → calendario, búsqueda global y auditoría → onboarding y configuración por laboratorio → expansión futura (priorizada, no comprometida).

## Estado del proyecto

El proyecto completó su proceso de preparación para **Release Candidate 1 (RC1)**: los hallazgos técnicos identificados durante la revisión previa al release (build de producción, cobertura de CI, una vulnerabilidad de seguridad y deuda de higiene de linting) fueron corregidos y verificados con evidencia automatizada — sin regresiones detectadas en ninguna de las dos suites de tests. El detalle completo de ese proceso es un documento de uso interno, no incluido en este repositorio.

## Capturas

> _Pendiente — capturas de pantalla del dashboard, gestión de equipos, documentos y calendario se agregarán aquí._

<!-- ![Dashboard](docs/assets/screenshot-dashboard.png) -->
<!-- ![Gestión de equipos](docs/assets/screenshot-equipos.png) -->
<!-- ![Documentos](docs/assets/screenshot-documentos.png) -->

## Autores

<!-- TODO: reemplazar por los autores/mantenedores reales del proyecto -->
_Pendiente de completar._

## Licencia

Software propietario. Todos los derechos reservados. Uso no autorizado sin permiso expreso del titular.
