# 25 — Diseño técnico: hojas de vida, mantenimiento y firmas (Fase 1)

**Proyecto:** LabSync Pro Enterprise
**Autor:** Claude Code (auditoría y diseño, sin código) — a partir de `docs/24-especificacion-hojas-de-vida-mantenimiento-firmas.md`
**Estado:** Borrador para aprobación de Gustavo Perea. No contiene cambios de código, modelos ni migraciones — solo diseño.
**Rama:** `docs/diseno-hojas-de-vida` (PR hacia `develop`)

> Este documento responde punto por punto al prompt de la Fase 1 (sección 7 de `docs/24-...md`). Cada vez que el
> diseño se aparta de la especificación original, se marca explícitamente como **[CORRECCIÓN PROPUESTA]** con el
> motivo y la alternativa — nunca se implementa en silencio una divergencia.
>
> **[REVISIÓN 2]** Gustavo revisó la primera versión y pidió 5 correcciones puntuales (congelamiento con la
> primera firma, `security_invoker` en la vista, columna `corregido` separada de `anulado` en calibraciones,
> manejo correcto de `DELETE` en el trigger, y el fallback de frecuencia del cronograma) y tomó 4 decisiones.
> Cada cambio de esa ronda está marcado **[REVISIÓN 2]** en el texto.
>
> **[REVISIÓN 3]** Gustavo (Líder de Gestión Metrológica del LSPC) decidió calificación/verificación interna
> (opción C: van en el módulo de Calibraciones, no en Mantenimientos ni en tablas nuevas) y pidió modelar los
> mantenimientos ejecutados por un proveedor externo (sin FOR-005 ni firmas, solo su informe con hash). Cada
> cambio de esta ronda está marcado **[REVISIÓN 3]**.
>
> **[REVISIÓN 4]** Gustavo decidió la última pregunta abierta: el hash de integridad de un informe o
> certificado lo calcula el **backend** (leyendo el archivo por streaming y validando sus magic bytes), nunca
> el cliente — un hash calculado por quien sube el archivo no es evidencia de integridad frente a ese mismo
> archivo. Con esta decisión no queda ninguna decisión de diseño pendiente (sección 8). Cada cambio de esta
> ronda está marcado **[REVISIÓN 4]**.

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

No existe ningún modelo de **calificación** ni **verificación interna** hoy. **[REVISIÓN 3 — decidido]**
Van en este mismo módulo, extendiendo `Calibracion` — no en Mantenimientos ni en tablas nuevas. Detalle y
motivos en la sección 4.1.

### 1.4 Documentos y adjuntos

| Pieza | Ruta | Qué hace hoy |
|---|---|---|
| `Documento`/`VersionDocumento` | [documentos/infrastructure/models.py](../backend/app/modules/documentos/infrastructure/models.py) | Gestor documental de **documentos de calidad del laboratorio** (SOP, formatos, etc.): carpetas, versiones, estado `vigente/obsoleto/en_revision`, aprobación, papelera con retención configurable. **No tiene `equipo_id`** — no está pensado para colgar un archivo de un equipo puntual. |
| `Adjunto` (modelo) | [adjuntos/infrastructure/models.py](../backend/app/modules/adjuntos/infrastructure/models.py) | Tabla polimórfica genérica: `entidad_tipo` + `entidad_id` + `object_key`. **Ya es el mecanismo real para "colgar un archivo de una entidad arbitraria"**, pero `entidad_tipo` tiene un `CHECK` cerrado desde la migración 0016: `('mantenimiento_evidencia', 'mantenimiento_informe', 'calibracion_certificado')`. Para "hoja de vida física escaneada" y las nuevas evidencias con "momento", este `CHECK` debe extenderse (sección 2). |
| `AlmacenamientoPort` | [documentos/domain/ports.py](../backend/app/modules/documentos/domain/ports.py) | Contrato MinIO compartido: `url_subida`, `url_descarga`, `url_vista_previa`, `copiar_objeto`, `eliminar_objeto`. El backend **nunca** transporta el binario *hacia o desde el navegador* — firma URLs y el frontend sube/baja directo a MinIO. **[REVISIÓN 4]** Este principio no cambia para subida/descarga; sí se agrega una lectura server-a-server puntual (sección 3.4/4.1) para hashear y validar archivos ya subidos — nunca para servirlos de vuelta al cliente. |

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
| 0020 | `equipo_accesorios_manuales` | 2 | Crea `equipo_accesorios`, `equipo_manuales` con `tipo CHECK IN ('manual_operacion','manual_instalacion','manual_servicio','manual_partes','sin_clasificar')`. **[REVISIÓN 2 — decidido]** Migra el valor actual de `equipos.manual_object_key` (si no es nulo) a una fila de `equipo_manuales` con `tipo='sin_clasificar'` — no se asume "operación" ni ningún otro tipo concreto, porque no hay forma de saberlo con certeza; el usuario lo reclasifica desde el formulario cuando lo note. |
| 0021 | `cronograma_metrologico` | 3 | Ver **[CORRECCIÓN PROPUESTA]** en sección 3.3: tabla reducida, sin fechas cacheadas. |
| 0022 | `equipo_novedades` | 3 | Tabla simple: `equipo_id`, `tipo` (falla/traslado/cambio_estado/baja), `descripcion`, `responsable_id`, `creado_en`. |
| 0023 | `adjuntos_hoja_vida_escaneada` | 3 | `ALTER` del `CHECK ck_adjuntos_entidad_tipo` para agregar `'equipo_hoja_vida_escaneada'` (drop + recreate, mismo patrón que si se agregara un valor a cualquier `CHECK` de dominio cerrado). |
| 0024 | **[REVISIÓN 3/4]** `calibraciones_tipo_ejecutor` | 3 | Agrega a `calibraciones`: `tipo CHECK IN ('calibracion','calificacion','verificacion_interna') NOT NULL DEFAULT 'calibracion'` (backfill: todas las filas existentes son `'calibracion'`, es lo único que hay hoy); `ejecutor_tipo CHECK IN ('interno','externo') NOT NULL`; `criterio_aceptacion TEXT NULL` (solo tiene sentido para `verificacion_interna`, nunca obligatorio); **[REVISIÓN 4]** `certificado_hash_sha256 TEXT NULL` (calculado por el backend al registrar la fila, solo si hay `certificado_adjunto_id` — sección 3.4/4.1, mismo mecanismo que `mantenimientos.informe_hash_sha256`). `CHECK (ejecutor_tipo = 'interno' OR laboratorio_proveedor IS NOT NULL)` — un ejecutor externo siempre debe decir qué proveedor la hizo. Backfill de `ejecutor_tipo`: `'externo'` si `laboratorio_proveedor IS NOT NULL`, si no `'interno'` — ver riesgo en sección 7 (puede haber calibraciones viejas sin `laboratorio_proveedor` diligenciado que en realidad fueron externas). Detalle completo en sección 4.1. |
| 0025 | `mantenimientos_estado_documento` | 4 | Agrega a `mantenimientos`: `estado_documento` (ahora **nullable** — sección 3.4), `falla_reportada`, `actividades_realizadas`, `comentarios`, `resultado`, `recomendaciones`, `estado_final_equipo`, `anulado_en`, `anulado_por`, `motivo_anulacion`, `reemplaza_a_id`, `consecutivo`, `snapshot_congelado JSONB NULL` (el contenido queda congelado desde la primera firma — sección 5.3, no desde la última). `CHECK ck_mantenimientos_estado_documento`. **[REVISIÓN 3]** `ck_mantenimientos_tipo` **no se toca** — calificación/verificación interna van en `calibraciones` (migración 0024), no aquí. |
| 0026 | **[REVISIÓN 3/4]** `mantenimientos_ejecutor` | 4 | Agrega a `mantenimientos`: `ejecutor_tipo CHECK IN ('interno','externo') NOT NULL DEFAULT 'interno'` (backfill: todo lo existente como `'interno'` — riesgo en sección 7, no hay forma de distinguir con certeza los históricos); `proveedor_id FK proveedores.id NULL`; `informe_hash_sha256 TEXT NULL` (**[REVISIÓN 4]** calculado por el backend al cerrar, leyendo el informe desde MinIO por streaming — sección 3.4, nunca enviado por el cliente). `CHECK (ejecutor_tipo = 'interno' OR proveedor_id IS NOT NULL)`. `CHECK ((ejecutor_tipo = 'interno') = (estado_documento IS NOT NULL))` — un mantenimiento externo nunca tiene `estado_documento`; uno interno siempre lo tiene (sección 3.4). |
| 0027 | `plantillas_checklist` | 4 | `plantillas_checklist`, `plantilla_checklist_items`, `mantenimiento_checklist` — **[REVISIÓN 3]** solo aplican a mantenimientos `ejecutor_tipo='interno'` (sección 3.4). |
| 0028 | `mantenimiento_repuestos_evidencias` | 4 | `mantenimiento_repuestos`; `mantenimiento_evidencias` (FK a `adjuntos.id` + columna `momento`, en vez de duplicar columnas de archivo — ver sección 2.1). Migra `repuestos_utilizados` texto a filas de `mantenimiento_repuestos` (best-effort, sin borrar el texto original). |
| 0029 | `firmas` | 5 | Tabla `firmas` (incluye `hash_contenido` — hash del `snapshot_congelado` en el momento de esa firma, sección 5.3 — y `descartada_en`/`descartada_por_id`, mismo patrón que `anulado_en`/`eliminado_en` ya usado en el proyecto, para el flujo "volver a borrador" de la sección 5.3; índice único parcial `(documento_tipo, documento_id, rol) WHERE descartada_en IS NULL`, mismo criterio que `uq_alertas_activa_por_origen` de la migración 0007) + triggers de inmutabilidad (sección 5.4, con manejo explícito de `DELETE`). **[REVISIÓN 3]** Solo existen firmas para mantenimientos `ejecutor_tipo='interno'` — nunca para externos ni para calibraciones/calificaciones/verificaciones. |
| 0030 | `documentos_generados` | 5 | Tabla `documentos_generados` + trigger de inmutabilidad (bloquea **todo** `UPDATE`/`DELETE` sin excepción, se crea una sola vez al completarse las firmas) + `configuraciones_laboratorio.versiones_formato_json`. **[REVISIÓN 3]** Solo se usa para el FOR-005 de mantenimientos internos; un mantenimiento externo nunca genera una fila aquí (su soporte es el informe del proveedor, hasheado directamente en `mantenimientos.informe_hash_sha256`, migración 0026). |
| 0031 | `vista_historial_equipo` | 5 (no 3) | Se agrega como migración propia y se mueve a la Fase 5: depende de `mantenimientos.estado_documento`/`anulado_en`/`ejecutor_tipo` (0025/0026) y de `calibraciones.tipo`/`ejecutor_tipo` (0024) — no puede ir antes de que existan esas columnas. `CREATE VIEW vista_historial_equipo WITH (security_invoker = true) AS ...` (sección 4.2, revisada en esta ronda) + test de aislamiento multi-tenant sobre la vista. |

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
  tiene una estructura separable de forma confiable (no hay un delimitador garantizado). La migración 0028
  **no transforma** el texto en filas estructuradas por heurística; en vez de eso: (a) mantiene
  `repuestos_utilizados` como está, de solo lectura para mantenimientos ya cerrados antes de esta fase, y
  (b) a partir de la Fase 4, los mantenimientos nuevos usan exclusivamente `mantenimiento_repuestos`. El
  historial unificado (sección 4) muestra `repuestos_utilizados` como texto para registros viejos y la tabla
  estructurada para los nuevos — ningún dato se pierde ni se reinterpreta a ciegas.
