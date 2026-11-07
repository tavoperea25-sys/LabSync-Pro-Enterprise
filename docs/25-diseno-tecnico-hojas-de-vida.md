# 25 — Diseño técnico: hojas de vida, mantenimiento y firmas (Fase 1)

**Proyecto:** LabSync Pro Enterprise
**Autor:** Claude Code (auditoría y diseño, sin código) — a partir de `docs/24-especificacion-hojas-de-vida-mantenimiento-firmas.md`
**Estado:** Borrador para aprobación de Gustavo Perea. No contiene cambios de código, modelos ni migraciones — solo diseño.
**Rama:** `docs/diseno-hojas-de-vida` (PR hacia `develop`)

> Este documento responde punto por punto al prompt de la Fase 1 (sección 7 de `docs/24-...md`). Cada vez que el
> diseño se aparta de la especificación original, se marca explícitamente como **[CORRECCIÓN PROPUESTA]** con el
> motivo y la alternativa — nunca se implementa en silencio una divergencia.

---

## 1. Mapa de lo existente

Arquitectura confirmada: todos los módulos siguen `domain/ports.py` + `domain/entities.py` →
`application/*_service.py` → `infrastructure/{models,repositories}.py` → `presentation/{router,schemas}.py`.
Inyección de dependencias manual por request (sin contenedor DI); permisos vía
`Depends(requiere_permiso("<modulo>.<accion>"))` (`backend/app/modules/auth/presentation/dependencies.py`).
RLS: cada migración define su propio helper local `_habilitar_rls(tabla)` que hace
`ENABLE/FORCE ROW LEVEL SECURITY` + `CREATE POLICY tenant_isolation_<tabla>` comparando
`laboratorio_id` contra `current_setting('app.current_tenant_id')`, y luego `GRANT ... TO labsync_app`
(ver [0007_mantenimientos_alertas.py](../backend/alembic/versions/0007_mantenimientos_alertas.py)). No existe
hoy ningún trigger de base de datos en el proyecto (ver sección 5.4).

### 1.1 Equipos

| Pieza | Ruta | Qué hace hoy |
|---|---|---|
| `Equipo` (modelo) | [backend/app/modules/equipos/infrastructure/models.py](../backend/app/modules/equipos/infrastructure/models.py) | Tabla `equipos`: código interno, nombre, categoría, marca/modelo/serie, **`fabricante`/`proveedor` como `String` libre**, fecha adquisición, `estado_operativo`, área, `foto_object_key` (columna física `foto_url`), `manual_object_key`, observaciones, soft delete (`eliminado_en`). |
| `CategoriaEquipo`, `Area` | mismo archivo | Catálogos por laboratorio; `CategoriaEquipo.frecuencia_calibracion_default_meses` ya existe — es la frecuencia **por defecto** que hoy alimenta el semáforo de calibraciones. |
| Entidades de dominio | [equipos/domain/entities.py](../backend/app/modules/equipos/domain/entities.py) | `ESTADOS_OPERATIVOS = (operativo, fuera_de_servicio, en_mantenimiento, de_baja)`. `Equipo.esta_activo()`. |
| `EquipoService` | [equipos/application/equipo_service.py](../backend/app/modules/equipos/application/equipo_service.py) | CRUD, `duplicar()` (excluye historial a propósito), `historial()`. |
| Router | [equipos/presentation/router.py](../backend/app/modules/equipos/presentation/router.py) | `GET/POST /equipos`, `PATCH/DELETE /equipos/{id}`, `POST /equipos/{id}/duplicar`, **`GET /equipos/{id}/historial`**, `upload-url/foto`, `upload-url/manual`, CRUD de `categorias-equipo` y `areas`. |
| Frontend | [frontend/src/features/equipos/components/EquipoFormPage.tsx](../frontend/src/features/equipos/components/EquipoFormPage.tsx), `EquipoDetailPage.tsx`, `EquiposListPage.tsx` | Formulario de una sola página (sin pestañas), con subida de foto y manual (presigned URL + `PUT` directo a MinIO). `EquipoDetailPage` ya compone `CalibracionesSection` + `MantenimientosSection` + un visor de auditoría (`camposCambiados`, diff antes/después) + sección QR. |

> **Hallazgo clave:** `GET /equipos/{id}/historial` **ya existe, pero es la bitácora de auditoría**
> (`equipo_service.historial()` llama a `auditoria.listar_por_entidad("equipo", equipo_id)`, es decir filas de
> `logs_auditoria` con diffs de campos), **no** una vista de intervenciones metrológicas. El nuevo "historial
> unificado" de la hoja de vida (sección 4) necesita su **propio endpoint**, con un nombre distinto, para no
> chocar con este. Detalle en sección 7.

### 1.2 Mantenimientos

| Pieza | Ruta | Qué hace hoy |
|---|---|---|
| `Mantenimiento` (modelo) | [mantenimientos/infrastructure/models.py](../backend/app/modules/mantenimientos/infrastructure/models.py) | `tipo`, `estado`, fechas programada/ejecutada, técnico, `descripcion`, **`repuestos_utilizados` como `Text` libre**, `tiempo_inactividad_horas`, `costo`, `informe_adjunto_id` (FK único a `adjuntos`, informe subido manualmente), `frecuencia_meses`, `generado_de_id` (autogeneración de preventivos recurrentes). |
| Dominio | [mantenimientos/domain/entities.py](../backend/app/modules/mantenimientos/domain/entities.py) | `TIPOS_MANTENIMIENTO = (preventivo, correctivo, predictivo, calibracion_correctiva)`. `ESTADOS_MANTENIMIENTO = (programado, en_ejecucion, completado, cancelado)` — **esto es el ciclo de ejecución, no el de firma**. `estado_operativo_para_tipo()` resuelve a qué `estado_operativo` del equipo pasa, con override por laboratorio (migración 0011, ver sección 3). |
| `MantenimientoService` | [mantenimientos/application/mantenimiento_service.py](../backend/app/modules/mantenimientos/application/mantenimiento_service.py) | Máquina de estados explícita: `crear` (nace `programado`) → `iniciar` → `cerrar` (exige `fecha_ejecutada`, autogenera el siguiente si es preventivo recurrente) / `cancelar`. Evidencias: `agregar_evidencia`/`listar_evidencias` (adjuntos con `entidad_tipo="mantenimiento_evidencia"`, **sin** columna de "momento"). Informe: `asignar_informe` sube un PDF ya hecho por el usuario (no lo genera el sistema). |
| Router | [mantenimientos/presentation/router.py](../backend/app/modules/mantenimientos/presentation/router.py) | `POST /mantenimientos`, `GET /mantenimientos` (paginado), `{id}/iniciar`, `{id}/cerrar`, `{id}/cancelar`, `{id}/evidencias`, `{id}/informe`, `{id}/informe-url`, `upload-url/evidencia`, `upload-url/informe`, `/mantenimientos/hoy`, `/mantenimientos/inactividad`. |
| Frontend | [frontend/src/features/mantenimientos/components/](../frontend/src/features/mantenimientos/components/) `MantenimientoFormulario.tsx`, `CerrarMantenimientoFormulario.tsx`, `MantenimientosSection.tsx`, `MisMantenimientosHoyWidget.tsx` | Formularios separados para crear y para cerrar (cierre = formulario de "resultado"), coherente con la máquina de estados del backend. |

