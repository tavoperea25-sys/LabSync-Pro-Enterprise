# 14 — Modelo de Base de Datos (ERD)

Motor: **PostgreSQL 16**. Todas las tablas con datos de negocio incluyen `laboratorio_id` y tienen **Row Level Security** activada (ver `13-arquitectura.md` sección 3 y `16-seguridad.md`). Toda tabla incluye `creado_en` (y la mayoría `actualizado_en`, con zona horaria); las entidades sujetas a soft delete incluyen `eliminado_en NULL`.

> **Nota de vigencia (auditoría 2026-07-31, hallazgo I11):** este documento se auditó columna por columna contra `app/modules/*/infrastructure/models.py` y las 16 migraciones de Alembic (2026-08-04). Se corrigieron nombres de columna incorrectos, se agregaron columnas y una tabla completa (`reportes_generados`) que faltaban, y se retiraron afirmaciones que no correspondían a ninguna restricción real del esquema. Donde este documento dice `ENUM(...)`, es una notación abreviada — **el proyecto no usa el tipo nativo `ENUM` de Postgres en ningún lado**; son columnas `VARCHAR` con un `CHECK` que restringe los valores (ver sección 5). Las columnas marcadas `ENUM(...)` sin nota adicional en la sección 5 no tienen `CHECK` real todavía — ver el propio listado de esa sección.

---

## 1. Diagrama entidad-relación (vista lógica)

```
laboratorios (tenant) ──┬──< usuarios >──┬── usuarios_roles ──< roles >── roles_permisos ──< permisos
                         │                │
                         │                └──< sesiones (refresh tokens)
                         │
                         ├──< categorias_equipo
                         ├──< areas
                         │
                         ├──< equipos >──┬──< calibraciones
                         │                ├──< mantenimientos
                         │                ├──< adjuntos (polimórfico — solo Calibraciones/Mantenimientos)
                         │                └──< qr_tokens ──< incidencias_qr
                         │
                         ├──< carpetas >──< documentos >──< documentos_versiones
                         │                       │
                         │                       └──< documentos_etiquetas >── etiquetas
                         │
                         ├──< alertas ──< notificaciones_pendientes (outbox)
                         ├──< eventos_calendario
                         ├──< reportes_generados
                         ├──< logs_auditoria  (append-only)
                         └──< configuraciones_laboratorio (1:1)
```

---

## 2. Definición de tablas

### `laboratorios` (tenant raíz)
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `nombre` | VARCHAR(200) NOT NULL | |
| `slug` | VARCHAR(100) NOT NULL UNIQUE | identificador corto usado en el login (`laboratorio_slug`) y en URLs — no editable desde la UI en v1 |
| `logo_object_key` | TEXT NULL | Object key en MinIO (bucket `logos`), no una URL — las de descarga son prefirmadas y expiran, nunca se persisten (renombrado desde `logo_url` en 0010, Sprint 12: nunca se había escrito antes de RF-CFG-04) |
| `estado` | VARCHAR(20) NOT NULL DEFAULT 'activo' | valores en uso: `activo`, `suspendido` — sin `CHECK` todavía, ver sección 5 |
| `creado_en` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

### `usuarios`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `laboratorio_id` | UUID FK → laboratorios | RLS aplicado |
| `correo` | VARCHAR(255) NOT NULL | UNIQUE (`laboratorio_id`, `correo`) — **no** es `CITEXT` (no se usa esa extensión en ningún lado del esquema); la comparación case-insensitive, si existe, se resuelve en la capa de aplicación |
| `password_hash` | TEXT NOT NULL | Argon2id |
| `nombre_completo` | VARCHAR(200) NOT NULL | |
| `foto_object_key` | TEXT NULL | RF-CFG-01, Sprint 25 — mismo criterio que `logo_object_key` |
| `estado` | VARCHAR(30) NOT NULL DEFAULT 'pendiente_activacion' | `CHECK` real: `activo`, `inactivo`, `pendiente_activacion` (ver sección 5) |
| `debe_cambiar_password` | BOOLEAN NOT NULL DEFAULT true | |
| `mfa_habilitado` | BOOLEAN NOT NULL DEFAULT false | reservado, sin flujo en v1 |
| `intentos_fallidos` | INT NOT NULL DEFAULT 0 | RF-AUTH-06, bloqueo progresivo — no forma parte del ERD original, agregado como extensión menor (ver docstring de `auth/infrastructure/models.py`) |
| `bloqueado_hasta` | TIMESTAMPTZ NULL | RF-AUTH-06 |
| `ultimo_login_en` | TIMESTAMPTZ NULL | |
| `creado_en` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