- **`equipo_manuales` y el `manual_object_key` existente.** Hoy un equipo tiene **un solo** manual (sin tipo).
  **[REVISIÓN 2 — decidido]** La migración 0020 no inventa un tipo: migra con `tipo='sin_clasificar'` (valor
  agregado al `CHECK` de `equipo_manuales.tipo`, junto a `manual_operacion`/`manual_instalacion`/
  `manual_servicio`/`manual_partes`). El usuario reclasifica manualmente si corresponde.

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
  frecuencia_meses_override INTEGER NULL,   -- si es NULL, el fallback depende de tipo_actividad —
                                             -- [REVISIÓN 2] ver la tabla de fallbacks más abajo
  UNIQUE (equipo_id, tipo_actividad)
)
```

`ultima_ejecucion`/`proxima_ejecucion` se **calculan en la consulta** (la misma vista/servicio del historial,
sección 4), tomando `MAX(fecha)` de la última intervención de ese `tipo_actividad` para ese equipo + la
frecuencia vigente, aplicando `calcular_proxima_fecha()` — la misma función pura que ya usa Calibraciones, sin
duplicarla. Si en la práctica el costo de recalcular en cada consulta del panel de equipos resulta alto, la
Fase 6 puede añadir columnas cacheadas *como optimización explícita y documentada*, nunca como fuente de
verdad — pero no se adopta por defecto en la Fase 1. **[REVISIÓN 2 — aprobado, con corrección del punto 5]**

**[REVISIÓN 2]** La frecuencia vigente **no** usa `categorias_equipo.frecuencia_calibracion_default_meses`
como fallback para `tipo_actividad='mantenimiento_preventivo'` — esa columna, por nombre y por uso actual
(`CalibracionService`), es el default de **calibración**, no de mantenimiento; usarla también como fallback de
preventivo mezclaría dos frecuencias que un laboratorio puede querer distintas (p. ej. calibrar cada 12 meses
pero hacer mantenimiento preventivo cada 6). Regla corregida, por `tipo_actividad`:

| `tipo_actividad` | Fallback si no hay `cronograma_metrologico.frecuencia_meses_override` |
|---|---|
| `calibracion` | `categorias_equipo.frecuencia_calibracion_default_meses` (ya existe, es su propósito original). |
| `mantenimiento_preventivo` | Ninguno inventado: **"sin programar"** (igual al `gris` que ya devuelve `semaforo()` cuando `proxima_fecha is None` — no se agrega un número mágico). El cronograma solo muestra fecha próxima si el equipo tiene un `frecuencia_meses_override` explícito en `cronograma_metrologico`, o si ya existe algún `mantenimientos.frecuencia_meses` de un preventivo recurrente previo para ese equipo. |
| `calificacion` / `verificacion_interna` | Igual que `mantenimiento_preventivo`: sin fallback numérico, "sin programar" si no hay `override` explícito. |

**[REVISIÓN 3]** Esta tabla no cambia con la decisión de la sección 4.1 (calificación/verificación interna
viven en `calibraciones`, no en `mantenimientos`): `cronograma_metrologico.tipo_actividad` es independiente
de en qué tabla se guarda cada intervención — sigue siendo "sin programar" para calificación/verificación
salvo `override` explícito, nunca el default de `calibracion`.

Si en el futuro Calidad quiere un default **por categoría** también para preventivo/calificación/verificación
(simétrico al de calibración), es una columna nueva en `categorias_equipo` por tipo de actividad — una mejora
aditiva, no necesaria para la Fase 1 y fuera de este alcance.

**Decidido:** `cronograma_metrologico` sin fechas cacheadas, con el fallback de frecuencia por
`tipo_actividad` de esta sección.

### 3.4 Mantenimientos externos (sin FOR-005 ni firmas) **[REVISIÓN 3 — nueva]**

Contexto real del LSPC: hoy algunos mantenimientos los ejecuta un proveedor externo, y el único soporte es
el informe que ese proveedor entrega — nadie llena el FOR-005 a mano para esos casos (de hecho, esto es
exactamente lo que ya resuelve `informe_adjunto_id`/`asignar_informe()` hoy, sección 1.2: un PDF ya hecho,
subido una vez, sin flujo de firmas). El diseño de la sección 5 (checklist, firmas, snapshot congelado) solo
tiene sentido para un mantenimiento que el **propio laboratorio** ejecuta y documenta paso a paso. Se agrega
`mantenimientos.ejecutor_tipo CHECK IN ('interno', 'externo')` (migración 0026, sección 2) para que ambos
casos convivan en la misma tabla sin forzar el flujo de firmas sobre lo que un proveedor externo ya
certificó por su cuenta:

| | `ejecutor_tipo = 'interno'` | `ejecutor_tipo = 'externo'` |
|---|---|---|
| Quién lo ejecuta | Personal del laboratorio | Un proveedor (`proveedor_id`, FK a `proveedores` — obligatorio si es externo, `CHECK` en la migración 0026) |
| Flujo | FOR-005 completo: checklist, repuestos, evidencias, firmas (sección 5), tal como está diseñado — **sin cambios**. | Sin FOR-005 ni firmas. Para `cerrar()` es **obligatorio** tener ya un informe adjunto (`informe_adjunto_id IS NOT NULL`, reutilizando `asignar_informe()` existente — sección 1.2, sin cambios en ese mecanismo). |
| `estado_documento` | Sigue el ciclo completo `borrador → pendiente_firmas → firmado → anulado` (secciones 3.1 y 5). | **Siempre `NULL`** — no aplica, no hay documento que firmar. `CHECK ((ejecutor_tipo = 'interno') = (estado_documento IS NOT NULL))` en la migración 0026 lo refuerza en base de datos. |
| Qué lo congela/vuelve inmutable | La primera firma (`estado_documento` pasa a `pendiente_firmas`, sección 5.3). | El propio `cerrar()`: al cerrar un mantenimiento externo con su informe ya adjunto, el registro completo (incluido el informe) queda inmutable de inmediato — no hace falta ninguna firma para que un informe de un tercero sea evidencia válida. |
| Hash de integridad | `firmas.hash_contenido` + `documentos_generados.hash_sha256` del PDF que el propio sistema genera (sección 5.3). | `mantenimientos.informe_hash_sha256` (migración 0026) — hash del informe del proveedor, calculado por el **backend** al cerrar (ver más abajo). |
| Corrección de un error | Anular (`estado_documento='anulado'`) + reemplazar (`reemplaza_a_id`), sección 5.1. | **Mismo mecanismo** — `anular_y_reemplazar()`/`POST /mantenimientos/{id}/anular` se generaliza para aceptar también un externo ya cerrado (su precondición deja de ser "`estado_documento=='firmado'`" y pasa a ser "está en el estado inmutable que le corresponda a su `ejecutor_tipo`", ver sección 5.1/5.4). |

**[REVISIÓN 4 — DECIDIDO POR GUSTAVO.] `informe_hash_sha256` lo calcula el backend, no el navegador.** Un
hash de integridad calculado por el cliente no es evidencia: el sistema nunca lo verificó, así que no prueba
nada frente a un cliente que miente o a un archivo corrupto en tránsito. Que hoy se confíe en
`tamano_bytes`/`tipo_mime` reportados por el cliente (`_solicitar_url` en `mantenimiento_service.py`, sección
1.2) es una debilidad **existente**, no un precedente a seguir — queda señalada aparte en el riesgo 21 de la
sección 7, sin corregirla aquí (fuera de alcance de esta Fase 1).

Al llamar `cerrar()` sobre un mantenimiento `externo` con su `informe_adjunto_id` ya asignado:

1. El backend lee el objeto desde MinIO **por streaming** (`AlmacenamientoPort`, método nuevo — sección
   4.1/7, riesgo 22 — recibe el `object_key` y entrega los bytes en fragmentos, nunca el archivo completo
   en memoria de una sola vez; el cliente MinIO/S3 soporta esto de forma nativa).
2. Mientras lee cada fragmento: acumula los primeros bytes (los *magic bytes* del formato — `%PDF` para PDF,
   `\xFF\xD8\xFF` para JPG, `\x89PNG\r\n\x1a\n` para PNG) y alimenta un `hashlib.sha256()` incremental con
   cada fragmento, sin tener que guardar el archivo completo para calcular el hash.
3. Al terminar de leer: compara los magic bytes reales contra el `tipo_mime` que el `Adjunto` declaró al
   subirse. Si no coinciden (alguien subió un `.exe` renombrado a `.pdf`, por ejemplo), **se rechaza el
   cierre** con un error de dominio — el mantenimiento no se cierra, no queda inmutable, y no se guarda
   ningún hash de un archivo que no es lo que dice ser.
4. Si coinciden, `informe_hash_sha256 = hasher.hexdigest()` se guarda junto con la transición a inmutable
   (mismo criterio transaccional que el congelamiento de la sección 5.3: todo en una sola operación).

**Mismo criterio para los certificados/informes de `calibraciones`** (sección 4.1): se agrega
`certificado_hash_sha256 TEXT NULL` a la migración 0024, calculado por el backend de la misma forma (lectura
por streaming + magic bytes + hash incremental) dentro de `CalibracionService._crear_fila()`, justo después
de registrar el `Adjunto` y antes de confirmar la fila de `Calibracion` — si el certificado no es lo que dice
ser, tampoco se crea el registro de calibración/calificación/verificación.

**Opción descartada: que el frontend calcule el hash con `crypto.subtle.digest("SHA-256", ...)` (Web Crypto
API) y lo envíe al backend.** Es más simple de implementar (sin tocar `AlmacenamientoPort` ni leer bytes en
el backend) y es lo que proponía la versión anterior de este documento, pero se descarta: un hash que el
propio cliente calcula sobre su propio archivo no es una garantía de integridad frente a ese cliente — solo
protegería contra una corrupción accidental después de que el backend ya confió en el valor reportado, no
contra un cliente que miente a propósito. La validación de integridad real tiene que hacerla quien no tiene
interés en mentir, es decir, el backend.

---

## 4. Vista de historial unificado y su consulta

### 4.1 Qué cuenta como "intervención metrológica"

La hoja `MTTO` del FOR-003 (ver `docs/formatos/LSPC-GMT-GPM-FOR-003.xlsx`) tiene una fila por fecha con
columnas `MTTO PREVENTIVO | MTTO CORRECTIVO | CALIB | CALIF | VERIFICACION INTERNA`, más "detalle de actividad
realizada", "realizado por" y "supervisado por". Son conceptualmente **el mismo tipo de evento** (una
intervención con fecha, responsable y resultado) con un `tipo` distinto.

**[REVISIÓN 3 — DECIDIDO POR GUSTAVO: OPCIÓN C.]** `calificación` y `verificación interna` no van como
valores adicionales de `mantenimientos.tipo` (opción A) ni como tablas nuevas (opción B): **van en el módulo
de Calibraciones**, extendiéndolo con `calibraciones.tipo CHECK IN ('calibracion', 'calificacion',
'verificacion_interna')`. Contexto real del LSPC que motiva esta decisión: calibración y calificación las
ejecuta un proveedor externo que entrega su propio certificado o informe; la verificación interna la ejecuta
el propio Gustavo (Líder de Gestión Metrológica) — las tres son, en los hechos, la misma clase de evento que
ya modela `Calibracion` (fecha, equipo, responsable, resultado conforme/no_conforme, certificado/informe
adjunto, corrección sin borrar vía `corrige_a_id`), **no** la misma clase de evento que `Mantenimiento`
(que tiene checklist, repuestos, evidencias y un ciclo de firma pensado para una intervención física sobre el
equipo, no para una medición o verificación de un patrón).

Validación contra el esquema real (`calibraciones/infrastructure/models.py`, sección 1.3) — qué ya existe y
qué falta:

| Campo que pide la decisión | ¿Ya existe? | Columna |
|---|---|---|
| Resultado conforme/no conforme (para verificación interna) | **Sí**, ya existe y es `NOT NULL` | `resultado` (CHECK `ck_calibraciones_resultado`, migración 0016) |
| Quién la ejecutó (para distinguir interno/externo) | Parcial — `responsable_id` ya existe, `laboratorio_proveedor` (texto, opcional) ya existe, pero no hay una columna explícita que diga "interno" o "externo" | Falta `ejecutor_tipo` |
| Criterio de aceptación (para verificación interna) | No existe | Falta `criterio_aceptacion` |
| Certificado/informe adjunto | **Sí**, ya existe (`certificado_adjunto_id`, reutiliza `adjuntos`) | Sin cambios |
| Hash de integridad del certificado (**[REVISIÓN 4]**) | No existe | Falta `certificado_hash_sha256`, calculado por el backend al registrar — mismo mecanismo que `mantenimientos.informe_hash_sha256` (sección 3.4) |
| Corrección sin borrar | **Sí**, ya existe (`corrige_a_id`/`motivo_correccion`) | Sin cambios |

Diseño (migración 0024, sección 2): se agrega `tipo` (como arriba), `ejecutor_tipo CHECK IN ('interno',
'externo') NOT NULL`, `criterio_aceptacion TEXT NULL` (solo se diligencia para `verificacion_interna`; nunca
obligatorio, consistente con "ningún dato ficticio" — sección 3.8 de la especificación), y **[REVISIÓN 4]**
`certificado_hash_sha256 TEXT NULL`, calculado por el backend dentro de `CalibracionService._crear_fila()`
justo después de registrar el `Adjunto` del certificado (lectura por streaming + validación de magic bytes,
mismo mecanismo que `mantenimientos.informe_hash_sha256` — sección 3.4). Un `CHECK
(ejecutor_tipo = 'interno' OR laboratorio_proveedor IS NOT NULL)` refuerza en base de datos que un ejecutor
externo siempre declare qué proveedor la hizo. **Ninguna de las tres (`calibracion`, `calificacion`,
`verificacion_interna`) genera un PDF FOR-005** — ese formato es exclusivamente del módulo de Mantenimientos
(sección 3.4); si Calidad en el futuro quiere un PDF propio para calificación/verificación, es un desarrollo
nuevo y separado, fuera de este alcance.

**Opciones descartadas, por el registro:**

- **Opción A — valores adicionales de `mantenimientos.tipo`.** A favor: reutiliza toda la infraestructura de
  checklist/repuestos/evidencias/firmas sin crear nada nuevo, y mantiene el historial como unión de solo dos
  fuentes. **Por qué se descarta:** con el ciclo de firma de la sección 5, cualquier fila de `mantenimientos`
  que llega a `pendiente_firmas`/`firmado` genera un PDF **FOR-005** ("Reporte de mantenimiento de equipos").
  Una calificación o una verificación interna no son un mantenimiento y no deberían terminar en un documento
  que se titula "Reporte de mantenimiento" — un PDF con el formato, código y versión equivocados para lo que
  realmente ocurrió. Además, en el LSPC real estas dos sí las ejecuta mayormente un proveedor externo
  (calificación) o el propio Gustavo con un patrón de referencia (verificación interna), no un técnico que
  llena un checklist de mantenimiento — la forma del dato en `Mantenimiento` no calza con el contexto real.
- **Opción B — tablas nuevas** `calificaciones`/`verificaciones_internas`. A favor: no fuerza columnas que no
  aplican y permite un ciclo de documento propio. **Por qué se descarta:** habría duplicado una tabla que ya
  existe y ya resuelve casi todo lo que estos dos tipos necesitan (`Calibracion`) — innecesario frente a
  extenderla con dos columnas, dado que su forma de dato (fecha, responsable, resultado, certificado,
  corrección) ya es la correcta para los tres casos.

Con esta decisión, el historial unificado sigue siendo la unión de solo **dos** fuentes
(`mantenimientos` ∪ `calibraciones`), pero `calibraciones` ahora cubre tres `tipo` distintos en vez de uno —
sección 4.2 ajusta la vista para exponerlos.

### 4.2 La vista

**[REVISIÓN 3]** Versión ajustada: agrega `ejecutor_tipo` (mantenimientos interno/externo — sección 3.4 — y
calibraciones/calificaciones/verificaciones — sección 4.1), `tipo_intervencion` ahora lee `calibraciones.tipo`
en vez de un literal fijo `'calibracion'`, y se agregan `documento_tipo`/`documento_referencia_id` para que
cada fila enlace a su documento soporte (FOR-005, informe externo, o certificado de calibración), sin que el
frontend tenga que adivinar de qué tabla viene cada enlace:

```sql
CREATE VIEW vista_historial_equipo
WITH (security_invoker = true) AS   -- sin esto, la vista corre con los privilegios de quien la CREÓ,
                                     -- no de quien la consulta, y el RLS podría saltarse (sección 4.2, nota 1).