### 1.3 Calibraciones

| Pieza | Ruta | Qué hace hoy |
|---|---|---|
| `Calibracion` (modelo) | [calibraciones/infrastructure/models.py](../backend/app/modules/calibraciones/infrastructure/models.py) | `fecha_calibracion`, `frecuencia_meses` **por registro** (no por equipo), `proxima_fecha` (calculada y guardada al crear), `resultado` (conforme/no_conforme), certificado adjunto, **`corrige_a_id` + `motivo_correccion`** — ya existe un patrón de "corrección sin borrar" muy parecido al que pide la especificación para mantenimientos. |
| Dominio | [calibraciones/domain/entities.py](../backend/app/modules/calibraciones/domain/entities.py) | `calcular_proxima_fecha()` (con *clamp* de fin de mes), `semaforo()` (verde/amarillo/rojo/gris según `UMBRAL_ALERTA_CALIBRACION_DIAS`, configurable por laboratorio). `EquipoConSemaforo` ya es, en los hechos, un mini-"cronograma" **solo para calibración**. |
| Router | [calibraciones/presentation/router.py](../backend/app/modules/calibraciones/presentation/router.py) | `POST /calibraciones`, `GET /calibraciones`, `GET /calibraciones/criticas` (el semáforo), `{id}/corregir`. |

No existe ningún modelo de **calificación** ni **verificación interna** hoy — ver hallazgo en sección 7.

### 1.4 Documentos y adjuntos

| Pieza | Ruta | Qué hace hoy |
|---|---|---|
| `Documento`/`VersionDocumento` | [documentos/infrastructure/models.py](../backend/app/modules/documentos/infrastructure/models.py) | Gestor documental de **documentos de calidad del laboratorio** (SOP, formatos, etc.): carpetas, versiones, estado `vigente/obsoleto/en_revision`, aprobación, papelera con retención configurable. **No tiene `equipo_id`** — no está pensado para colgar un archivo de un equipo puntual. |
| `Adjunto` (modelo) | [adjuntos/infrastructure/models.py](../backend/app/modules/adjuntos/infrastructure/models.py) | Tabla polimórfica genérica: `entidad_tipo` + `entidad_id` + `object_key`. **Ya es el mecanismo real para "colgar un archivo de una entidad arbitraria"**, pero `entidad_tipo` tiene un `CHECK` cerrado desde la migración 0016: `('mantenimiento_evidencia', 'mantenimiento_informe', 'calibracion_certificado')`. Para "hoja de vida física escaneada" y las nuevas evidencias con "momento", este `CHECK` debe extenderse (sección 2). |
| `AlmacenamientoPort` | [documentos/domain/ports.py](../backend/app/modules/documentos/domain/ports.py) | Contrato MinIO compartido: `url_subida`, `url_descarga`, `url_vista_previa`, `copiar_objeto`, `eliminar_objeto`. El backend **nunca** transporta el binario — firma URLs y el frontend sube/baja directo a MinIO. Los nuevos flujos (snapshot PDF, firmas) deben seguir este mismo contrato. |

### 1.5 Reportes (PDF existentes)

| Pieza | Ruta | Qué hace hoy |
|---|---|---|
| `ReporteGenerado` | [reportes/infrastructure/models.py](../backend/app/modules/reportes/infrastructure/models.py) | **Jobs de exportación** (inventario, calibraciones, vencidos, cumplimiento, paquete de auditoría…), síncronos o async según volumen (`UMBRAL_ASINCRONO`), estado `pendiente/procesando/listo/fallido`. Es un patrón de "cola de trabajos", no de "documento legal inmutable". |
| `exportadores.py` | [reportes/infrastructure/exportadores.py](../backend/app/modules/reportes/infrastructure/exportadores.py) | Usa `fpdf2` (`FPDF`). **Dato crítico para el diseño del PDF FOR-003/FOR-005:** la fuente core `Helvetica` de fpdf2 es Latin-1 — ya existe un helper `_texto_pdf()` que normaliza caracteres fuera de rango (p. ej. raya "—" → guion normal) para evitar `FPDFUnicodeEncodingException`. También existe `_agregar_logo_encabezado(pdf, logo_bytes)` para el logo institucional (`Laboratorio.logo_object_key`, [auth/infrastructure/models.py](../backend/app/modules/auth/infrastructure/models.py)). **Los nuevos generadores de FOR-003/FOR-005 deben reutilizar estos dos helpers**, no reimplementarlos. |

### 1.6 Configuración (donde vive la versión de formato)

[configuracion/infrastructure/models.py](../backend/app/modules/configuracion/infrastructure/models.py): fila única
por laboratorio (`laboratorio_id` es PK), con varios `*_json` JSONB ya existentes
(`politica_password_json`, `mapeo_estados_mantenimiento_json`). Es el lugar natural para la nueva
`versiones_formato_json` (sección 3.6 de la especificación).

### 1.7 Convenciones de frontend confirmadas

- Formularios: `react-hook-form` + `zodResolver`, esquema con **zod 4** real (`z.string().min(1, { error: "..." })`,
  `z.enum([...])`) — visto en
  [EquipoFormPage.tsx](../frontend/src/features/equipos/components/EquipoFormPage.tsx). Los esquemas de la
  sección 6 siguen exactamente esta sintaxis.