**Índices:** único compuesto (`laboratorio_id`, `correo`); índice sobre `laboratorio_id`.

### `roles`
`id` UUID PK · `laboratorio_id` UUID FK NULL (NULL = rol de sistema/semilla, no editable) · `nombre` VARCHAR(100) · `es_sistema` BOOLEAN

Seed de roles de sistema: `administrador`, `director_tecnico`, `calidad`, `metrologia`, `tecnico`, `consulta`.

### `permisos`
`id` UUID PK · `clave` VARCHAR(100) UNIQUE (ej. `equipos.crear`, `documentos.aprobar`, `auditoria.ver`) · `descripcion` TEXT

### `roles_permisos`
`rol_id` FK · `permiso_id` FK · PK compuesta (`rol_id`, `permiso_id`)

### `usuarios_roles`
`usuario_id` FK · `rol_id` FK · `laboratorio_id` FK NOT NULL (denormalizado a propósito, para que la política RLS de esta tabla no necesite un `JOIN` contra `usuarios`) · PK compuesta (`usuario_id`, `rol_id`) — permite múltiples roles por usuario (RF-USR-02).

### `sesiones`
`id` UUID PK · `laboratorio_id` FK NOT NULL (RLS) · `usuario_id` FK · `refresh_token_hash` TEXT UNIQUE · `expira_en` TIMESTAMPTZ · `revocada` BOOLEAN DEFAULT false · `ip_origen` INET NULL · `user_agent` TEXT NULL · `creado_en` TIMESTAMPTZ

### `categorias_equipo`
`id` UUID PK · `laboratorio_id` FK · `nombre` VARCHAR(100) · `frecuencia_calibracion_default_meses` INT NULL · `bloquea_activacion_si_calibracion_vencida` BOOLEAN NOT NULL DEFAULT false (RN-EQ-03, Sprint 17)

### `areas`
`id` UUID PK · `laboratorio_id` FK · `nombre` VARCHAR(100)

### `equipos`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `laboratorio_id` | UUID FK | RLS |
| `codigo_interno` | VARCHAR(50) NOT NULL | UNIQUE (`laboratorio_id`, `codigo_interno`) — RN-EQ-02 |
| `nombre` | VARCHAR(200) NOT NULL | |
| `categoria_id` | UUID FK → categorias_equipo NULL | |
| `marca` | VARCHAR(100) NULL | |
| `modelo` | VARCHAR(100) NULL | |
| `numero_serie` | VARCHAR(100) NULL | |
| `fabricante` | VARCHAR(150) NULL | |
| `proveedor` | VARCHAR(150) NULL | |
| `fecha_adquisicion` | DATE NULL | |
| `estado_operativo` | VARCHAR(30) NOT NULL DEFAULT 'operativo' | `CHECK` real: `operativo`, `fuera_de_servicio`, `en_mantenimiento`, `de_baja` (RN-EQ-03, ver sección 5) |
| `area_id` | UUID FK → areas NULL | |
| `responsable_id` | UUID FK → usuarios NULL | |
| `foto_url` | TEXT NULL | pese al nombre, contiene un *object key* de MinIO (bucket `fotos-equipos`), no una URL — mismo patrón que `logo_object_key`; el nombre quedó así desde el Sprint 24 y no se renombró para no romper compatibilidad de una columna ya en uso |
| `manual_object_key` | TEXT NULL | RF-EQ-01, Sprint 26 — manual de usuario (PDF), bucket `manuales-equipos` |
| `observaciones` | TEXT NULL | |
| `eliminado_en` | TIMESTAMPTZ NULL | soft delete — RN-EQ-01 |
| `creado_en` / `actualizado_en` | TIMESTAMPTZ | |