SELECT
  m.laboratorio_id,
  m.equipo_id,
  'mantenimiento'::text                AS origen,
  m.tipo                                AS tipo_intervencion,
  m.fecha_ejecutada                     AS fecha,
  m.estado                              AS estado_ejecucion,
  m.estado_documento                    AS estado_documento,   -- NULL si ejecutor_tipo='externo' (sección 3.4)
  m.ejecutor_tipo                       AS ejecutor_tipo,
  m.tecnico_responsable_id              AS responsable_id,
  m.descripcion                         AS resumen,
  m.id                                  AS origen_id,
  (m.anulado_en IS NOT NULL)            AS anulado,
  false                                 AS corregido,   -- un mantenimiento no se "corrige", se anula y reemplaza
  CASE
    WHEN m.ejecutor_tipo = 'interno' AND m.estado_documento = 'firmado' THEN 'FOR-005'
    WHEN m.ejecutor_tipo = 'externo' AND m.informe_hash_sha256 IS NOT NULL THEN 'informe_externo'
    ELSE NULL
  END                                   AS documento_tipo,
  CASE
    WHEN m.ejecutor_tipo = 'interno' THEN dg.id              -- documentos_generados.id (el PDF firmado)
    WHEN m.ejecutor_tipo = 'externo' THEN m.informe_adjunto_id  -- adjuntos.id (el informe del proveedor)
    ELSE NULL
  END                                   AS documento_referencia_id
