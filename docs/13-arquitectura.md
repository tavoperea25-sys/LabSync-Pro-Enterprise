# 13 — Arquitectura

Decisiones vinculantes heredadas de `00-analisis-critico-y-recomendaciones.md`: monolito modular (no microservicios en v1), Docker Compose (no Kubernetes en v1), multi-tenancy por fila con Row Level Security.

> **Nota de vigencia (auditoría 2026-07-31, hallazgo C4):** este documento fue auditado línea por línea contra el `docker-compose.yml` y el código real del repositorio. Describe **únicamente lo que existe hoy**. Todo lo que antes se documentaba como si ya existiera pero en realidad es un plan a futuro (capa Nginx/TLS, despliegue de producción, balanceo de carga, etc.) se movió explícitamente a la sección **11. Arquitectura futura**, con la etiqueta 🔮 para que no vuelva a confundirse con el estado actual.

---

## 1. Vista lógica (estado actual)

El único entorno que existe hoy es el que levanta `docker-compose.yml` — no hay un `docker-compose.prod.yml` ni ninguna otra variante de despliegue en el repositorio. El navegador habla **directo** con dos procesos distintos, sin ningún componente intermedio (ni reverse proxy, ni balanceador, ni terminación TLS):

```
┌──────────────────────────────────────────────────────────────────────┐
│                           Cliente (navegador)                          │
└──────────────────┬────────────────────────────────┬────────────────────┘
                    │ HTTP :5173                      │ HTTP :8000
                    │ (sin TLS — ver sección 11)       │ REST + WebSocket (sin TLS)
┌───────────────────▼──────────────┐   ┌───────────────▼─────────────────────────┐
│  frontend (contenedor Docker)      │   │  backend (contenedor Docker)               │
│  Vite dev server                   │   │  FastAPI — monolito modular, Uvicorn        │
│  React 19 + TS + Tailwind          │   │  ┌────────────────────────────────────┐    │
│  (`npm run dev`, no build de        │   │  │ Presentación (routers REST + WS)     │    │
│  producción — ver sección 11)       │   │  ├────────────────────────────────────┤    │
└─────────────────────────────────────┘   │  │ Aplicación (casos de uso)            │    │
                                           │  ├────────────────────────────────────┤    │
                                           │  │ Dominio (entidades, reglas, puertos) │    │
                                           │  ├────────────────────────────────────┤    │
                                           │  │ Infraestructura (SQLAlchemy, MinIO,   │    │
                                           │  │ JWT, outbox)                          │    │
                                           │  └────────────────────────────────────┘    │
                                           │  Módulos: auth · equipos · documentos ·      │
                                           │  calibraciones · mantenimientos · alertas ·  │
                                           │  calendario · busqueda · usuarios ·          │
                                           │  auditoria · reportes · qr · configuracion   │
                                           └───────┬───────────────┬───────────┬───────────┘
                                                   │               │           │
                                       ┌───────────▼──────┐ ┌──────▼───────┐ ┌─▼────────────────┐
                                       │  postgres (Docker)  │ │  minio (Docker)│ │  worker (Docker)   │
                                       │  PostgreSQL 16       │ │  S3-compatible │ │  proceso Python     │
                                       │  RLS multi-tenant     │ │  documentos/   │ │  separado — outbox,  │
                                       │                       │ │  evidencias    │ │  alertas, reportes    │
                                       └───────────────────────┘ └────────────────┘ │  async (polling,       │
                                                                                     │  sin cola dedicada)     │
                                                                                     └─────────────────────────┘
```

**Lo que confirma el propio `docker-compose.yml`:** 5 servicios — `frontend`, `backend`, `worker`, `postgres`, `minio`. Ningún servicio `nginx` ni ningún proxy inverso. `backend` expone el puerto 8000 directamente al host; `frontend` expone el 5173 directamente (Vite dev server, no un build estático servido por algo como Nginx/Caddy). Ninguno de los dos tiene TLS configurado — todo el tráfico, incluido el login, viaja hoy sobre HTTP plano en este entorno.

## 2. Patrones arquitectónicos