**Índices:** (`laboratorio_id`, `codigo_interno`) único; (`laboratorio_id`, `estado_operativo`); `tsvector` GIN sobre `nombre || numero_serie || codigo_interno` para búsqueda. `categoria_id`, `area_id` y `responsable_id` **no** tienen índice propio — hallazgo de auditoría pendiente (I4), ver sección 4.

### `calibraciones`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `laboratorio_id` | UUID FK | RLS |
| `equipo_id` | UUID FK → equipos | |
| `fecha_calibracion` | DATE NOT NULL | ≤ hoy — validado solo en la capa de aplicación (RF-CAL), **no** hay `CHECK` en base de datos pese a lo que decía una versión anterior de este documento |
| `frecuencia_meses` | INT NOT NULL | `CHECK (frecuencia_meses > 0)` — este sí es real, ver sección 5 |
| `proxima_fecha` | DATE NOT NULL | calculada = fecha_calibracion + frecuencia (RN-CAL-03) |
| `laboratorio_proveedor` | VARCHAR(200) NULL | |
| `numero_certificado` | VARCHAR(100) NULL | |
| `resultado` | VARCHAR(20) NOT NULL | `CHECK` real: `conforme`, `no_conforme` (RN-CAL-04, ver sección 5) |
| `incertidumbre` | NUMERIC(10,4) NULL | |
| `responsable_id` | UUID FK → usuarios NULL | |
| `certificado_adjunto_id` | UUID FK → adjuntos NULL | |
| `corrige_a_id` | UUID FK → calibraciones NULL | auto-referencia — RN-CAL-02 |
| `motivo_correccion` | TEXT NULL | obligatorio en la capa de aplicación cuando `corrige_a_id` no es nulo; no listado en una versión anterior de este documento |
| `observaciones` | TEXT NULL | |
| `creado_en` | TIMESTAMPTZ | |

**Índices:** (`equipo_id`, `proxima_fecha`) — clave para el cálculo de semáforo y listados de "próximos a vencer"; (`laboratorio_id`, `proxima_fecha`). `responsable_id`, `certificado_adjunto_id` y `corrige_a_id` no tienen índice propio (I4).

**Sin `eliminado_en`** deliberadamente — RN-CAL-02 prohíbe eliminación física o lógica, solo corrección referenciada.

### `mantenimientos`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `laboratorio_id` | UUID FK | RLS |
| `equipo_id` | UUID FK → equipos | |
| `tipo` | VARCHAR(30) NOT NULL | `CHECK` real: `preventivo`, `correctivo`, `predictivo`, `calibracion_correctiva` (ver sección 5) |
| `estado` | VARCHAR(20) NOT NULL DEFAULT 'programado' | `CHECK` real: `programado`, `en_ejecucion`, `completado`, `cancelado` (ver sección 5) |
| `fecha_programada` | DATE NULL | |
| `fecha_ejecutada` | DATE NULL | obligatoria para cerrar — RN-MANT-02 |
| `tecnico_responsable_id` | UUID FK → usuarios NULL | |
| `descripcion` | TEXT NULL | |
| `repuestos_utilizados` | TEXT NULL | |
| `tiempo_inactividad_horas` | NUMERIC(8,2) NULL | |
| `costo` | NUMERIC(12,2) NULL | |
| `informe_adjunto_id` | UUID FK → adjuntos NULL | |
| `frecuencia_meses` | INT NULL | mantenimientos preventivos recurrentes — no listado en una versión anterior de este documento |
| `generado_de_id` | UUID FK → mantenimientos NULL | auto-referencia — enlaza un mantenimiento generado automáticamente con el que lo originó |

**Índices:** (`equipo_id`, `fecha_programada`); (`laboratorio_id`, `estado`); (`tecnico_responsable_id`, `fecha_programada`). `informe_adjunto_id` y `generado_de_id` no tienen índice propio (I4).

### `carpetas`
`id` UUID PK · `laboratorio_id` FK · `nombre` VARCHAR(150) · `carpeta_padre_id` UUID FK → carpetas NULL (jerarquía)