FROM mantenimientos m
LEFT JOIN documentos_generados dg ON dg.tipo = 'FOR-005' AND dg.entidad_id = m.id
WHERE m.fecha_ejecutada IS NOT NULL   -- no mezclar "programado" sin ejecutar en el historial
UNION ALL
SELECT
  c.laboratorio_id,
  c.equipo_id,
  'calibracion'::text,
  c.tipo,                               -- [REVISIÓN 3] 'calibracion' | 'calificacion' | 'verificacion_interna'
  c.fecha_calibracion,
  'completado',
  NULL,                                 -- ninguno de los 3 tipos de calibraciones firma documento alguno
  c.ejecutor_tipo,                       -- [REVISIÓN 3] 'interno' | 'externo' (migración 0024)
  c.responsable_id,
  c.resultado,
  c.id,
  false                                 AS anulado,     -- una calibración nunca se anula formalmente hoy
  EXISTS (                                              -- "corregido" = existe OTRA fila cuyo corrige_a_id
    SELECT 1 FROM calibraciones c2                       -- apunta a esta; corrige_a_id vive en el registro
    WHERE c2.corrige_a_id = c.id                          -- NUEVO, no en el viejo, por eso se busca "hacia
  )                                     AS corregido,      -- adelante" en vez de leer la propia fila.
  CASE WHEN c.certificado_adjunto_id IS NOT NULL THEN 'certificado_calibracion' ELSE NULL END,
  c.certificado_adjunto_id              AS documento_referencia_id