- **Clean Architecture / Arquitectura Hexagonal** por módulo: el dominio no depende de FastAPI ni de SQLAlchemy — depende de puertos (interfaces) que la infraestructura implementa. Esto permite testear reglas de negocio sin base de datos real y es lo que hace viable extraer un módulo a servicio independiente en el futuro sin reescribir lógica.
- **Feature-based structure** tanto en backend (`app/modules/<modulo>/{domain,application,infrastructure,presentation}`) como en frontend (`src/features/<modulo>/{components,hooks,api,types}`).
- **Repository Pattern**: cada módulo expone un repositorio (puerto) para su agregado principal; SQLAlchemy es el único punto que conoce el esquema real.
- **DTOs tipados**: Pydantic v2 en el límite de la API (nunca se exponen modelos de base de datos directamente en las respuestas).
- **Manejo global de errores**: un middleware central traduce excepciones de dominio a respuestas HTTP consistentes (ver `15-api-design.md`, formato de error estándar).
- **Outbox pattern** para notificaciones: ninguna operación de negocio (ej. registrar calibración) depende de que un envío de email/WebSocket tenga éxito; se escribe en una tabla `notificaciones_pendientes` dentro de la misma transacción, y un worker separado la procesa.
- **CQRS ligero** en lecturas de alto volumen (Dashboard, Reportes): queries de lectura optimizadas separadas de los comandos de escritura, sin llegar a event sourcing — complejidad no justificada en v1.

## 3. Multi-tenancy

- Columna `laboratorio_id` (tenant) en toda tabla con datos de negocio.
- **Row Level Security de PostgreSQL** activada por tabla, con política basada en una variable de sesión (`SET app.current_tenant_id`) establecida por el backend en cada conexión/transacción a partir del tenant resuelto del JWT.
- El backend nunca construye queries que dependan únicamente de un `WHERE laboratorio_id = :id` manual como única barrera — RLS es la barrera de último recurso incluso si un desarrollador olvida el filtro.
- Pruebas automatizadas de aislamiento (un usuario del tenant A nunca puede leer/escribir datos del tenant B) son un gate obligatorio de CI, no un "nice to have" (ver `19-checklist.md`).

## 4. Autenticación y autorización

- JWT de acceso (15 min) + refresh token rotativo (7 días) almacenado como cookie `httpOnly`, `secure`, `SameSite=strict`.
- RBAC modelado como `roles` ↔ `permisos` (muchos a muchos), no como enum hardcodeado — ver `14-base-de-datos.md`.
- Autorización verificada en el backend en cada endpoint (dependency de FastAPI), nunca confiada únicamente al frontend ocultando botones.

## 5. Almacenamiento

- MinIO (S3-compatible) para documentos, fotografías y evidencias.
- Subida y descarga vía **URLs prefirmadas** — el backend nunca actúa como proxy de bytes de archivos grandes.
- Cifrado en reposo (SSE) habilitado a nivel de bucket.
- Un bucket lógico por tipo de contenido (`documentos`, `evidencias`, `fotos-equipos`), con prefijo `laboratorio_id/` dentro de cada uno para organización y facilidad de purga por tenant si algún día se requiere.

## 6. Tiempo real

- WebSocket para: centro de notificaciones, actualización en vivo del Dashboard.
- Fallback automático a polling (cada 30s) si la conexión WebSocket falla o el entorno de red del cliente la bloquea.
- Un gateway de WebSocket ligero dentro del propio backend FastAPI en v1 (no un servicio separado) — se reevalúa si el volumen de conexiones concurrentes lo justifica.

## 7. Búsqueda

- PostgreSQL full-text search (`tsvector`/`tsquery`) con índices GIN sobre las entidades buscables en v1. Suficiente para el volumen esperado de un laboratorio individual. Se documenta como punto de extensión futuro (ej. OpenSearch/Meilisearch) si el volumen agregado de todos los tenants lo justifica — no se construye de entrada por sobre-ingeniería (ver `00-analisis-critico-y-recomendaciones.md`).

## 8. Infraestructura y despliegue (estado actual)

- **Docker Compose** (`docker-compose.yml`, único archivo de este tipo en el repo) es hoy exclusivamente un entorno de **desarrollo**: `frontend` corre el dev server de Vite (no un build de producción), `backend` corre Uvicorn con `--reload`. Servicios reales: `frontend`, `backend`, `worker`, `postgres`, `minio`. No existe todavía un entorno de producción desplegado en ningún lado — ver sección 11.
- **CI con GitHub Actions** (`.github/workflows/ci.yml`, verificado): en cada PR y en push a `main` corre lint (ruff/eslint) + type-check (mypy/tsc) + tests (pytest/vitest) + build del frontend, en dos jobs (`backend`, `frontend`). **No** hay ningún paso de build/push de imágenes Docker ni de despliegue — el pipeline es hoy un gate de calidad, no un pipeline de entrega continua.
- **Observabilidad v1 real**: logs estructurados en JSON emitidos a stdout de cada contenedor (`app/core/logging.py`, `TraceIdMiddleware` — correlación por `trace_id`), y health checks de Docker Compose en `postgres`, `minio`, `backend` y `worker` (`frontend` no tiene healthcheck definido). No hay ningún recolector/agregador de logs desplegado (ELK, Loki, CloudWatch, etc.) — "centralizado" hoy solo significa "estructurado y uniforme", no "reunido en un solo lugar consultable". Métricas/tracing distribuido (Prometheus/OpenTelemetry) no están implementados — ver sección 11 y `17-roadmap.md` (Fase 5).
- **Kubernetes**: no usado, explícitamente diferido — ver justificación en `00-analisis-critico-y-recomendaciones.md`, sección 3.2. La arquitectura modular permite migrar sin reescritura cuando exista evidencia operativa que lo justifique.