- Subida de archivos: pedir `url_subida` + `object_key` al backend, `fetch(url_subida, { method: "PUT", body: archivo })` directo a MinIO, y solo entonces mandar el `object_key` al guardar el formulario (nunca se omite un `object_key` ya existente al reenviar, para no borrar el archivo actual).
- **No existe hoy ningún componente de pestañas** (`frontend/src/shared/components/ui/` solo tiene `badge`,
  `button`, `checkbox`, `empty-state`, `input`, `link-button`, `select`, `skeleton`, `subir-foto-con-preview`,
  `textarea`). El formulario de ficha técnica "por pestañas" (Fase 2) requiere **crear un componente `Tabs`
  nuevo** en `shared/components/ui/`.
- `signature_pad` **no está** en `frontend/package.json` — es una dependencia nueva a agregar en la Fase 5.

---

## 2. Modelo de datos final

Convención confirmada en migraciones reales: `UUID` PK, `laboratorio_id` FK + RLS, `CHECK` constraints para
toda columna tipo-enum (migración 0016, por auditoría previa — "la aplicación no debe ser la única barrera").
Toda tabla/columna nueva de este desarrollo sigue el mismo patrón.

Numeración planeada (siguiente libre: `0018`, después de `0017_sesion_duracion_y_gracia.py`). Se agrupan por
fase de entrega (sección 5 de la especificación) para que cada PR traiga sus propias migraciones:

| # | Migración planeada | Fase | Contenido |
|---|---|---|---|
| 0018 | `catalogos_proveedor_fabricante` | 2 | Crea `proveedores`, `fabricantes`. Agrega `equipos.proveedor_id`, `equipos.fabricante_id` (FK nullable). **No borra** `equipos.proveedor`/`fabricante` (texto) todavía. |
| 0019 | `equipos_ficha_tecnica` | 2 | Agrega a `equipos`: `capitulo`, `grupo`, `subgrupo`, `ubicacion`, `numero_inventario`, `condicion_fisica`, `clasificacion_riesgo`, `criticidad`, `forma_adquisicion`, `garantia`, `garantia_inicio`, `garantia_fin` + sus `CHECK`. Crea `equipo_ficha_tecnica` (1:1, PK = `equipo_id`). |
| 0020 | `equipo_accesorios_manuales` | 2 | Crea `equipo_accesorios`, `equipo_manuales`. Migra el valor actual de `equipos.manual_object_key` (si no es nulo) a una fila de `equipo_manuales` — ver riesgo en sección 7 (no se sabe su "tipo" real). |
| 0021 | `cronograma_metrologico` | 3 | Ver **[CORRECCIÓN PROPUESTA]** en sección 3.3: tabla reducida, sin fechas cacheadas. |
| 0022 | `equipo_novedades` | 3 | Tabla simple: `equipo_id`, `tipo` (falla/traslado/cambio_estado/baja), `descripcion`, `responsable_id`, `creado_en`. |
| 0023 | `adjuntos_hoja_vida_escaneada` | 3 | `ALTER` del `CHECK ck_adjuntos_entidad_tipo` para agregar `'equipo_hoja_vida_escaneada'` (drop + recreate, mismo patrón que si se agregara un valor a cualquier `CHECK` de dominio cerrado). |
| 0024 | `mantenimientos_estado_documento` | 4 | Agrega a `mantenimientos`: `estado_documento`, `falla_reportada`, `actividades_realizadas`, `comentarios`, `resultado`, `recomendaciones`, `estado_final_equipo`, `anulado_en`, `anulado_por`, `motivo_anulacion`, `reemplaza_a_id`, `consecutivo`. `CHECK ck_mantenimientos_estado_documento`. **Además** extiende `ck_mantenimientos_tipo` con `'calificacion'` y `'verificacion_interna'` — ver sección 7. |
| 0025 | `plantillas_checklist` | 4 | `plantillas_checklist`, `plantilla_checklist_items`, `mantenimiento_checklist`. |
| 0026 | `mantenimiento_repuestos_evidencias` | 4 | `mantenimiento_repuestos`; `mantenimiento_evidencias` (FK a `adjuntos.id` + columna `momento`, en vez de duplicar columnas de archivo — ver sección 2.1). Migra `repuestos_utilizados` texto a filas de `mantenimiento_repuestos` (best-effort, sin borrar el texto original). |
| 0027 | `firmas` | 5 | Tabla `firmas` + trigger de inmutabilidad (sección 5.4). |
| 0028 | `documentos_generados` | 5 | Tabla `documentos_generados` + trigger de inmutabilidad + `configuraciones_laboratorio.versiones_formato_json`. |

### 2.1 Correcciones puntuales a la sección 4 de la especificación

- **`mantenimiento_evidencias` no debe duplicar columnas de archivo.** El módulo `adjuntos` ya resuelve
  `object_key`/`nombre_archivo`/`tamano_bytes`/`tipo_mime`/`subido_por_id` de forma polimórfica y ya se usa
  para evidencias de mantenimiento. Diseño: `mantenimiento_evidencias(id, laboratorio_id, mantenimiento_id,
  adjunto_id FK adjuntos.id, momento CHECK IN ('antes','durante','despues','otro'))`. El `AdjuntoRepository`
  no cambia; solo se agrega esta tabla puente. Las evidencias **existentes** (ya subidas vía
  `agregar_evidencia`, con `entidad_tipo='mantenimiento_evidencia'` y sin "momento") se migran con
  `momento='otro'` por defecto.
- **Catálogo de proveedor/fabricante es más rico que "nombre".** El FOR-003 (hoja `H.V.`, celdas `G37:K42`)
  pide país-ciudad, dirección, email, teléfono y contacto — no solo un nombre. `proveedores`/`fabricantes` se
  diseñan con esos campos, no como un simple `(id, nombre)`.
- **Riesgo de migración de datos explícito:** `equipos.fabricante`/`proveedor` son texto libre, sin
  normalizar (`"Fisher Scientific"` vs `"FISHER SCIENTIFIC S.A."` serían dos filas distintas en el catálogo
  tras un `INSERT ... SELECT DISTINCT`). La migración 0018 crea los catálogos y las columnas `*_id` **nullable**
  y hace el backfill por coincidencia exacta de texto; **no** borra `equipos.fabricante`/`proveedor`. Se deja
  una tarea manual explícita para Calidad/Gustavo: revisar duplicados casi-iguales en el catálogo antes de que
  una migración posterior (fuera del alcance de esta Fase 1) elimine las columnas de texto.