### `documentos`
| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | identidad lógica del documento (estable entre versiones) |
| `laboratorio_id` | UUID FK | RLS |
| `carpeta_id` | UUID FK → carpetas NULL | |
| `nombre` | VARCHAR(255) NOT NULL | |
| `categoria` | VARCHAR(100) NULL | |
| `estado` | VARCHAR(20) NOT NULL DEFAULT 'vigente' | `CHECK` real: `vigente`, `obsoleto`, `en_revision` (RN-DOC-01, RN-DOC-02, ver sección 5) |
| `fecha_emision` | DATE NULL | |
| `fecha_vencimiento` | DATE NULL | `CHECK (fecha_vencimiento IS NULL OR fecha_emision IS NULL OR fecha_vencimiento > fecha_emision)` — RN-DOC-04 |
| `responsable_aprobacion_id` | UUID FK → usuarios NULL | |
| `version_vigente_id` | UUID FK → documentos_versiones NULL | |
| `eliminado_en` | TIMESTAMPTZ NULL | papelera, purga tras ventana configurable — RN-DOC-03 |

**Índices:** (`laboratorio_id`); (`laboratorio_id`, `carpeta_id`); `tsvector` GIN para búsqueda. `responsable_aprobacion_id` y `version_vigente_id` no tienen índice propio (I4).

### `documentos_versiones`
`id` UUID PK · `laboratorio_id` FK NOT NULL (RLS — no listado en una versión anterior de este documento) · `documento_id` FK → documentos · `numero_version` INT · `object_key` TEXT (referencia al objeto en MinIO — **no** `archivo_url`, nombre corregido) · `nombre_archivo` VARCHAR(255) NOT NULL (no listado antes) · `tamano_bytes` BIGINT · `tipo_mime` VARCHAR(100) · `subido_por_id` FK → usuarios NULL · `aprobado_por_id` FK → usuarios NULL · `aprobado_en` TIMESTAMPTZ NULL

**Único** (`documento_id`, `numero_version`). Índices: (`laboratorio_id`); (`documento_id`). `subido_por_id` y `aprobado_por_id` no tienen índice propio (I4).

### `etiquetas` / `documentos_etiquetas`
`etiquetas`: `id` UUID PK · `laboratorio_id` FK · `nombre` VARCHAR(60)
`documentos_etiquetas`: PK compuesta (`documento_id`, `etiqueta_id`) · `etiqueta_id` no tiene índice propio (I4)

### `documentos_favoritos`
`documento_id` FK · `usuario_id` FK · `laboratorio_id` FK (índice propio) — no listada en una versión anterior de este documento; respalda RF-DOC (marcar/filtrar favoritos).

### `adjuntos` (tabla polimórfica — reutilizada por Calibraciones y Mantenimientos, **no** por Equipos)
`id` UUID PK · `laboratorio_id` FK · `entidad_tipo` VARCHAR(50) · `entidad_id` UUID · `object_key` TEXT (no `archivo_url`) · `nombre_archivo` VARCHAR(255) (no listado antes) · `tamano_bytes` BIGINT (no listado antes) · `tipo_mime` VARCHAR(100) · `subido_por_id` FK usuarios NULL

`CHECK` real sobre `entidad_tipo` (ver sección 5): `mantenimiento_evidencia`, `mantenimiento_informe`, `calibracion_certificado`. Los valores `equipo_manual`/`equipo_foto` que aparecían en una versión anterior de este documento **no existen** — la foto y el manual de un equipo se guardan directamente en columnas de `equipos` (`foto_url`, `manual_object_key`), no en esta tabla polimórfica.

**Índice:** (`entidad_tipo`, `entidad_id`); (`laboratorio_id`).

### `alertas`
`id` UUID PK · `laboratorio_id` FK · `tipo` VARCHAR(20) · `origen_tipo` VARCHAR(30) · `origen_id` UUID · `mensaje` TEXT · `estado` VARCHAR(20) DEFAULT 'activa' · `leida_en` TIMESTAMPTZ NULL (no listado antes) · `resuelta_por_id` FK usuarios NULL · `resuelta_en` TIMESTAMPTZ NULL

`CHECK` real (ver sección 5): `tipo` ∈ {`critica`,`preventiva`}, `estado` ∈ {`activa`,`resuelta`}, `origen_tipo` ∈ {`calibracion`,`documento`,`mantenimiento`,`equipo`}.