FROM calibraciones c;
```

Notas de diseño:

1. Es una **vista real de PostgreSQL**, pero sin `WITH (security_invoker = true)` eso **no basta** para que
   el RLS se aplique correctamente: por defecto (`security_invoker = false`, el comportamiento histórico),
   una vista evalúa las políticas RLS de las tablas base con los **privilegios del dueño de la vista**, no de
   quien la consulta — un hueco real y documentado de PostgreSQL, no una particularidad de este proyecto.
   `security_invoker = true` (disponible desde PostgreSQL 15; el proyecto corre PostgreSQL 16 en
   `docker-compose.yml`) fuerza a que la vista use los privilegios y el
   `current_setting('app.current_tenant_id')` de quien consulta, igual que cualquier otra tabla. Con esto no
   hace falta una política RLS adicional sobre la vista ni filtrar `laboratorio_id` a mano en el servicio.
2. Esta es, junto con el trigger de la sección 5.4, la primera vista del proyecto — se agrega a la migración
   0031 (sección 2) un **test de aislamiento multi-tenant específico sobre la vista**
   (`test_hoja_vida_historial_isolation.py`, mismo patrón que `test_tenant_isolation.py` y
   `test_equipos_isolation.py` ya existentes): crear mantenimientos/calibraciones en dos laboratorios distintos
   y confirmar que consultar la vista como el laboratorio A nunca devuelve filas del laboratorio B. Este test
   entra en el mismo gate de CI que ya corre los demás `test_*_isolation.py`, no es un mecanismo nuevo de
   verificación.
3. El servicio de consulta (`HistorialService` o un método en `EquipoService`, por decidir en Fase 3) hace
   `SELECT * FROM vista_historial_equipo WHERE equipo_id = :id ORDER BY fecha DESC`, con el `laboratorio_id`
   resuelto implícitamente por RLS (igual que el resto del código).
4. `calibraciones.corrige_a_id` vive en el registro **nuevo** (el que corrige), apuntando al viejo — por eso
   el registro viejo no puede exponer "estoy corregido" leyendo su propia fila; se necesita el `EXISTS` de la
   rama de calibraciones de la vista. `corregido` es una columna separada de `anulado`: una calibración
   corregida sigue siendo un resultado válido y visible en el historial, con su propio `resultado`
   (conforme/no_conforme) — no es lo mismo que un mantenimiento `anulado` (que fue formalmente invalidado
   porque tenía datos firmados o un informe incorrecto). La vista expone ambas columnas por separado, sin
   forzarlas a una sola bandera booleana, precisamente para no perder esta distinción.
5. **[REVISIÓN 3]** `documento_tipo`/`documento_referencia_id` resuelven, en una sola columna por fila, a qué
   endpoint apuntar desde el frontend: `'FOR-005'` → `GET /mantenimientos/{origen_id}/documento/pdf`
   (sección 5.1); `'informe_externo'` → `GET /mantenimientos/{origen_id}/informe-url` (existente, sección
   1.2); `'certificado_calibracion'` → `GET /calibraciones/{origen_id}/certificado-url` (existente, sección
   1.3). `documento_referencia_id` solo se expone por completitud/depuración — el frontend no necesita
   construir la URL con él, porque los tres endpoints ya reciben `origen_id` (el id del mantenimiento o la
   calibración), no el id del documento/adjunto.
6. Nuevo endpoint propuesto: `GET /equipos/{equipo_id}/hoja-vida/historial` (nombre deliberadamente distinto
   de `GET /equipos/{equipo_id}/historial`, que sigue siendo la auditoría de cambios de campos). **Aprobado
   por Gustavo.**

---

## 5. Diseño del flujo de firma

**[REVISIÓN 3]** Todo lo de esta sección aplica **solo a mantenimientos `ejecutor_tipo='interno'`** (sección
3.4). Un mantenimiento externo nunca tiene firmas ni documento generado — su soporte es el informe del
proveedor, cerrado con su propio hash (sección 3.4). El endpoint de anulación (`POST
/mantenimientos/{id}/anular`) es la única excepción: se generaliza para servir a ambos casos.

### 5.1 Endpoints nuevos (sobre `mantenimientos`, sigue el router existente)

| Método y ruta | Permiso | Qué hace |
|---|---|---|
| `POST /mantenimientos/{id}/firmas` | `mantenimientos.firmar` (nuevo, mismo patrón `requiere_permiso`) | Solo para `ejecutor_tipo='interno'`. Agrega una firma (`rol`, `nombre_firmante`, `cargo`, `registro_invima?`, `usuario_id?`, `firma_object_key` ya subida a MinIO vía `upload-url/firma`). Valida precondiciones (5.2) y, si es la primera firma, congela el contenido (`borrador → pendiente_firmas`); si completa los roles obligatorios, genera el documento (`pendiente_firmas → firmado`) — ver 5.3. |
| `GET /mantenimientos/{id}/firmas` | `equipos.leer` | Lista las firmas ya capturadas (vigentes y descartadas, para trazabilidad), para que el frontend muestre qué falta. Vacía siempre para `ejecutor_tipo='externo'`. |
| `POST /mantenimientos/{id}/volver-a-borrador` | `mantenimientos.firmar` | Solo para `ejecutor_tipo='interno'` y `estado_documento == 'pendiente_firmas'` (nunca si ya `firmado`). Body: `motivo`. Marca todas las firmas vigentes de ese mantenimiento como descartadas (`descartada_en`/`descartada_por_id`, **no se borran**) y devuelve el mantenimiento a `estado_documento='borrador'` con `snapshot_congelado=NULL`, para volver a editar el contenido. |
| `POST /mantenimientos/{id}/anular` | `mantenimientos.firmar` | **[REVISIÓN 3 — generalizado]** Sirve para los dos `ejecutor_tipo`. Precondición: el mantenimiento debe estar en su estado inmutable (`interno` con `estado_documento == 'firmado'`, o `externo` con `estado == 'completado'` e `informe_hash_sha256 IS NOT NULL` — sección 3.4/5.4). Body: `motivo`. Marca el registro actual como `anulado` (campos de la sección 2) y crea un **nuevo** `Mantenimiento` en `borrador`/`programado` (mismo `ejecutor_tipo`) con `reemplaza_a_id` apuntando al anulado (mismo `equipo_id`/`tipo`, sin copiar datos de ejecución). |
| `GET /mantenimientos/{id}/documento/pdf` | `equipos.leer` | Solo para `ejecutor_tipo='interno'` con `estado_documento == 'firmado'`. Devuelve URL de descarga firmada (`AlmacenamientoPort.url_descarga`) del PDF en `documentos_generados`. Para `externo`, el frontend usa el endpoint ya existente `GET /mantenimientos/{id}/informe-url` (sección 1.2, sin cambios). |
| `POST /mantenimientos/upload-url/firma` | `mantenimientos.firmar` | Igual patrón que `upload-url/evidencia`: valida que sea PNG, tamaño máximo (p. ej. 2 MB), devuelve `url_subida` + `object_key` bajo `firmas/{mantenimiento_id}/{uuid}.png`. |

### 5.2 Validaciones antes de aceptar una firma

**[REVISIÓN 3]** Precondición 0, nueva: `mantenimiento.ejecutor_tipo == 'interno'` — un mantenimiento
`externo` rechaza cualquier intento de agregar una firma (error de dominio, no silencioso).

1. `mantenimiento.estado == 'completado'` (RN ya existente de que no se cierra sin `fecha_ejecutada`).
2. `mantenimiento.estado_documento in ('borrador', 'pendiente_firmas')` — nunca se agrega una firma a un
   reporte `firmado` o `anulado` (defensa en capa de servicio, redundante con el trigger de 5.4). **[REVISIÓN
   2]** Nótese que esto ya no distingue "antes/después del congelamiento" como en la versión anterior: desde
   la Revisión 2, `pendiente_firmas` **ya es** contenido congelado (sección 5.3) — esta validación solo dice
   en qué dos estados se puede seguir agregando firmas, no si el contenido es editable.
3. `rol in ('realiza', 'recibe', 'supervisa')`.
4. No existe ya una firma **vigente** con ese mismo `rol` para este `mantenimiento_id` (constraint único
   parcial `(documento_tipo, documento_id, rol) WHERE descartada_en IS NULL` — mismo criterio que
   `uq_alertas_activa_por_origen` en la migración 0007, único "mientras vigente"). Reemplazar una firma exige
   **volver a borrador** (si aún no está `firmado`) o **anular** (si ya está `firmado`), nunca sobrescribir.
5. **[REVISIÓN 2 — decidido]** `realiza` y `recibe` son **siempre obligatorias**; `supervisa` es **siempre
   opcional** (no depende del tipo de mantenimiento). El conjunto "roles obligatorios" de la sección 5.3 es,
   por lo tanto, fijo: `{realiza, recibe}`.

### 5.3 Cuándo se congela el snapshot y se calcula el hash

**[REVISIÓN 2 — corrección del punto 1]** La versión anterior de este documento congelaba el contenido en la
**última** firma obligatoria. Es un error: `pendiente_firmas` debe significar "contenido inmutable" **desde
que existe la primera firma**, no solo cuando ya están todas. El congelamiento ahora ocurre en dos momentos
distintos, y hay un tercer flujo nuevo para deshacerlo mientras aún no está `firmado`:

**(a) Primera firma — `borrador → pendiente_firmas` (congela el contenido):**

```
1. BEGIN;
2. SELECT ... FOR UPDATE del mantenimiento (evita una carrera si dos personas firman casi al mismo tiempo).
3. Si mantenimiento.estado_documento != 'borrador': error (ya está congelado o firmado — no es "la primera").
4. Construir snapshot JSONB = { equipo: {...datos actuales...}, mantenimiento: {...}, checklist: [...],
   repuestos: [...], evidencias: [...] }  -- sin "firmas": las firmas se consultan aparte, nunca se congelan
   dentro del propio snapshot (si no, el snapshot cambiaría con cada firma siguiente).
5. UPDATE mantenimientos SET estado_documento = 'pendiente_firmas', snapshot_congelado = :snapshot WHERE id = :id.
6. hash_contenido = hashlib.sha256(json_canonico(snapshot)).hexdigest()   -- [REVISIÓN 2] hash del CONTENIDO
   (el snapshot, no el PDF, que todavía no existe) en el momento exacto de ESTA firma.
7. INSERT INTO firmas (..., hash_contenido, descartada_en = NULL).
8. COMMIT.
```

A partir de este `COMMIT`, el trigger de la sección 5.4 bloquea cualquier edición del mantenimiento, su
checklist, sus repuestos y sus evidencias — **ya no hace falta esperar a que falten firmas para proteger el
contenido**.

**(b) Firmas siguientes, mientras `estado_documento == 'pendiente_firmas'`:**

```
1. BEGIN; SELECT ... FOR UPDATE.
2. hash_contenido = hashlib.sha256(json_canonico(mantenimiento.snapshot_congelado)).hexdigest()
   -- [REVISIÓN 2] Debe ser IDÉNTICO al hash_contenido de la primera firma, porque el contenido no
   -- pudo cambiar (el trigger lo impide). Si un test o una auditoría encontrara dos firmas del mismo
   -- mantenimiento con hash_contenido distinto, sería evidencia de que algo (un acceso directo a la
   -- base de datos, un bug) saltó el trigger — nunca debería ocurrir en operación normal. Por eso vale
   -- la pena guardarlo en cada firma y no solo una vez: es evidencia forense redundante, a propósito.