- **`repuestos_utilizados` → `mantenimiento_repuestos` tampoco es automático sin pérdida.** El texto libre no
  tiene una estructura separable de forma confiable (no hay un delimitador garantizado). La migración 0026
  **no transforma** el texto en filas estructuradas por heurística; en vez de eso: (a) mantiene
  `repuestos_utilizados` como está, de solo lectura para mantenimientos ya cerrados antes de esta fase, y
  (b) a partir de la Fase 4, los mantenimientos nuevos usan exclusivamente `mantenimiento_repuestos`. El
  historial unificado (sección 4) muestra `repuestos_utilizados` como texto para registros viejos y la tabla
  estructurada para los nuevos — ningún dato se pierde ni se reinterpreta a ciegas.
- **`equipo_manuales` y el `manual_object_key` existente.** Hoy un equipo tiene **un solo** manual (sin tipo).
  La migración 0020 no puede inventar un `tipo` — ver sección 7 (riesgo abierto, requiere decisión de Calidad).

### 2.2 Tablas sin cambios respecto a la especificación

`equipo_ficha_tecnica`, `equipo_accesorios`, `firmas`, `documentos_generados`, `equipo_novedades`,
`plantillas_checklist`/`plantilla_checklist_items`/`mantenimiento_checklist` se validan contra el esquema real
sin objeciones — no colisionan con ninguna tabla ni convención existente.

---

## 3. Reconciliación de estados

### 3.1 `mantenimientos.estado` (ejecución) vs. `estado_documento` (firma) — son dos ejes independientes

`estado` ya existe y es la máquina de **ejecución física** del mantenimiento (`programado → en_ejecucion →
completado` / `cancelado`), implementada con transiciones explícitas en `MantenimientoService` (`iniciar`,
`cerrar`, `cancelar`), cada una con su propia regla de negocio. **No se reemplaza.** `estado_documento`
(`borrador → pendiente_firmas → firmado → anulado`) es un eje nuevo y ortogonal sobre el **reporte FOR-005**
de ese mantenimiento. Reglas de interacción:

| `estado` (ejecución) | `estado_documento` permitido | Motivo |
|---|---|---|
| `programado` | `borrador` | El reporte se puede empezar a diligenciar (checklist, datos) antes de ejecutar, pero no se puede pedir firma sin fecha de ejecución (ver `FaltaFechaEjecutada` ya existente). |
| `en_ejecucion` | `borrador` | Igual — se sigue editando en campo. |
| `completado` | `borrador → pendiente_firmas → firmado → anulado` | Solo un mantenimiento `completado` (con `fecha_ejecutada`) puede pasar a `pendiente_firmas`. Es la **única** transición nueva que se agrega a `MantenimientoService.cerrar()` como precondición de `solicitar_firma()`. |
| `cancelado` | `borrador` (congelado) | Un mantenimiento cancelado nunca firma — no tiene sentido legal. El servicio rechaza `solicitar_firma()` si `estado == "cancelado"`. |

No hace falta un `CHECK` cruzado en base de datos entre ambas columnas (la combinación inválida
`estado='cancelado' AND estado_documento='firmado'` nunca la escribe el servicio porque todas las transiciones
de `estado_documento` pasan por `MantenimientoService`), pero si se quiere blindaje adicional a nivel de base
de datos, un `CHECK` simple `(estado <> 'cancelado' OR estado_documento = 'borrador')` es barato y consistente
con el criterio ya usado en la migración 0016 (dominio cerrado reforzado en la base de datos).

### 3.2 La migración 0011 no se toca — es un concepto distinto

0011 (`mapeo_estados_mantenimiento_json`) resuelve **a qué `estado_operativo` pasa el *equipo*** cuando un
mantenimiento se abre (RN-MANT-01, configurable por tipo y por laboratorio). Es ortogonal a `estado_documento`
(que es sobre el *reporte*, no sobre el equipo). No requiere ningún cambio para este desarrollo; se menciona
en la especificación porque ambas cosas viven en la misma tabla `mantenimientos`, pero no interactúan.

### 3.3 Frecuencia actual vs. `cronograma_metrologico`

**[CORRECCIÓN PROPUESTA]** La especificación (sección 4) propone `cronograma_metrologico` con
`frecuencia`, `ultima_ejecucion` y `proxima_ejecucion` **cacheadas** por `(equipo_id, tipo_actividad)`. Esto
contradice el propio principio de la sección 3.3 de la especificación ("el historial es una consulta, no una
tabla copiada... así es imposible que se desincronice"): si `ultima_ejecucion`/`proxima_ejecucion` se guardan
como columnas, hay que recordar actualizarlas desde `MantenimientoService.cerrar()` y desde
`CalibracionService.crear()` cada vez — exactamente el mismo riesgo de desincronización que la sección 3.3
quiere evitar para el historial.

Hoy ya existen **tres** lugares con frecuencia:
- `categorias_equipo.frecuencia_calibracion_default_meses` (default por categoría, ya en producción).
- `calibraciones.frecuencia_meses` (por registro, ya en producción — cada calibración puede traer una
  frecuencia distinta a la anterior).
- `mantenimientos.frecuencia_meses` (por registro, solo relevante si `tipo='preventivo'`).

**Alternativa propuesta:** `cronograma_metrologico` se reduce a una tabla de **solo configuración/override**,
sin fechas:

```
cronograma_metrologico(
  id, laboratorio_id,
  equipo_id FK equipos.id,
  tipo_actividad CHECK IN ('mantenimiento_preventivo','calibracion','calificacion','verificacion_interna'),
  frecuencia_meses_override INTEGER NULL,   -- si es NULL, se usa el default de la categoría
  UNIQUE (equipo_id, tipo_actividad)
)
```

`ultima_ejecucion`/`proxima_ejecucion` se **calculan en la consulta** (la misma vista/servicio del historial,
sección 4), tomando `MAX(fecha)` de la última intervención de ese `tipo_actividad` para ese equipo + la
frecuencia vigente (`cronograma_metrologico.frecuencia_meses_override` si existe, si no
`categorias_equipo.frecuencia_calibracion_default_meses`, aplicando `calcular_proxima_fecha()` — la misma
función pura que ya usa Calibraciones, sin duplicarla). Si en la práctica el costo de recalcular en cada
consulta del panel de equipos resulta alto, la Fase 6 puede añadir columnas cacheadas *como optimización
explícita y documentada*, nunca como fuente de verdad — pero no se adopta por defecto en la Fase 1.

Si Gustavo prefiere mantener el diseño original de la especificación (tabla con fechas cacheadas) por
simplicidad de consulta, es una decisión válida — se deja marcada como punto a confirmar en la sección 7.

---

## 4. Vista de historial unificado y su consulta

### 4.1 Qué cuenta como "intervención metrológica"

La hoja `MTTO` del FOR-003 (ver `docs/formatos/LSPC-GMT-GPM-FOR-003.xlsx`) tiene una fila por fecha con
columnas `MTTO PREVENTIVO | MTTO CORRECTIVO | CALIB | CALIF | VERIFICACION INTERNA`, más "detalle de actividad
realizada", "realizado por" y "supervisado por". Son conceptualmente **el mismo tipo de evento** (una
intervención con fecha, responsable y resultado) con un `tipo` distinto. Como se detalla en la sección 7,
`calificación` y `verificación interna` no tienen tabla propia hoy ni la propone la especificación — la opción
más simple y consistente con lo que ya existe es tratarlas como **valores adicionales de
`mantenimientos.tipo`** (junto a `preventivo`/`correctivo`/`predictivo`/`calibracion_correctiva`), no como
tablas nuevas. Con esa decisión, el historial unificado solo necesita combinar **dos** fuentes:
`mantenimientos` (ya cubre preventivo/correctivo/calificación/verificación) y `calibraciones`.

