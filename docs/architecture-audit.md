# Auditoría de arquitectura pre-Git — LabSync Pro Enterprise

**Fecha:** 2026-08-06
**Alcance:** revisión estructural de backend, frontend e infraestructura (`docker-compose.yml`), sin proponer ni aplicar cambios de código. Complementa (no repite) los hallazgos ya documentados en `docs/24-auditoria-independiente-2026-08-05.md` (auditoría técnica completa, no publicada en el repositorio público).

---

## Backend

**Estructura de carpetas:** organización por módulo de negocio (`backend/app/modules/<modulo>/`), 14 módulos activos (`adjuntos`, `alertas`, `auditoria`, `auth`, `busqueda`, `calendario`, `calibraciones`, `configuracion`, `dashboard`, `documentos`, `equipos`, `mantenimientos`, `qr`, `reportes`), más `app/core/` (configuración, seguridad, base de datos, almacenamiento) y `app/worker/` (proceso de outbox/alertas).

**Separación por capas:** confirmada en cada módulo revisado (ejemplo verificado: `documentos/`) — `domain/` (puertos e entidades, sin dependencias externas), `application/` (casos de uso), `infrastructure/` (implementación SQLAlchemy), `presentation/` (routers FastAPI). Consistente con Clean Architecture, documentado en `docs/13-arquitectura.md` sección 10.

**Configuración:** centralizada en `app/core/config.py` vía Pydantic Settings, con valores por defecto de desarrollo explícitos y comentados (no valores mágicos sin explicación).

**Manejo de errores:** handler global de `IntegrityError` (`app/core/errors.py`) que traduce violaciones de constraints de base de datos a respuestas HTTP controladas, en vez de exponer errores 500 genéricos.

**Seguridad:** JWT asimétrico (RS256), Argon2id para contraseñas, Row-Level Security de PostgreSQL como mecanismo de aislamiento multi-tenant. Detalle completo (incluidos hallazgos de seguridad y su remediación) en la auditoría interna no publicada.

**Pruebas:** 352 tests automatizados (`pytest`), 95% de cobertura, ejecutados contra PostgreSQL y MinIO reales (sin mocks de infraestructura core) — confirmado en la Sección E de este mismo informe.

## Frontend

**Estructura:** organización por feature (`frontend/src/features/<modulo>/`), 14 features activas, con `frontend/src/shared/` para componentes/hooks reutilizables entre features.

**Componentes:** sistema propio con estilo shadcn/ui sobre Tailwind CSS; separación consistente entre componentes de presentación y hooks de datos (TanStack Query).

**Rutas:** todas las páginas usan `React.lazy()` + `Suspense` para code-splitting por ruta, sin excepciones.

**Configuración:** Vite + TypeScript en modo estricto (`noUncheckedIndexedAccess` activo), ESLint con la regla `react-refresh/only-export-components` exigida en modo estricto (`--max-warnings 0`).

**Calidad del código:** 121 tests automatizados (Vitest + Testing Library), enfocados en comportamiento observable, no en detalles de implementación.

## Infraestructura (`docker-compose.yml`)

**Variables externas:** las 6 credenciales de `postgres`/`minio` están parametrizadas vía `${VARIABLE:-valor_por_defecto}` (cambio de Fase 2) — documentadas en `.env.example`.

**Persistencia:** 3 volúmenes nombrados (`labsync_postgres_data`, `labsync_backend_keys`, `labsync_minio_data`), cada uno con un propósito claro y distinto.

**Servicios:** 5 servicios (`postgres`, `minio`, `backend`, `worker`, `frontend`), nombres consistentes, en minúsculas, sin abreviaturas ambiguas.

**Healthchecks — hallazgo de consistencia (menor, no bloqueante):** `postgres`, `minio`, `backend` y `worker` tienen healthcheck propio; **`frontend` no tiene ninguno**, y su `depends_on: [backend]` usa la forma corta (sin `condition: service_healthy`) — a diferencia del resto de dependencias del compose, que sí esperan explícitamente el estado `service_healthy`. No es un bloqueante: el servidor de desarrollo de Vite arranca casi instantáneamente y no depende de que el backend esté listo para *arrancar* (sí para servir peticiones reales, que ocurre después). Se documenta como hallazgo menor de consistencia, no se corrige en esta fase.

**Nombres consistentes:** confirmado — no se encontró ninguna inconsistencia de nomenclatura entre servicios, volúmenes y variables de entorno.

## Conclusión de la sección

Ningún hallazgo de arquitectura bloquea el primer commit. El único hallazgo (ausencia de healthcheck en `frontend`) es una mejora menor de consistencia para una fase posterior, no un defecto que afecte la funcionalidad ni la seguridad del proyecto.