3. INSERT INTO firmas (..., hash_contenido, descartada_en = NULL).
4. Si con esta firma ya están completos los roles obligatorios ({realiza, recibe}, sección 5.2):
   a. Render del PDF con fpdf2 a partir de `mantenimiento.snapshot_congelado` (NO de datos "en vivo" del
      equipo, que pudieron cambiar entre la primera firma y esta — sección 3.2 de la especificación),
      reutilizando `_texto_pdf()` y `_agregar_logo_encabezado()` (reportes/infrastructure/exportadores.py).
   b. object_key = f"documentos-generados/{laboratorio_id}/{mantenimiento_id}/{uuid4()}.pdf"
   c. hash_sha256 = hashlib.sha256(pdf_bytes).hexdigest()   -- hash del PDF final (distinto del
      hash_contenido de las firmas, que es del snapshot JSON): así cualquiera puede re-descargar el PDF
      y verificar este hash sin reconstruir el JSON.
   d. INSERT INTO documentos_generados (tipo='FOR-005', entidad_id=mantenimiento_id, object_key, hash_sha256,
      snapshot=mantenimiento.snapshot_congelado,
      version_formato=<de configuraciones_laboratorio.versiones_formato_json>, generado_por_id, generado_en).
   e. UPDATE mantenimientos SET estado_documento = 'firmado' WHERE id = :id.
5. COMMIT.
```

**(c) "Volver a borrador" — `pendiente_firmas → borrador` (descongela, descarta firmas sin borrarlas):**

```
1. BEGIN; SELECT ... FOR UPDATE.
2. Si mantenimiento.estado_documento != 'pendiente_firmas': error (ya firmado, o ya en borrador).
3. UPDATE firmas SET descartada_en = now(), descartada_por_id = :actor WHERE mantenimiento_id = :id
   AND descartada_en IS NULL.
4. UPDATE mantenimientos SET estado_documento = 'borrador', snapshot_congelado = NULL WHERE id = :id.
5. COMMIT.
```

`hashlib.sha256` es de la librería estándar — no se necesita una dependencia nueva (`cryptography` ya está en
`requirements.txt` pero no hace falta aquí). La subida del PDF a MinIO usa el mismo `AlmacenamientoPort`
existente (`url_subida` + que el backend mismo haga el `PUT`, o firmar una URL y subir desde el backend —
dado que el backend genera los bytes del PDF, aquí sí es el backend quien sube, a diferencia de
evidencias/fotos donde sube el navegador).

### 5.4 Cómo se impide editar un reporte firmado (o un informe externo cerrado)

**[REVISIÓN 2]** Con el congelamiento movido a la primera firma (sección 5.3), el trigger debe bloquear
ediciones ya desde `pendiente_firmas`, no solo desde `firmado`/`anulado` como en la versión anterior.
**[REVISIÓN 3]** Y debe cubrir también `ejecutor_tipo='externo'` (sección 3.4), donde `estado_documento` es
siempre `NULL` — la inmutabilidad ahí no la marca `estado_documento`, sino `informe_hash_sha256`.

**En el servicio** (defensa de primera línea, igual criterio que `TransicionInvalida` ya usado en
`MantenimientoService`): cualquier método que modifique campos de un `Mantenimiento` empieza con:

```python
if mantenimiento.ejecutor_tipo == "interno" and mantenimiento.estado_documento != "borrador":
    raise DocumentoFirmadoEsInmutable()
if mantenimiento.ejecutor_tipo == "externo" and mantenimiento.informe_hash_sha256 is not None:
    raise DocumentoFirmadoEsInmutable()
```

**En base de datos** (defensa real, no delegada solo a la aplicación — mismo espíritu que la auditoría C1 que
motivó la migración 0016): este proyecto **no tiene triggers hoy**; este sería el primero. **[REVISIÓN 2 —
corrección del punto 4]** La versión anterior tenía un error real: en un trigger de `DELETE`, la fila `NEW`
**no existe** (es `NULL`), así que `RETURN NEW;` en la rama de `DELETE` no "permite seguir sin cambios" — en
PostgreSQL, el valor de retorno de un trigger `BEFORE DELETE` que no sea `NULL` deja que el `DELETE` proceda
(y `RETURN NEW` con `NEW = NULL` equivale a `RETURN NULL`, que **cancela el borrado en silencio**, sin avisar
con una excepción). El trigger debe distinguir `TG_OP` explícitamente y usar `RETURN OLD` para `DELETE`:

```sql
CREATE OR REPLACE FUNCTION fn_bloquear_edicion_documento_firmado() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    -- Nunca se borra físicamente un mantenimiento interno que ya tuvo alguna firma, ni uno externo
    -- ya cerrado con su informe hasheado ("ningún registro histórico se elimina físicamente").
    IF (OLD.ejecutor_tipo = 'interno' AND OLD.estado_documento <> 'borrador')
       OR (OLD.ejecutor_tipo = 'externo' AND OLD.informe_hash_sha256 IS NOT NULL)
    THEN
      RAISE EXCEPTION 'No se puede eliminar este mantenimiento (ejecutor=%, id=%): ya tiene documento o informe inmutable.',
        OLD.ejecutor_tipo, OLD.id;
    END IF;
    RETURN OLD;  -- sin documento/informe aún: sí se puede borrar.
  END IF;

  -- A partir de aquí, TG_OP = 'UPDATE'. [REVISIÓN 3] Rama separada para 'externo': no usa
  -- estado_documento (que para externos siempre es NULL por el CHECK de la migración 0026).
  IF OLD.ejecutor_tipo = 'externo' THEN
    IF OLD.informe_hash_sha256 IS NULL THEN
      RETURN NEW;  -- todavía no se cerró con informe adjunto: edición libre.
    END IF;
    IF NEW.anulado_en IS NOT NULL AND OLD.anulado_en IS NULL
       -- y solo cambiaron anulado_en/anulado_por/motivo_anulacion respecto a OLD.
    THEN
      RETURN NEW;  -- la única transición permitida tras cerrar: anular + reemplazar (sección 5.1).
    END IF;
    RAISE EXCEPTION 'No se puede modificar un mantenimiento externo con informe ya cerrado (id=%).', OLD.id;
  END IF;

  -- ejecutor_tipo = 'interno': solo 4 transiciones de estado_documento están permitidas una vez que ya
  -- no es 'borrador'; cualquier otro cambio se rechaza.
  IF OLD.estado_documento = 'borrador' THEN
    RETURN NEW;  -- edición libre, incluida la transición borrador -> pendiente_firmas (primera firma).
  END IF;

  IF OLD.estado_documento = 'pendiente_firmas' AND NEW.estado_documento = 'borrador' THEN
    RETURN NEW;  -- "volver a borrador" (5.3c): descongela; las firmas se descartan en la tabla `firmas`,
                 -- no aquí.
  END IF;

  IF OLD.estado_documento = 'pendiente_firmas' AND NEW.estado_documento = 'firmado'
     -- y ninguna otra columna de contenido cambió respecto a OLD (comparación columna por columna,
     -- se escribe en la migración real; aquí NEW.snapshot_congelado IS NOT DISTINCT FROM
     -- OLD.snapshot_congelado es la pieza clave: el contenido no se toca al completar las firmas).
  THEN
    RETURN NEW;
  END IF;

  IF OLD.estado_documento = 'firmado' AND NEW.estado_documento = 'anulado'
     AND NEW.anulado_en IS NOT NULL AND OLD.anulado_en IS NULL
     -- y solo cambiaron anulado_en/anulado_por/motivo_anulacion respecto a OLD.
  THEN
    RETURN NEW;
  END IF;

  RAISE EXCEPTION 'No se puede modificar un mantenimiento con documento en estado % (id=%).',
    OLD.estado_documento, OLD.id;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_mantenimientos_inmutable
  BEFORE UPDATE OR DELETE ON mantenimientos
  FOR EACH ROW EXECUTE FUNCTION fn_bloquear_edicion_documento_firmado();