### 4.2 La vista

```sql
CREATE VIEW vista_historial_equipo AS
SELECT
  m.laboratorio_id,
  m.equipo_id,
  'mantenimiento'::text          AS origen,
  m.tipo                          AS tipo_intervencion,
  m.fecha_ejecutada               AS fecha,
  m.estado                        AS estado_ejecucion,
  m.estado_documento              AS estado_documento,
  m.tecnico_responsable_id        AS responsable_id,
  m.descripcion                   AS resumen,
  m.id                             AS origen_id,
  m.anulado_en IS NOT NULL         AS anulado
FROM mantenimientos m
WHERE m.fecha_ejecutada IS NOT NULL   -- no mezclar "programado" sin ejecutar en el historial
UNION ALL
SELECT
  c.laboratorio_id,
  c.equipo_id,
  'calibracion'::text,
  'calibracion',
  c.fecha_calibracion,
  'completado',
  NULL,                            -- las calibraciones no tienen ciclo de firma hoy
  c.responsable_id,
  c.resultado,
  c.id,
  c.corrige_a_id IS NOT NULL       -- una calibración corregida no se "anula": ver nota
FROM calibraciones c;
```

Notas de diseño:

- Es una **vista real de PostgreSQL**, no una consulta ensamblada en Python con dos `SELECT` + `UNION` en
  memoria — esto es importante porque las políticas RLS de `mantenimientos` y `calibraciones` **sí** se
  aplican a través de la vista (una vista normal en Postgres ejecuta con los privilegios de quien la consulta
  sobre las tablas base; no hay `SECURITY DEFINER` aquí), así que no hace falta una política RLS adicional
  sobre la vista misma, ni filtrar `laboratorio_id` a mano en el servicio — el filtro ya lo impone
  `app.current_tenant_id` como en cualquier otra consulta.
- El servicio de consulta (`HistorialService` o un método en `EquipoService`, por decidir en Fase 3) hace
  `SELECT * FROM vista_historial_equipo WHERE equipo_id = :id ORDER BY fecha DESC`, con el `laboratorio_id`
  resuelto implícitamente por RLS (igual que el resto del código).
- `calibraciones.corrige_a_id` ya marcaba "esta calibración corrige una anterior" **sin** un campo de
  anulación explícito (la anterior simplemente queda visible con su propio resultado, no se marca
  "anulada"). Es una semántica distinta a la de `mantenimientos.anulado_en` (anulación formal de un documento
  firmado). La vista expone ambos conceptos bajo una sola columna booleana `anulado` para que el frontend no
  tenga que conocer el detalle de cada módulo, pero el significado exacto difiere — documentado para que no
  se asuma que son lo mismo (sección 7 profundiza esta divergencia).
- Nuevo endpoint propuesto: `GET /equipos/{equipo_id}/hoja-vida/historial` (nombre deliberadamente distinto
  de `GET /equipos/{equipo_id}/historial`, que sigue siendo la auditoría de cambios de campos — sección 7).

---

## 5. Diseño del flujo de firma

