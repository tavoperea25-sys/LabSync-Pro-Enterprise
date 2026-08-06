# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

Sin cambios todavía sobre el estado de la primera publicación.

## [1.0.0-rc1] - 2026-08-06

Primera publicación del repositorio bajo control de versiones. El proyecto llega a
este punto tras un proceso de desarrollo por fases (fundación del producto, módulos
operativos, y una revisión técnica previa al release) y queda marcado como
**Release Candidate 1**.

### Added
- Backend FastAPI + SQLAlchemy 2.0 sobre PostgreSQL con Row-Level Security
  multi-tenant, siguiendo Clean Architecture por módulo de negocio.
- Frontend React 19 + TypeScript + Vite, organizado por features.
- Autenticación JWT (RS256) con Argon2id y rotación de refresh tokens.
- Almacenamiento de archivos vía MinIO con URLs prefirmadas.
- Módulos funcionales: equipos, documentos, calibraciones, mantenimientos,
  alertas, calendario, búsqueda global, auditoría, reportes, configuración,
  usuarios.
- Suite de tests automatizados de backend (pytest, contra Postgres/MinIO
  reales) y frontend (Vitest).
- Pipeline de integración continua (GitHub Actions) con lint, type-check y
  tests para ambos stacks.
- Infraestructura de repositorio: `.gitignore`, `.gitattributes`, plantillas
  de issues y pull requests, `CODEOWNERS`, `SECURITY.md`, Dependabot.

### Changed
- `docker-compose.yml`: credenciales de desarrollo de `postgres`/`minio`
  parametrizadas vía variables de entorno con valores por defecto
  (`${VARIABLE:-valor}`), en vez de estar fijas en el archivo.
- Reorganización de archivos de repositorio: el prototipo estático de diseño
  del login se movió a `design/login-prototype/`, separado de la aplicación.

### Fixed
- Corregidos los hallazgos técnicos identificados durante la revisión previa
  al release (build de producción, cobertura de la suite de tests en CI, una
  vulnerabilidad de seguridad en la previsualización de documentos, y deuda
  de formato de linting), todos verificados con evidencia automatizada antes
  de este release.

### Security
- Las credenciales que antes vivían hardcodeadas en `docker-compose.yml`
  ahora se parametrizan vía `.env` (no versionado), con `.env.example`
  documentando las variables esperadas.

[Unreleased]: ../../compare/v1.0.0-rc1...HEAD
[1.0.0-rc1]: ../../releases/tag/v1.0.0-rc1