**Índices:** (`laboratorio_id`, `estado`); (`origen_tipo`, `origen_id`). `resuelta_por_id` no tiene índice propio (I4).

**Restricción única lógica** (aplicada en capa de aplicación, RN-ALT-01): no duplicar alerta activa para el mismo (`origen_tipo`, `origen_id`, `tipo`) no resuelta.

### `notificaciones_pendientes` (outbox — RF-ALT-05)
`id` UUID PK · `laboratorio_id` FK · `alerta_id` FK → alertas NOT NULL (no listado antes — el outbox está diseñado para notificaciones originadas por una alerta; el evento "reporte listo" no pasa por esta tabla, ver el docstring de `app/worker/main.py`) · `canal` VARCHAR(20) · `payload` JSONB · `estado` VARCHAR(20) DEFAULT 'pendiente' · `intentos` INT DEFAULT 0 · `procesado_en` TIMESTAMPTZ NULL

`CHECK` real (ver sección 5): `canal` ∈ {`websocket`,`email`,`push`}, `estado` ∈ {`pendiente`,`enviado`,`fallido`}. `alerta_id` no tiene índice propio (I4).

### `eventos_calendario`
`id` UUID PK · `laboratorio_id` FK · `tipo` VARCHAR(30) · `titulo` VARCHAR(255) · `descripcion` TEXT NULL (no listado antes) · `fecha` TIMESTAMPTZ · `origen_tipo` VARCHAR(50) NULL · `origen_id` UUID NULL · `creado_por_id` FK usuarios NULL (NULL si es generado por el sistema)

`CHECK` real sobre `tipo`: `calibracion`, `mantenimiento`, `auditoria`, `capacitacion`, `vencimiento_documental`, `institucional` — de estos, solo `auditoria`/`capacitacion`/`institucional` se materializan como filas; el resto se sintetiza en el momento de la lectura a partir de `calibraciones.proxima_fecha`, `mantenimientos.fecha_programada` y `documentos.fecha_vencimiento` (ver el docstring de `alembic/versions/0008_calendario_busqueda.py` — no hay una sección dedicada a Calendario en `13-arquitectura.md`). `creado_por_id` no tiene índice propio (I4).

**Índices:** (`laboratorio_id`); (`laboratorio_id`, `fecha`).

### `reportes_generados` (RF-REP, RNF-PERF-04 — Sprint 11) — tabla ausente por completo de una versión anterior de este documento
`id` UUID PK · `laboratorio_id` FK · `tipo` VARCHAR(40) · `formato` VARCHAR(10) · `filtros` JSONB NULL · `estado` VARCHAR(20) DEFAULT 'pendiente' · `object_key` TEXT NULL · `nombre_archivo` VARCHAR(255) NULL · `error` TEXT NULL · `solicitado_por_id` FK usuarios NULL · `creado_en` TIMESTAMPTZ · `completado_en` TIMESTAMPTZ NULL

`CHECK` real sobre `tipo`, `formato` y `estado` (los 7 tipos de reporte, los formatos `csv`/`xlsx`/`pdf`, y `pendiente`/`procesando`/`listo`/`fallido` — este último valor, `procesando`, está permitido por el `CHECK` pero el worker nunca transiciona a él hoy, ver informe de auditoría). Si el volumen supera el umbral de RNF-PERF-04, el reporte se genera de forma asíncrona (worker) en vez de en la misma petición HTTP. **Índice:** (`laboratorio_id`). `solicitado_por_id` no tiene índice propio (I4).

### `logs_auditoria` (append-only — RN-AUD-01)
`id` UUID PK · `laboratorio_id` FK **NOT NULL** (corregido — una versión anterior de este documento decía "NULL para acciones de plataforma/Superadmin"; esa función no existe todavía, así que hoy la columna es obligatoria, ver docstring de la migración 0003) · `usuario_id` FK usuarios NULL · `ip_origen` INET NULL · `modulo` VARCHAR(50) · `accion` VARCHAR(50) · `entidad_tipo` VARCHAR(50) — deliberadamente **sin** `CHECK`: es un valor de texto libre que cada módulo define al registrar su propia auditoría (`documento`, `usuario`, `equipo`, `calibracion`, `reporte`, etc.), restringirlo rompería la extensibilidad · `entidad_id` UUID NULL · `valor_anterior` JSONB NULL · `valor_nuevo` JSONB NULL · `creado_en` TIMESTAMPTZ NOT NULL DEFAULT now()