### 5.1 Endpoints nuevos (sobre `mantenimientos`, sigue el router existente)

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /mantenimientos/{id}/firmas` | `mantenimientos.firmar` (nuevo, mismo patrón `requiere_permiso`) | Agrega una firma (`rol`, `nombre_firmante`, `cargo`, `registro_invima?`, `usuario_id?`, `firma_object_key` ya subida a MinIO vía `upload-url/firma`). Valida precondiciones (5.2) y dispara la transición de `estado_documento` si corresponde (5.3). |
| `GET /mantenimientos/{id}/firmas` | `equipos.leer` | Lista las firmas ya capturadas (para que el frontend muestre qué falta). |
| `POST /mantenimientos/{id}/anular` | `mantenimientos.firmar` | Solo si `estado_documento == 'firmado'`. Body: `motivo`. Marca el reporte actual como `anulado` (campos de la sección 2) y crea un **nuevo** `Mantenimiento` en `borrador`/`programado` con `reemplaza_a_id` apuntando al anulado (mismo `equipo_id`/`tipo`, sin copiar datos de ejecución). |
| `GET /mantenimientos/{id}/documento/pdf` | `equipos.leer` | Solo si `estado_documento == 'firmado'`. Devuelve URL de descarga firmada (`AlmacenamientoPort.url_descarga`) del PDF en `documentos_generados`. |
| `POST /mantenimientos/upload-url/firma` | `mantenimientos.firmar` | Igual patrón que `upload-url/evidencia`: valida que sea PNG, tamaño máximo (p. ej. 2 MB), devuelve `url_subida` + `object_key` bajo `firmas/{mantenimiento_id}/{uuid}.png`. |

### 5.2 Validaciones antes de aceptar una firma

1. `mantenimiento.estado == 'completado'` (RN ya existente de que no se cierra sin `fecha_ejecutada`).
2. `mantenimiento.estado_documento in ('borrador', 'pendiente_firmas')` — nunca se agrega una firma a un
   reporte `firmado` o `anulado` (defensa en capa de servicio, redundante con el trigger de 5.4).
3. `rol in ('realiza', 'recibe', 'supervisa')`.
4. No existe ya una firma con ese mismo `rol` para este `mantenimiento_id` (constraint único
   `(documento_tipo, documento_id, rol)` — reemplazar una firma exige **anular**, no sobrescribir).
5. Si `rol == 'supervisa'` es **opcional** según el tipo (a confirmar con Calidad, ver sección 7); `realiza`
   y `recibe` son obligatorios siempre.

### 5.3 Cuándo se congela el snapshot y se calcula el hash

El congelamiento ocurre en una sola transacción, disparada por la firma que completa el conjunto de roles
obligatorios (normalmente `recibe`, que suele ser la última en capturarse de forma presencial):

```
1. BEGIN;
2. SELECT ... FOR UPDATE del mantenimiento (evita que dos firmas concurrentes disparen el congelamiento dos veces).
3. INSERT de la firma nueva.
4. Si ahora están todos los roles obligatorios:
   a. Construir snapshot JSONB = { equipo: {...datos actuales...}, mantenimiento: {...}, checklist: [...],
      repuestos: [...], evidencias: [...], firmas: [...] }.
   b. Render del PDF con fpdf2, reutilizando `_texto_pdf()` y `_agregar_logo_encabezado()`
      (reportes/infrastructure/exportadores.py) para no reinventar el saneo de caracteres Latin-1.
   c. object_key = f"documentos-generados/{laboratorio_id}/{mantenimiento_id}/{uuid4()}.pdf"
   d. hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()   -- hash del PDF final, no del snapshot JSON:
      así cualquiera puede re-descargar el PDF y verificar el hash sin tener que reconstruir el JSON.
   e. INSERT INTO documentos_generados (tipo='FOR-005', entidad_id=mantenimiento_id, object_key, hash_sha256,
      snapshot, version_formato=<de configuraciones_laboratorio.versiones_formato_json>, generado_por_id, generado_en).
   f. UPDATE mantenimientos SET estado_documento = 'firmado' WHERE id = :id.
5. COMMIT.
```

`hashlib.sha256` es de la librería estándar — no se necesita una dependencia nueva (`cryptography` ya está en
`requirements.txt` pero no hace falta aquí). La subida del PDF a MinIO usa el mismo `AlmacenamientoPort`
existente (`url_subida` + que el backend mismo haga el `PUT`, o firmar una URL y subir desde el backend —
dado que el backend genera los bytes del PDF, aquí sí es el backend quien sube, a diferencia de
evidencias/fotos donde sube el navegador).

### 5.4 Cómo se impide editar un reporte firmado

**En el servicio** (defensa de primera línea, igual criterio que `TransicionInvalida` ya usado en
`MantenimientoService`): cualquier método que modifique campos de un `Mantenimiento` (`cerrar`, futuros
`actualizar_checklist`, `agregar_repuesto`, etc.) empieza con:

```python
if mantenimiento.estado_documento in ("firmado", "anulado"):
    raise DocumentoFirmadoEsInmutable()
```

**En base de datos** (defensa real, no delegada solo a la aplicación — mismo espíritu que la auditoría C1 que
motivó la migración 0016): este proyecto **no tiene triggers hoy**; este sería el primero. Propuesta:

```sql
CREATE OR REPLACE FUNCTION fn_bloquear_edicion_documento_firmado() RETURNS trigger AS $$
BEGIN
  IF OLD.estado_documento IN ('firmado', 'anulado') THEN
    -- única transición permitida después de firmado: firmado -> anulado,
    -- tocando solo las columnas de anulación.
    IF NEW.estado_documento = 'anulado' AND OLD.estado_documento = 'firmado'
       AND NEW.anulado_en IS NOT NULL AND OLD.anulado_en IS NULL
       AND row(NEW.*) IS DISTINCT FROM row(OLD.*) -- placeholder: comparar solo columnas no-anulación
    THEN
      RETURN NEW;
    END IF;
    IF NEW IS DISTINCT FROM OLD THEN
      RAISE EXCEPTION 'No se puede modificar un mantenimiento con documento % (id=%).', OLD.estado_documento, OLD.id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_mantenimientos_inmutable
  BEFORE UPDATE OR DELETE ON mantenimientos
  FOR EACH ROW EXECUTE FUNCTION fn_bloquear_edicion_documento_firmado();