```

(Las comparaciones "ninguna otra columna cambió" se escriben columna por columna en la migración real de la
Fase 4/5 — aquí se deja como diseño, no como migración ya escrita, conforme al alcance de esta Fase 1.)

Sobre `firmas`: nunca se actualizan excepto para pasar de vigente a descartada (`descartada_en` de `NULL` a
`NOT NULL`, sin tocar ningún otro campo — mismo patrón de comparación que arriba) y nunca se borran
físicamente (mismo `TG_OP = 'DELETE'` siempre rechazado). Sobre `documentos_generados`: se crea una sola vez,
al completarse las firmas (5.3b) — ahí el trigger es más simple porque no hay transiciones intermedias que
permitir: bloquea **todo** `UPDATE` y **todo** `DELETE` sin excepción, siempre con la misma distinción
explícita de `TG_OP` (nunca `RETURN NEW` dentro de la rama de `DELETE`).

**[REVISIÓN 2, ajustada]** Nota operativa para quien escriba estas migraciones: cualquier migración
**posterior** que haga un `UPDATE` masivo sobre `mantenimientos` (un backfill, una corrección de datos) va a
chocar con este trigger para toda fila `interno` con `estado_documento <> 'borrador'`, o **[REVISIÓN 3]**
toda fila `externo` con `informe_hash_sha256 IS NOT NULL`. Antes de este desarrollo todas las filas
existentes tienen `estado_documento = 'borrador'` (los `interno`) por defecto (columna nueva), así que una
migración de backfill que corra *antes* de que exista cualquier firma o cierre externo no tiene problema.
Cualquier migración de datos escrita *después* de que el sistema lleve tiempo en producción con reportes
firmados o informes externos cerrados **debe filtrar explícitamente** (`WHERE estado_documento = 'borrador'`
para `interno`, `WHERE informe_hash_sha256 IS NULL` para `externo`) y dejar fuera del `UPDATE` cualquier fila
que ya sea inmutable.

**Regla sin excepciones:** está **prohibido** desactivar el trigger (`ALTER TABLE ... DISABLE TRIGGER`) sobre
`firmas` o `documentos_generados`, bajo cualquier circunstancia — esas dos tablas no tienen ninguna
transición de "corrección de datos" legítima una vez creada la fila, así que no existe un caso válido para
saltarse la protección. Sobre `mantenimientos`, tampoco se desactiva el trigger: si una migración necesitara
tocar una fila ya inmutable (interna o externa), eso significa que el dato está mal pensado, no que el
trigger esté de más. **Un dato erróneo en un reporte firmado o en un informe externo ya cerrado se corrige
únicamente por el camino de negocio (anular + reemplazar, sección 5.1), nunca editando la fila
directamente** — ni por servicio, ni por una migración, ni por acceso directo a la base de datos.

Es la primera vez que el proyecto introduce triggers de PL/pgSQL (junto con la vista de la sección 4.2) —
vale la pena que el PR de la Fase 5 incluya un test específico que intente `UPDATE` y `DELETE` directos por
SQL (no por el servicio) sobre un mantenimiento en `pendiente_firmas` y en `firmado`, y confirme que la base
de datos los rechaza con una excepción clara (no que el `DELETE` se "pierda" en silencio), no solo el
servicio.

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

**[REVISIÓN 3]** Cada fila del historial ahora muestra de qué lo ejecutó (badge **Interno**/**Externo**, de
`ejecutor_tipo`) y el tipo de calibración ya distingue sus tres variantes (`calibración`/`calificación`/
`verificación interna`, de `calibraciones.tipo` — sección 4.1); el enlace de cada fila usa
`documento_tipo`/`documento_referencia_id` de la vista (sección 4.2) para apuntar al PDF firmado, al informe
del proveedor o al certificado, según corresponda:

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
│  Verificación interna         sin programar     ⚪            │
│                                                              │
│ Historial (vista unificada — vista_historial_equipo)         │
│  2026-10-02  Mantenimiento preventivo  [Interno]  Firmado   [Ver PDF]        │
│  2026-08-10  Mantenimiento correctivo  [Externo]  Cerrado   [Ver informe]    │
│  2026-07-15  Calibración                [Externo]  Conforme  [Certificado]   │
│  2026-06-01  Verificación interna       [Interno]  Conforme  [Certificado]   │
│  2026-05-20  Mantenimiento correctivo  [Interno]  Firmado   [Ver PDF]        │
│  2026-03-01  Mantenimiento correctivo  [Interno]  ANULADO (ver motivo)       │
│                                                              │
│ Novedades                                                    │
│  2026-01-10  Traslado a Fisicoquímico de Aguas               │
│                                                              │
│ Hojas de vida físicas escaneadas                              │
│  [Subir escaneo PDF]   hoja-vida-2019.pdf  [Ver]              │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Formulario FOR-005 (borrador de mantenimiento, Fase 4)

**[REVISIÓN 3]** Este formulario solo aplica a mantenimientos `ejecutor_tipo='interno'` (sección 3.4). Al
crear un mantenimiento, lo primero que se pregunta es quién lo ejecuta — si se elige "Externo", el flujo salta
directamente al wireframe 6.3-bis (sin checklist, sin firmas).

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

### 6.3-bis Cierre de mantenimiento externo (sin FOR-005, Fase 4) **[REVISIÓN 3 — nuevo]**

```
┌─────────────────────────────────────────────────────────┐
│ ← Volver                        Cerrar mantenimiento       │
├─────────────────────────────────────────────────────────┤
│ Equipo: Autoclave AC-204 (AC-204)        [datos de solo    │
│ Área: Fisicoquímico de Aguas              lectura, auto-   │
│ Marca/Serie: Tuttnauer / SN-8821          cargados]        │
├─────────────────────────────────────────────────────────┤
│ Ejecutor: ○Interno  ◉Externo                                │
│ Proveedor*: [Seleccionar proveedor ▾]   (obligatorio)       │
├─────────────────────────────────────────────────────────┤
│ Tipo: ○Preventivo ○Correctivo ○Instalación                 │
│ Falla reportada: [________________________________]        │
│ Fecha de ejecución*: [____/____/______]                     │
├─────────────────────────────────────────────────────────┤
│ Informe del proveedor*                                       │
│  [Subir PDF]   informe-tuttnauer-oct2026.pdf                │
│  (obligatorio para poder cerrar — sin checklist, sin firmas) │
├─────────────────────────────────────────────────────────┤
│                                          [Cerrar mantenimiento] │
└─────────────────────────────────────────────────────────┘
```

Al presionar "Cerrar mantenimiento": el frontend calcula el hash SHA-256 del PDF ya subido (Web Crypto API,
sección 3.4) y lo envía junto con el resto de los datos. A partir de ahí, el registro queda inmutable
(sección 5.4) y la pantalla pasa a modo de solo lectura, igual que un FOR-005 ya firmado — pero sin firmas ni
PDF generado por el sistema, solo el informe del proveedor.

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
   campos, no intervenciones metrológicas. El nuevo endpoint es
   `GET /equipos/{id}/hoja-vida/historial` (sección 4.2) para no romper ni confundir el existente.
   **[REVISIÓN 2 — aprobado.]**
2. **`reportes_generados` vs. `documentos_generados`: nombres parecidos, propósitos distintos.**
   `reportes_generados` es una cola de trabajos de exportación agregada (puede fallar, se reintenta, no es
   evidencia legal de un equipo puntual). `documentos_generados` es un registro legal inmutable por
   mantenimiento/equipo. **No se deben fusionar** aunque ambos "generan PDF" — se señala explícitamente para
   que nadie intente reutilizar `reportes_generados` para esto en la Fase 5.
3. **No existe `calificaciones` ni `verificaciones_internas` como tabla, y la especificación tampoco las
   modela en su sección 4**, pese a que la sección 3.3 y la hoja `MTTO` del FOR-003 las mencionan como
   columnas propias. **[REVISIÓN 3 — decidido por Gustavo: OPCIÓN C]** (sección 4.1 completa): van en el
   módulo de Calibraciones (`calibraciones.tipo CHECK IN ('calibracion','calificacion','verificacion_interna')`
   + `ejecutor_tipo`/`criterio_aceptacion`), no en Mantenimientos (opción A, descartada porque generaría un
   PDF FOR-005 incorrecto) ni en tablas nuevas (opción B, descartada por innecesaria frente a extender una
   tabla que ya tiene casi todo lo que hace falta).
4. **`equipo_manuales` y el manual único existente.** `equipos.manual_object_key` no registra qué *tipo* de
   manual es. **[REVISIÓN 2 — decidido]:** la migración 0020 migra con `tipo='sin_clasificar'` (valor nuevo en
   el `CHECK` de `equipo_manuales.tipo`), sin asumir "operación" ni ningún otro tipo concreto — el usuario lo
   reclasifica manualmente si corresponde.
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
11. **Rol `supervisa` ¿obligatorio u opcional?** **[REVISIÓN 2 — decidido]:** siempre opcional; `realiza` y
    `recibe` siempre obligatorias, sin que dependa del tipo de mantenimiento (sección 5.2).
12. **Permiso `mantenimientos.firmar`** es nuevo (sección 5.1) — falta decidir en qué roles del sistema de
    permisos existente (`backend/app/modules/auth/`) se otorga por defecto. No se exploró el modelo de roles
    en detalle en esta Fase 1 (fuera del alcance de "equipos, mantenimientos, calibraciones, documentos,
    reportes" que pidió el prompt); queda como tarea de la Fase 5.
13. **Componente `Tabs` nuevo en frontend.** No existe hoy (sección 1.7) — su diseño visual/de accesibilidad
    (teclado, ARIA) no se especifica en este documento de backend/datos; se deja para que lo cubra el diseño
    de UI de la Fase 2 antes de programarlo.
14. **`cronograma_metrologico` con o sin fechas cacheadas** (sección 3.3) — **[REVISIÓN 2 — decidido]:** sin
    fechas cacheadas, con el ajuste del fallback de frecuencia por `tipo_actividad` (no usar el default de
    calibración para mantenimiento preventivo/calificación/verificación — sección 3.3).
15. **[REVISIÓN 2]** Primer `CREATE VIEW` del proyecto (sección 4.2), además del primer trigger (punto 7).
    Ninguno de los dos patrones (vistas con `security_invoker`, triggers de inmutabilidad con manejo de
    `DELETE`) tiene precedente en el código actual — ambos quedan como la primera instancia, por lo que el PR
    de la Fase correspondiente debe incluir tests explícitos de cada uno (aislamiento multi-tenant sobre la
    vista, y `UPDATE`/`DELETE` directos por SQL contra el trigger), no solo contra el servicio.
16. **[REVISIÓN 2]** El flujo "volver a borrador" (sección 5.1/5.3c) es nuevo y no estaba en la especificación
    original — se agregó porque el congelamiento ahora ocurre desde la primera firma (punto 1 de esta
    revisión), y hace falta una forma de deshacer una firma capturada por error *antes* de llegar a
    `firmado` (después de `firmado` ya no aplica: ahí es anular + reemplazar, sección 5.1). Usa el mismo
    permiso `mantenimientos.firmar` que capturar una firma — a confirmar si Calidad quiere restringirlo a un
    rol distinto (p. ej. solo supervisores), igual que el punto 12 de permisos en general.
17. **[REVISIÓN 3]** Backfill de `calibraciones.ejecutor_tipo` (migración 0024, sección 2): se infiere
    `'externo'` cuando `laboratorio_proveedor IS NOT NULL`, si no `'interno'`. Es una heurística, no un hecho
    certero — una calibración vieja donde alguien olvidó diligenciar `laboratorio_proveedor` quedaría
    clasificada como `'interno'` por error. Se recomienda que Calidad revise la lista de calibraciones
    backfilleadas como `'interno'` antes de confiar en el filtro por ejecutor en reportes o paneles.
18. **[REVISIÓN 3]** Backfill de `mantenimientos.ejecutor_tipo` (migración 0026, sección 2): **todo** lo
    existente se migra como `'interno'` por defecto, porque hoy no hay ninguna columna que distinga el caso
    externo — el único rastro posible es que un mantenimiento tenga `informe_adjunto_id` sin checklist ni
    evidencias diligenciadas, una señal débil, no una regla confiable. A diferencia del punto 17 (donde hay
    una señal razonable), aquí no se propone ninguna heurística automática: se migra todo como `'interno'` y
    se deja a Calidad la tarea de revisar y reclasificar los mantenimientos que en realidad fueron externos.
19. **[REVISIÓN 4 — decidido]** Cómo se calcula `mantenimientos.informe_hash_sha256`/`calibraciones.certificado_hash_sha256`
    (sección 3.4/4.1): lo calcula el **backend**, leyendo el objeto desde MinIO por streaming y validando los
    magic bytes contra el `tipo_mime` declarado — no el frontend. Un hash que calcula el propio cliente sobre
    su propio archivo no es evidencia de integridad frente a ese cliente.
20. **[REVISIÓN 3]** El endpoint `POST /mantenimientos/{id}/anular` (sección 5.1) ahora sirve para dos casos
    con reglas de inmutabilidad distintas (`interno` firmado vs. `externo` cerrado con informe) — el servicio
    necesita una función única que determine "¿está en estado inmutable?" para cualquier `ejecutor_tipo`
    (la misma lógica que ya describe el trigger de la sección 5.4, duplicada a propósito en Python como
    defensa de primera línea, igual criterio que el resto de este documento).
21. **[REVISIÓN 4]** `tamano_bytes`/`tipo_mime` reportados por el cliente al pedir una URL de subida
    (`_solicitar_url`, sección 1.2/1.4) siguen sin verificarse contra el binario real en ningún flujo de este
    proyecto, incluido este desarrollo, **salvo** en los dos puntos nuevos que sí leen y validan el archivo
    (cierre de mantenimiento externo y registro de certificado de calibración, punto 19). Es una debilidad
    **preexistente** del proyecto, no introducida por este desarrollo — se señala explícitamente porque la
    decisión de esta ronda deja la inconsistencia a la vista: dos flujos nuevos validan el binario real, el
    resto de subidas del sistema (fotos, manuales, evidencias, informes antes de cerrar, versiones de
    documentos) siguen confiando en lo que el cliente declara. Corregir eso en todos los flujos existentes es
    un desarrollo propio, fuera del alcance de esta Fase 1.
22. **[REVISIÓN 4]** El método nuevo de `AlmacenamientoPort` para leer un objeto por streaming (sección 3.4)
    es la primera vez que el backend lee un binario completo que no generó él mismo — hasta ahora solo firma
    URLs o genera bytes en memoria (los PDF de `reportes`/`documentos_generados`, donde el propio backend es
    quien los crea). Dos límites a tener presentes en la implementación real: (a) la validación de magic
    bytes es una verificación de **cabecera**, no de contenido — un archivo con la cabecera correcta de PDF
    pero cuerpo corrupto o malicioso pasaría igual; no sustituye un antivirus ni un sandbox de apertura, solo
    descarta el caso más burdo (extensión/mime mentidos); (b) leer el objeto completo por streaming para
    hashearlo tiene un costo de I/O y tiempo proporcional al tamaño del archivo — aceptable para PDFs de
    informes/certificados (decenas de MB como mucho, según los límites ya existentes en el proyecto para
    estos tipos de archivo), pero el método no debe reutilizarse sin pensarlo para archivos potencialmente
    mucho más grandes.

---

## 8. Resumen de lo que requiere aprobación antes de la Fase 2

**[REVISIÓN 4] No queda ninguna decisión de diseño pendiente.** Las cuatro rondas de revisión quedaron
resueltas: nombre del endpoint de historial, manual existente a `'sin_clasificar'`, cronograma sin fechas
cacheadas con el fallback por tipo de actividad, `supervisa` siempre opcional, congelamiento desde la primera
firma con el flujo "volver a borrador", la regla sin excepciones sobre `DISABLE TRIGGER`, `security_invoker`
en la vista, columna `corregido` separada de `anulado`, manejo de `DELETE` en el trigger,
calificación/verificación interna en el módulo de Calibraciones (opción C) con mantenimientos externos sin
FOR-005 ni firmas, y — la decisión de esta ronda — el hash de integridad de informes/certificados lo calcula
el backend, nunca el cliente.

Puntos menores que no bloquean, para resolver durante la implementación (no son decisiones de diseño, son
detalles de construcción):
- A qué roles del sistema de permisos se les otorga `mantenimientos.firmar`, y si "volver a borrador"
  necesita un permiso más restrictivo que capturar una firma (riesgos 12/16).
- Diseño visual/de accesibilidad del componente `Tabs` nuevo (riesgo 13).
- Revisión manual de los backfills de `ejecutor_tipo` en calibraciones y mantenimientos antes de confiar en
  ellos para reportes (riesgos 17/18) — no bloquea escribir las migraciones, sí bloquea confiar en los datos
  históricos reclasificados hasta que Calidad los revise.
- La forma exacta del método nuevo de `AlmacenamientoPort` para lectura por streaming, y sus límites de
  tamaño/tiempo (riesgo 22) — es un detalle de implementación de la Fase 4, no cambia el diseño.

Ningún punto de este documento bloquea el inicio de la Fase 2 (ficha técnica extendida).