**A nivel de base de datos:** el rol de aplicación tiene permisos `INSERT`, `SELECT` únicamente sobre esta tabla — `UPDATE`/`DELETE` revocados incluso para el rol de administración de la aplicación (solo accesibles por un rol de mantenimiento de infraestructura fuera del flujo normal). **Índice:** (`laboratorio_id`) y un índice `tsvector` adicional para búsqueda global.

### `qr_tokens`
`id` UUID PK · `laboratorio_id` FK (no listado antes) · `equipo_id` FK UNIQUE · `token` VARCHAR(64) UNIQUE (aleatorio, no adivinable — RN-QR-01) · `revocado` BOOLEAN DEFAULT false · `creado_en` TIMESTAMPTZ

### `incidencias_qr`
`id` UUID PK · `laboratorio_id` FK (no listado antes) · `equipo_id` FK · `descripcion` TEXT · `contacto_nombre` VARCHAR(150) NULL · `contacto_medio` VARCHAR(150) NULL · `estado` VARCHAR(20) DEFAULT 'pendiente' · `creado_en` TIMESTAMPTZ

`CHECK` real sobre `estado`: `pendiente`, `en_revision`, `resuelta` (ver sección 5). **Índice:** (`laboratorio_id`).

### `configuraciones_laboratorio`
`laboratorio_id` PK/FK (1:1) · `umbral_alerta_calibracion_dias` INT NOT NULL DEFAULT 30 (`CHECK > 0`) · `umbral_alerta_mantenimiento_dias` INT NOT NULL DEFAULT 15 (`CHECK > 0`) · `umbral_alerta_documento_dias` INT NOT NULL DEFAULT 30 (`CHECK > 0`) · `dias_retencion_papelera_documentos` INT NOT NULL DEFAULT 30 (RN-DOC-03, Sprint 19) · `politica_password_json` JSONB NULL · `mapeo_estados_mantenimiento_json` JSONB NULL (RN-MANT-01, Sprint 14) · `actualizado_en` TIMESTAMPTZ

---

## 3. Row Level Security (patrón aplicado a toda tabla con `laboratorio_id`)

```sql
ALTER TABLE equipos ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipos FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_equipos ON equipos
  USING (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
  WITH CHECK (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
```

(`NULLIF(..., '')` y el segundo argumento `true` de `current_setting` hacen que la política falle de forma segura — cero filas — en vez de lanzar un error de Postgres, si por algún motivo la variable de sesión nunca se fijó; `FORCE ROW LEVEL SECURITY` es necesario porque el rol de aplicación es el dueño de las tablas, y sin ese `FORCE` Postgres exime a los dueños de tabla de sus propias políticas RLS.)

El backend establece `app.current_tenant_id` al inicio de cada transacción (`SET LOCAL`, se pierde en cada `COMMIT`/`ROLLBACK` — hay que refijarlo después), derivado del `laboratorio_id` embebido en el JWT validado — nunca de un parámetro de la petición controlable por el cliente. `laboratorios` es la única tabla sin RLS (es el tenant raíz, no tiene un `laboratorio_id` propio).

## 4. Optimización

- Índices compuestos donde el patrón de consulta es predecible (`equipo_id + proxima_fecha`, `laboratorio_id + estado_operativo`, etc. — ver el detalle por tabla en la sección 2).
- **Corrección de una afirmación anterior:** este documento decía "todas las claves foráneas indexadas explícitamente" — **no es así**. Postgres no indexa FKs automáticamente, y hay ~20 columnas FK sin índice propio en `equipos`, `documentos`, `calibraciones`, `mantenimientos`, `alertas`, `roles`, `usuarios_roles`, `carpetas`, `documentos_versiones`, `documentos_etiquetas`, `notificaciones_pendientes`, `eventos_calendario` y `reportes_generados` — señaladas individualmente en la sección 2 (hallazgo de auditoría I4, pendiente al momento de escribir esto). Bajo el volumen actual del proyecto el impacto es bajo; se agravará con el crecimiento de tablas historizadas.
- `tsvector` + índice GIN para búsqueda global (Módulo 9) — sobre `equipos`, `documentos`, `usuarios`, `calibraciones`, `mantenimientos` y `logs_auditoria`.
- Particionamiento de `logs_auditoria` por rango de fecha (mensual) contemplado como optimización de Fase 3+ si el volumen lo justifica — no se implementa prematuramente en v1.