```

(El pseudocódigo de la comparación "solo columnas de anulación" se debe escribir columna por columna en la
migración real de la Fase 5, no con `row(...)`, que compara todas las columnas — aquí se deja como diseño,
no como migración ya escrita, conforme al alcance de esta Fase 1.) La misma función (parametrizada por
tabla) se reutiliza en `documentos_generados` y `firmas`, que tampoco deben poder editarse ni borrarse nunca
una vez creados — ahí el trigger es más simple: bloquea **todo** `UPDATE`/`DELETE`.

Es la primera vez que el proyecto introduce triggers de PL/pgSQL — vale la pena que el PR de la Fase 5
incluya un test específico que intente `UPDATE` directo por SQL (no por el servicio) sobre un mantenimiento
firmado y confirme que la base de datos lo rechaza, no solo el servicio.

---

## 6. Wireframes en texto

### 6.1 Formulario de ficha técnica por pestañas (`EquipoFormPage`, Fase 2)

Requiere el componente `Tabs` nuevo (sección 1.7). Pestañas, en el orden del FOR-003 hoja `H.V.`:

```
┌─────────────────────────────────────────────────────────┐
│ ← Volver                                   Nuevo equipo  │
├─────────────────────────────────────────────────────────┤
│ [ General ] [ Datos técnicos ] [ Accesorios y manuales ] │
│ [ Proveedor y fabricante ] [ Información adicional ]     │
├─────────────────────────────────────────────────────────┤
│  (pestaña activa: General)                                │
│  Capítulo ▾   Grupo ▾   Subgrupo ▾                        │
│  Código interno*   Nombre*                                 │
│  Área ▾   Ubicación*                                       │
│  Marca   Modelo   N° de serie   N° de inventario           │
│  Condición física: ◉Bueno ○Regular ○Malo                   │
│  Clasificación por riesgo: ○I ○IIA ○IIB ○III                │
│  Criticidad: ○Baja ○Media ○Alta                             │
│  Estado operativo ▾   (campo YA existente, distinto de      │
│                         "condición física" — sección 3.4    │
│                         de la especificación)                │
│  Fotografía  [Subir]                                        │
├─────────────────────────────────────────────────────────┤
│                              [Cancelar]   [Guardar]          │
└─────────────────────────────────────────────────────────┘
```

Esquema zod (sintaxis zod 4 real, igual a la de `EquipoFormPage.tsx` actual):

```ts
const esquemaFichaTecnica = z.object({
  codigo_interno: z.string().min(1, { error: "El código interno es obligatorio." }).max(50),
  nombre: z.string().min(1, { error: "El nombre es obligatorio." }).max(200),
  capitulo: z.string().optional(),
  grupo: z.string().optional(),
  subgrupo: z.string().optional(),
  ubicacion: z.string().min(1, { error: "La ubicación es obligatoria." }),
  condicion_fisica: z.enum(["bueno", "regular", "malo"], { error: "Selecciona la condición física." }),
  clasificacion_riesgo: z.enum(["I", "IIA", "IIB", "III"]).optional(),
  criticidad: z.enum(["baja", "media", "alta"]).optional(),
  // ... resto de pestañas, mismo criterio: campos técnicos siempre .optional(),
  // nunca se exige inventar un dato (sección 3.8 de la especificación).
});
```

### 6.2 Hoja de vida digital (`EquipoDetailPage`, nueva pestaña, Fase 3)

```
┌─────────────────────────────────────────────────────────┐
│ Equipo: Autoclave AC-204          [Editar] [Eliminar] [QR]│
├─────────────────────────────────────────────────────────┤
│ [ Ficha técnica ] [ Hoja de vida ] [ Documentos ] [ Auditoría ] │
├─────────────────────────────────────────────────────────┤
│ (pestaña activa: Hoja de vida)                             │
│                                                              │
│ Cronograma metrológico                                      │
│  Mantenimiento preventivo   próx. 2026-12-15   🟡            │
│  Calibración                 próx. 2027-02-01   🟢            │
│                                                              │
│ Historial (vista unificada — vista_historial_equipo)         │
│  2026-10-02  Mantenimiento preventivo   Firmado   [Ver PDF]  │
│  2026-07-15  Calibración                Conforme  [Certificado] │
│  2026-05-20  Mantenimiento correctivo   Firmado   [Ver PDF]  │
│  2026-03-01  Mantenimiento correctivo   ANULADO (ver motivo) │
│                                                              │
│ Novedades                                                    │
│  2026-01-10  Traslado a Fisicoquímico de Aguas               │
│                                                              │
│ Hojas de vida físicas escaneadas                              │
│  [Subir escaneo PDF]   hoja-vida-2019.pdf  [Ver]              │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Formulario FOR-005 (borrador de mantenimiento, Fase 4)

```
┌─────────────────────────────────────────────────────────┐
│ ← Volver                        Reporte de mantenimiento   │
├─────────────────────────────────────────────────────────┤
│ Equipo: Autoclave AC-204 (AC-204)        [datos de solo    │
│ Área: Fisicoquímico de Aguas              lectura, auto-   │
│ Marca/Serie: Tuttnauer / SN-8821          cargados]        │
├─────────────────────────────────────────────────────────┤
│ Tipo: ○Preventivo ○Correctivo ○Instalación                 │
│ Falla reportada: [________________________________]        │
├─────────────────────────────────────────────────────────┤
│ Checklist general                                           │
│  ☐ Inspección del estado físico     ☐ Limpieza integral     │
│  ☐ Revisión de perillas de ajuste   ☐ Lubricación           │
│  ... (copiado de la plantilla al crear el reporte —          │
│       sección 3.7: cambiar la plantilla después no altera    │
│       reportes ya creados)                                   │
│ ☐ Sistema hidráulico (si aplica)                             │
│  ☐ Revisión de mangueras  ☐ Revisión de fluido  ...          │
│ ☐ Sistema eléctrico (si aplica)  /  ☐ Sistema electrónico    │
├─────────────────────────────────────────────────────────┤
│ Piezas reemplazadas                            [+ Agregar]  │
│  1. Empaque de puerta   Ref. EP-220   Cant. 1                │
├─────────────────────────────────────────────────────────┤
│ Evidencias                                                   │
│  [Antes 📷] [Durante 📷] [Después 📷]                        │
├─────────────────────────────────────────────────────────┤
│ Actividades realizadas: [___________________________]       │
│ Comentario: [___________________________]                   │
├─────────────────────────────────────────────────────────┤
│              [Guardar borrador]   [Continuar a firmas →]     │
└─────────────────────────────────────────────────────────┘
```