## 9. Puntos de extensión (para integraciones futuras sin romper el core)

- **API pública versionada** (`/api/v1`) — el propio frontend es "cliente cero" de esta API, no hay atajos internos que la salten.
- **Webhooks salientes** (ej. `calibracion.vencida`) como mecanismo genérico de integración, preferido sobre integraciones nativas puntuales (M365, Google Workspace) que se evalúan caso a caso más adelante.
- **Adaptadores de notificación** (email, push, Slack, etc.) implementados como puertos separados del outbox — agregar un canal nuevo no toca la lógica de negocio que genera la notificación.

## 10. Estructura de carpetas (real)

```
login/
├── frontend/
│   └── src/
│       ├── features/{equipos,documentos,calibraciones,...}/
│       ├── shared/{components,hooks,lib}/
│       └── app/ (routing, providers)
├── backend/
│   └── app/
│       ├── modules/{auth,equipos,documentos,calibraciones,...}/
│       │   ├── domain/
│       │   ├── application/
│       │   ├── infrastructure/
│       │   └── presentation/
│       ├── core/ (config, seguridad transversal, middleware)
│       └── worker/ (jobs de outbox, alertas, reportes async)
├── docker-compose.yml   ← único compose del repo (entorno de desarrollo, ver sección 8)
├── .github/workflows/ci.yml
└── docs/  ← este blueprint
```

No existe `docker-compose.prod.yml` — ver sección 11.

---

## 11. Arquitectura futura (roadmap de infraestructura) 🔮

Todo lo listado en esta sección es **intencionado pero no construido todavía**. Ninguno de estos componentes existe en el repositorio ni está desplegado en ningún entorno — se documentan aquí explícitamente separados del estado actual (secciones 1-10) para que nadie despliegue asumiendo que ya están, y para que sirvan de referencia cuando se prioricen en un sprint real.

| Componente futuro | Qué resolvería | Dónde viviría |
|---|---|---|
| 🔮 **Reverse proxy (Nginx u otro)** | Terminación TLS, un único origen público para frontend+backend (hoy son dos puertos distintos sin HTTPS), cabeceras de seguridad centralizadas | Nuevo servicio en un futuro `docker-compose.prod.yml` |
| 🔮 **Terminación TLS/HTTPS** | Cifrado en tránsito — hoy todo el tráfico, incluidas credenciales de login, viaja en HTTP plano en este entorno | En el reverse proxy, con certificados (Let's Encrypt o gestionados) |
| 🔮 **`docker-compose.prod.yml`** (o manifiesto equivalente) | Un despliegue de producción real: build de frontend (`npm run build` servido como estático, no el dev server de Vite), límites de recursos por contenedor (ver hallazgo de auditoría R4) — `backend/docker-entrypoint.sh` ya soporta el modo sin `--reload`/con `--workers` parametrizable vía `ENTORNO=produccion` (Fase 2/M7), pendiente de que este manifiesto exista para usarlo | Raíz del repo, junto al `docker-compose.yml` actual |
| 🔮 **Balanceador de carga** | Repartir tráfico entre múltiples réplicas de `backend` — hoy solo corre una instancia; RNF-ESC-02 (`04-requerimientos-no-funcionales.md`) ya exige que el backend sea stateless para que esto sea viable cuando se construya | Delante del reverse proxy, o el propio reverse proxy en modo balanceador |
| 🔮 **Pipeline de despliegue continuo** | El CI actual (sección 8) valida calidad pero no construye ni publica imágenes ni despliega — agregar esos pasos a `.github/workflows/ci.yml` (o un workflow nuevo) | GitHub Actions |
| 🔮 **Observabilidad centralizada** | Agregación real de logs (hoy son JSON a stdout, sin recolector) y métricas/tracing distribuido (Prometheus/OpenTelemetry) | Ver `17-roadmap.md`, Fase 5 |

**Antes de construir cualquiera de estos componentes**, actualizar esta tabla moviendo la fila correspondiente de vuelta a las secciones 1-10 con la evidencia real (archivo de configuración, servicio en `docker-compose`, etc.) — el mismo criterio de "no documentar lo que no existe" que motivó esta revisión.