## 5. Restricciones de integridad relevantes

**Migración 0016 (2026-08-04, corrección del hallazgo crítico C1 de la auditoría 2026-07-31)** agregó `CHECK` reales a las columnas de tipo/estado que antes solo se validaban en la capa de aplicación. Estado actual, tabla por tabla:

| Tabla.columna | Valores permitidos por el `CHECK` |
|---|---|
| `usuarios.estado` | `activo`, `inactivo`, `pendiente_activacion` |
| `equipos.estado_operativo` | `operativo`, `fuera_de_servicio`, `en_mantenimiento`, `de_baja` |
| `documentos.estado` | `vigente`, `obsoleto`, `en_revision` |
| `calibraciones.resultado` | `conforme`, `no_conforme` |
| `mantenimientos.tipo` | `preventivo`, `correctivo`, `predictivo`, `calibracion_correctiva` |
| `mantenimientos.estado` | `programado`, `en_ejecucion`, `completado`, `cancelado` |
| `alertas.tipo` | `critica`, `preventiva` |
| `alertas.estado` | `activa`, `resuelta` |
| `alertas.origen_tipo` | `calibracion`, `documento`, `mantenimiento`, `equipo` |
| `notificaciones_pendientes.estado` | `pendiente`, `enviado`, `fallido` |
| `notificaciones_pendientes.canal` | `websocket`, `email`, `push` |
| `incidencias_qr.estado` | `pendiente`, `en_revision`, `resuelta` |
| `adjuntos.entidad_tipo` | `mantenimiento_evidencia`, `mantenimiento_informe`, `calibracion_certificado` |

Ya existían desde su creación (no forman parte de la migración 0016): `eventos_calendario.tipo`, `reportes_generados.tipo`/`formato`/`estado`.

**Sin `CHECK` todavía** (deliberadamente en el caso de `logs_auditoria.entidad_tipo`, ver sección 2; pendiente sin decisión tomada para `laboratorios.estado`):
- `laboratorios.estado` — solo 2 valores en uso hoy (`activo`/`suspendido`), sin restricción real. No estaba en el alcance de la migración 0016 porque no se detectó en la auditoría original; queda anotado aquí para una futura pasada.

**Otras restricciones reales:**
- `CHECK (fecha_vencimiento IS NULL OR fecha_emision IS NULL OR fecha_vencimiento > fecha_emision)` en `documentos`.
- `CHECK (frecuencia_meses > 0)` en `calibraciones`.
- `CHECK (umbral_alerta_*_dias > 0)` (los 3) en `configuraciones_laboratorio`.
- Únicos: (`laboratorio_id`,`correo`) en `usuarios`; (`laboratorio_id`,`codigo_interno`) en `equipos`; (`laboratorio_id`,`nombre`) en `categorias_equipo` y `areas`; (`documento_id`,`numero_version`) en `documentos_versiones`; `token` en `qr_tokens`; `equipo_id` en `qr_tokens`; `refresh_token_hash` en `sesiones`; `slug` en `laboratorios`; `clave` en `permisos`.

**Corrección de una afirmación anterior:** este documento decía *"`CHECK (fecha_calibracion <= CURRENT_DATE)` en `calibraciones`"* — **no existe tal `CHECK`**; esa validación es solo de la capa de aplicación (`calibracion_service.py`). También decía *"`ON DELETE RESTRICT` en todas las FK hacia `equipos`, `usuarios` y `laboratorios`"* — ninguna definición de FK del esquema especifica `ondelete=` explícitamente; el comportamiento por defecto de Postgres sin esa cláusula (`NO ACTION`) produce en la práctica un efecto similar (bloquea el `DELETE` si hay filas referenciando), pero no es lo mismo que un `RESTRICT` declarado, y no se comprobó exhaustivamente para las ~40 FKs del esquema.