Nota sobre el formato físico: en `LSPC-GMT-ECM-FOR-005.docx` el checklist de **sistema hidráulico/eléctrico/
electrónico** aparece como secciones marcables con una casilla de encabezado (`□ Sistema Hidráulico`), no como
plantillas totalmente distintas por categoría de equipo. El diseño de arriba refleja eso: **una** plantilla
con secciones generales obligatorias + 3 secciones opcionales activables por categoría (en vez de "N
plantillas distintas", que sería forzar una variedad que el formato real no tiene — ver sección 7).

### 6.4 Pantalla de firma en celular (Fase 5)

```
┌───────────────────────────┐
│ ← Volver      Firmar reporte│
├───────────────────────────┤
│ Firma como: ◉Realiza        │
│             ○Recibe          │
│             ○Supervisa       │
├───────────────────────────┤
│ Nombre completo: [_________]│
│ Cargo:           [_________]│
│ Registro INVIMA: [_________]│
│                 (solo si aplica, se omite en el PDF la cédula) │
├───────────────────────────┤
│ Firme en el recuadro:       │
│ ┌─────────────────────────┐│
│ │                         ││
│ │    <canvas signature_pad>││
│ │      touch-action: none  ││
│ │                         ││
│ └─────────────────────────┘│
│        [Limpiar]            │
├───────────────────────────┤
│           [Guardar firma]   │
└───────────────────────────┘
```

Tras la firma que completa el set obligatorio, la pantalla pasa directo a "Reporte firmado — [Descargar PDF]"
en modo de solo lectura (ya no hay botón "editar").

---

## 7. Riesgos, dudas abiertas y contradicciones con el código actual

1. **Colisión de nombres: `historial`.** `GET /equipos/{id}/historial` ya existe y es auditoría de cambios de
   campos, no intervenciones metrológicas. El nuevo endpoint se propone como
   `GET /equipos/{id}/hoja-vida/historial` (sección 4.2) para no romper ni confundir el existente. **Pendiente
   de confirmar el nombre con Gustavo** antes de la Fase 3.
2. **`reportes_generados` vs. `documentos_generados`: nombres parecidos, propósitos distintos.**
   `reportes_generados` es una cola de trabajos de exportación agregada (puede fallar, se reintenta, no es
   evidencia legal de un equipo puntual). `documentos_generados` es un registro legal inmutable por
   mantenimiento/equipo. **No se deben fusionar** aunque ambos "generan PDF" — se señala explícitamente para
   que nadie intente reutilizar `reportes_generados` para esto en la Fase 5.
3. **No existe `calificaciones` ni `verificaciones_internas` como tabla, y la especificación tampoco las
   modela en su sección 4**, pese a que la sección 3.3 y la hoja `MTTO` del FOR-003 las mencionan como
   columnas propias. Se propone (sección 4.1) resolverlo extendiendo `mantenimientos.tipo` con
   `'calificacion'` y `'verificacion_interna'` en vez de crear dos tablas nuevas — es la opción que menos
   infraestructura nueva requiere y mantiene el historial unificado como una unión de solo dos fuentes.
   **Esto es una desviación real de la especificación tal como está escrita** (que no menciona esta extensión
   del enum) — se necesita la aprobación explícita de Gustavo antes de la Fase 4.
4. **`equipo_manuales` y el manual único existente.** `equipos.manual_object_key` no registra qué *tipo* de
   manual es. La migración 0020 no tiene forma de inferirlo con certeza — se propone migrarlo como
   "Manual de operación" por defecto (el más común) y dejar una nota visible en el formulario para que el
   usuario lo corrija si no corresponde. Alternativa: dejarlo fuera de `equipo_manuales` y mostrarlo aparte
   como "manual histórico (sin clasificar)". **Pendiente de decisión.**
5. **Catálogos de proveedor/fabricante y duplicados por texto libre.** Ver sección 2.1 — backfill por
   coincidencia exacta de texto, con revisión manual pendiente antes de poder borrar las columnas de texto.
6. **`repuestos_utilizados` no se puede parsear de forma confiable a filas estructuradas.** Se mantiene como
   campo de solo lectura para mantenimientos históricos (ver sección 2.1); no se inventa una heurística de
   separación que podría partir mal un texto libre.
7. **Primer trigger de base de datos del proyecto.** Hasta ahora toda regla de negocio vive en Python; la
   inmutabilidad de un documento firmado (sección 5.4) es, por su naturaleza de evidencia legal, un caso
   genuino para reforzarla en la base de datos. Se señala como una novedad de infraestructura (requiere test
   específico de intento de `UPDATE` directo por SQL) para que la revisión de la Fase 5 le preste atención
   particular.
8. **`calibraciones.corrige_a_id`/`motivo_correccion` vs. `mantenimientos.reemplaza_a_id`/`anulado_en`/
   `motivo_anulacion`: dos patrones de "no borrar, corregir" con forma distinta.** En calibraciones, el
   registro viejo **no** se marca como anulado — simplemente queda y el nuevo lo "corrige" (ambos visibles,
   ambos con su propio resultado). En mantenimientos, el documento firmado **sí** se marca formalmente
   `anulado` (con motivo/quién/cuándo) porque es un documento de calidad firmado, no solo un dato corregido.
   La divergencia es intencional (la calibración no tiene firma ni PDF legal hoy), pero se deja explícita para
   que no se intente "unificar" ambos patrones sin entender por qué son distintos.
9. **Celda residual `B19` de la hoja `H.V.` del FOR-003** (`Corriente(A): 0,1666...`) — confirmado que es un
   valor pegado que no forma parte del formato; se ignoró al leer el archivo, como se indicó. El campo real
   del formato es "Corriente(A):" vacío, parte de "Datos técnicos" (sección 6.1 de este documento).
10. **Duplicación del FOR-005 dentro del mismo `.docx`.** El archivo trae el formulario repetido dos veces de
    forma idéntica (ahorro de papel: dos reportes por hoja física). No afecta el modelo de datos ni el PDF
    digital — un reporte digital es un documento, no dos.
11. **Rol `supervisa` ¿obligatorio u opcional?** La especificación (3.5) no lo precisa. El checklist de
    aceptación global de la Fase 5 ("firmar en celular, descargar e imprimir") tampoco lo aclara. **Pregunta
    abierta para Gustavo/Calidad** antes de implementar las validaciones de la sección 5.2.
12. **Permiso `mantenimientos.firmar`** es nuevo (sección 5.1) — falta decidir en qué roles del sistema de
    permisos existente (`backend/app/modules/auth/`) se otorga por defecto. No se exploró el modelo de roles
    en detalle en esta Fase 1 (fuera del alcance de "equipos, mantenimientos, calibraciones, documentos,
    reportes" que pidió el prompt); queda como tarea de la Fase 5.
13. **Componente `Tabs` nuevo en frontend.** No existe hoy (sección 1.7) — su diseño visual/de accesibilidad
    (teclado, ARIA) no se especifica en este documento de backend/datos; se deja para que lo cubra el diseño
    de UI de la Fase 2 antes de programarlo.
14. **`cronograma_metrologico` con o sin fechas cacheadas** (sección 3.3) — se deja como decisión abierta,
    con una recomendación clara (sin caché) pero sin bloquear si Gustavo prefiere el diseño original de la
    especificación por simplicidad de consulta.

---

## 8. Resumen de lo que requiere aprobación antes de la Fase 2

- Nombre del nuevo endpoint de historial unificado (punto 1).
- Extender `mantenimientos.tipo` con `calificacion`/`verificacion_interna` en vez de tablas nuevas (punto 3).
- Criterio de migración del manual único existente hacia `equipo_manuales` (punto 4).
- Diseño de `cronograma_metrologico` sin fechas cacheadas vs. el original de la especificación (punto 14).
- Si `supervisa` es obligatorio siempre, nunca, o depende del tipo de mantenimiento (punto 11).

Ningún otro punto de este documento bloquea el inicio de la Fase 2 (ficha técnica extendida).
