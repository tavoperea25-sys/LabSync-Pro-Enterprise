# 18 — Planificación por Sprints

Metodología Scrum, sprints de 2 semanas. Numeración continua a través de las fases de `17-roadmap.md`.

---

## Sprint 1 — Fundación técnica
**Objetivos:** dejar el monorepo, CI/CD básico y la autenticación multi-tenant funcionando de punta a punta.
**Historias:** HU-ADMIN-01 (parcial: estructura de configuración), infraestructura base (no tiene HU de usuario final, es habilitante).
**Entregables:**
- Repositorio con estructura de `13-arquitectura.md` (frontend + backend + docker-compose).
- CI con lint + type-check + tests en cada PR.
- Autenticación (login, refresh, logout) con RLS multi-tenant verificado por pruebas automatizadas de aislamiento.
**Riesgos:** subestimar el esfuerzo de configurar RLS correctamente desde el inicio — mitigación: este sprint no avanza a otro módulo hasta que el gate de aislamiento esté verde en CI.

## Sprint 2 — Migración de diseño + RBAC
**Objetivos:** llevar el login ya construido a React manteniendo su nivel de accesibilidad, y modelar RBAC granular.
**Historias:** HU-ADMIN-02, HU-ALL-01 (tema claro/oscuro base).
**Entregables:**
- Login migrado a React + shadcn/ui sobre los tokens de `11-design-system.md`.
- Modelo `roles`/`permisos`/`roles_permisos` funcionando con los 6 roles semilla.
- Shell de aplicación (sidebar, navbar) con navegación filtrada por rol.
**Riesgos:** diferencias sutiles de accesibilidad al migrar de HTML plano a componentes React — mitigación: re-ejecutar el mismo checklist de `better-accessibility` ya aplicado al login original sobre la versión migrada.

## Sprint 3 — Módulo Equipos (I)
**Objetivos:** CRUD completo de equipos con ficha técnica.
**Historias:** RF-EQ-01 a RF-EQ-04, RF-EQ-06, RF-EQ-07.
**Entregables:** listado filtrable, formulario de alta/edición, ficha de detalle, soft delete.
**Riesgos:** validaciones de negocio duplicadas entre frontend y backend desincronizadas — mitigación: Zod (frontend) y Pydantic (backend) generados/derivados de un mismo contrato documentado en `15-api-design.md`.

## Sprint 4 — Módulo Equipos (II) + QR + cierre de MVP
**Objetivos:** completar el módulo Equipos y cerrar la Fase 2.
**Historias:** RF-EQ-05, RF-EQ-08 a RF-EQ-11, RF-QR-01 a RF-QR-04, Dashboard inicial.
**Entregables:** generación de QR, vista pública QR, exportación PDF/Excel, historial de auditoría por equipo, Dashboard con KPIs disponibles hasta este punto.
**Riesgos:** la vista pública QR requiere endurecer rate limiting antes de exponerse sin autenticación — mitigación: gate de seguridad explícito antes de marcar el sprint como cerrado.
**Checkpoint:** revisión de arquitectura de fin de Fase 2 (ver `17-roadmap.md`).

## Sprint 5 — Gestor Documental (I)
**Objetivos:** subida, versionado y organización de documentos.
**Historias:** RF-DOC-01 a RF-DOC-11.
**Entregables:** drag & drop, carpetas, versionado, previsualización.
**Riesgos:** manejo de archivos grandes bloqueando el hilo principal del backend — mitigación: URLs prefirmadas desde el día 1 (ya decidido en `13-arquitectura.md`), nunca proxy de bytes.

## Sprint 6 — Gestor Documental (II)
**Objetivos:** control de vigencia y aprobación documental.
**Historias:** RF-DOC-12 a RF-DOC-14, HU-CAL-01, HU-CAL-02, HU-DT-02.
**Entregables:** estados de vigencia, flujo de aprobación, papelera con restauración.
**Riesgos:** ninguno de alto impacto identificado; sprint de complejidad media.

## Sprint 7 — Calibraciones
**Objetivos:** registrar calibraciones con cálculo automático de estado.
**Historias:** RF-CAL-01 a RF-CAL-07, HU-MET-01, HU-MET-02.
**Entregables:** formulario de calibración, cálculo de semáforo, tendencia histórica, listado de críticos.
**Riesgos:** job de recálculo diario de semáforos debe ser idempotente y no duplicar alertas — mitigación: diseño de RN-ALT-01 ya definido antes de este sprint.

## Sprint 8 — Mantenimientos + Alertas
**Objetivos:** cerrar el ciclo operativo con mantenimientos y notificaciones automáticas.
**Historias:** RF-MANT-01 a RF-MANT-05, RF-ALT-01 a RF-ALT-06, HU-TEC-01.
**Entregables:** módulo de mantenimientos, centro de alertas, outbox de notificaciones, WebSocket con fallback a polling.
**Riesgos:** gestión de conexiones WebSocket concurrentes — mitigación: fallback a polling ya decidido, y prueba de carga básica antes de cerrar el sprint.

## Sprint 9 — Calendario + Búsqueda Global
**Objetivos:** unificar la visibilidad operativa.
**Historias:** RF-CAL2-01 a RF-CAL2-05, RF-SEARCH-01 a RF-SEARCH-05.
**Entregables:** calendario multi-vista, omnibox con atajo de teclado.
**Riesgos:** rendimiento de búsqueda full-text a medida que crece el volumen — mitigación: índices GIN ya contemplados en `14-base-de-datos.md`, monitoreo de tiempos de respuesta.

## Sprint 10 — Auditoría + Usuarios y Permisos (UI)
**Objetivos:** exponer en interfaz lo que ya existe en el modelo de datos desde el Sprint 1.
**Historias:** RF-AUD-01 a RF-AUD-04, RF-USR-01 a RF-USR-07, HU-ADMIN-03.
**Entregables:** pantalla de auditoría avanzada con filtros y exportación, gestión de usuarios/roles.
**Riesgos:** ninguno de alto impacto — es principalmente construcción de UI sobre datos ya generados por sprints anteriores.

## Sprint 11 — Reportes
**Objetivos:** generación de reportes profesionales, incluido el paquete de auditoría.
**Historias:** RF-REP-01 a RF-REP-08.
**Entregables:** generación síncrona y asíncrona según volumen (RNF-PERF-04), plantillas PDF corporativas.
**Riesgos:** tiempos de generación de reportes grandes — mitigación: patrón de job async ya decidido en `13-arquitectura.md`.

## Sprint 12 — Configuración
**Objetivos:** cerrar el módulo de Configuración, huérfano en la planificación original.
**Historias:** RF-CFG-01 a RF-CFG-05 (Módulo 14 — Configuración y Perfil, sin sprint asignado en la planificación original; corregido aquí porque varias decisiones de sprints anteriores ya lo daban por hecho — ver el comentario en `password_policy.py` desde el Sprint 10 y en `exportadores.py`/`CategoriaEquipoRepositorySQLAlchemy` desde los Sprints 3 y 11), HU-CO-01.
**Entregables:** módulo de Configuración (perfil propio, tema, umbrales de alerta, datos institucionales, categorías/áreas/frecuencias), umbrales de alerta configurables por laboratorio (antes hardcodeados) y política de contraseña configurable.
**Riesgos:** umbrales configurables tocan código ya usado por Calibraciones, Alertas y Reportes — mitigación: se centraliza la lectura de configuración en un único punto por repositorio en vez de propagar `laboratorio_id`/config por cada firma de función.
**Nota:** el objetivo original de este sprint incluía cerrar la Fase 5 completa (HU-ALL-01, accesibilidad y rendimiento en toda la plataforma) — resultó ser más de lo que un sprint puede sostener con calidad real, así que ese alcance se movió al Sprint 13.

## Sprint 13 — Observabilidad, portabilidad de datos y cierre de Fase 5
**Objetivos:** completar lo que quedó pendiente de la Fase 5 tras el Sprint 12.
**Historias:** HU-ALL-01 (completo), NFRs de accesibilidad y observabilidad de `04-requerimientos-no-funcionales.md`, "Onboarding de nuevos laboratorios" y "Exportación de datos del tenant" de `17-roadmap.md` Fase 5.
**Entregables:**
- Logs estructurados (JSON) con `trace_id` de correlación en API y worker — gate de `19-checklist.md` nunca satisfecho en ningún sprint anterior.
- Script de alta de laboratorio (provisiona tenant + Administrador inicial) — "gestionado manualmente en v1" según el propio roadmap, no se construye una UI/rol Superadmin completo sin evidencia de que se necesite.
- Exportación/portabilidad de datos del tenant: ZIP de CSVs de las entidades del laboratorio, reutilizando el patrón async de Reportes (Sprint 11).
- Auditoría de accesibilidad real (no superficial) sobre los módulos ya construidos, con hallazgos concretos corregidos, no solo una casilla marcada.
**Riesgos:** una auditoría WCAG 2.2 AA verdaderamente exhaustiva de 12 módulos frontend excede lo que se puede verificar manualmente con rigor en un solo sprint — mitigación: combinar barrido estructural (grep de anti-patrones conocidos) con verificación dirigida en navegador sobre páginas representativas, documentando explícitamente qué se verificó y qué queda como riesgo residual en vez de reclamar cobertura total sin evidencia. El "piloto real con un laboratorio" del objetivo original de Fase 5 queda fuera de lo que este equipo puede completar de forma autónoma (requiere un laboratorio externo real) — se deja como paso de negocio pendiente tras el cierre técnico.

## Sprint 14 — Cierre de loops abiertos por sprints anteriores
**Objetivos:** con el módulo de Configuración ya completo (Sprint 12), cerrar dos piezas que sprints anteriores dejaron explícitamente documentadas como "pendiente cuando exista Configuración" en vez de dejarlas como deuda silenciosa.
**Historias:** RN-MANT-01 ("configurable por tipo", `07-reglas-de-negocio.md`, pendiente desde el Sprint 8), RF-CFG-04 ("información para reportes", pendiente desde el Sprint 11).
**Entregables:**
- Asignación tipo de mantenimiento → estado operativo del equipo, configurable por laboratorio (antes fija en código).
- Logo institucional embebido en el encabezado de los reportes PDF (tabulares y el paquete de auditoría), con degradación silenciosa (sin logo) si el laboratorio no configuró uno o si la descarga desde MinIO falla — un adorno de encabezado no debe tumbar la generación de un reporte.
**Riesgos:** ninguno de alto impacto — cambios contenidos a un único call site cada uno (`MantenimientoService.iniciar`, `exportar_bytes`), verificados con pruebas automatizadas y generación real de PDF contra MinIO.

## Sprint 15 — Health checks de backend y worker
**Objetivos:** cerrar el último punto pendiente de observabilidad de la Fase 5 (`17-roadmap.md`) que el Sprint 13 dejó sin tocar.
**Historias:** NFR de observabilidad, gate de `19-checklist.md` "Health check expuesto para todo servicio nuevo" — nunca satisfecho para `backend`/`worker` (solo `postgres`/`minio` lo tenían).
**Entregables:**
- `docker-compose.yml`: healthcheck real para `backend` (su propio endpoint `/health`, antes no verificado por compose pese a existir).
- Heartbeat en archivo para `worker` (no expone HTTP) — se actualiza tras cada ciclo de barrido; el healthcheck verifica que no lleva más del doble del intervalo de barrido sin actualizarse.
- `worker` ahora espera a que `backend` esté `service_healthy` (antes solo `service_started`) — cierra una ventana de condición de carrera con las migraciones que un comentario en el código ya señalaba como riesgo aceptado.
**Riesgos:** ninguno — ambos healthchecks usan solo la librería estándar de Python (sin `curl` ni dependencias de sistema nuevas en la imagen).

## Sprint 16 — Cobertura de pruebas de frontend

**Objetivos:** el backend alcanzaba 92% de cobertura (`pytest --cov`), pero el frontend tenía solo una suite (`LoginPage.test.tsx`) pese a contar con el mismo stack de pruebas (Vitest + Testing Library) ya configurado desde el inicio del proyecto — una brecha real de calidad, no una historia de usuario nueva. Se presentó la disyuntiva al Product Owner (seguir cerrando funcionalidad vs. construir esta cobertura) y se eligió explícitamente construir las pruebas antes de continuar.
**Historias:** ninguna nueva — cierre de deuda de calidad sobre RF-CAL2-01..05 (Calendario), RF-CFG-01..05 (Configuración), RF-USR-01..07 (Usuarios) y RF-SEARCH-01..05 (Omnibox), todas ya entregadas en sprints anteriores.
**Entregables:**
- 61 pruebas nuevas (antes: 2) sobre 9 archivos nuevos: lógica pura de calendario y navegación, hook `useDebouncedValue`, y pruebas de componente para `ConfiguracionPage` (gating por rol), `PerfilSection`, `AlertasSection`, `UsuarioFormulario` y `Omnibox`.
- Bug real corregido: `avanzar()` en `CalendarioPage.tsx` desbordaba de mes al navegar desde los días 29-31 (`Date.setMonth()` sin clamp de día) — mismo patrón ya resuelto en el backend en `calibraciones` (Sprint 7), encontrado por tener por primera vez una prueba de esa función.
- Bug de accesibilidad real corregido, sistémico: `Input`, `Select`, `Textarea` y `Checkbox` (`shared/components/ui/`) resolvían el `id` del control con `id ?? props.name`, sin tercer valor de respaldo — cualquier formulario que no usara react-hook-form (todos excepto el login) quedaba con `<label>` sin `htmlFor` real, rompiendo la asociación label/control para lectores de pantalla (WCAG 1.3.1/4.1.2) en Configuración, Calendario, Mantenimientos, Usuarios y Equipos. Pasó inadvertido en la auditoría WCAG del Sprint 13 porque es invisible a inspección visual y a un lector de pantalla que use heurísticas de adyacencia. Corregido con `useId()` como respaldo final en los 4 componentes base — encontrado porque `getByLabelText` (la forma estándar de Testing Library de ubicar campos) falló en la primera prueba de un formulario de Configuración.
**Riesgos:** ninguno de alto impacto — cobertura de componentes restante (formularios de Equipos, Documentos, Calibraciones, Mantenimientos) queda fuera de este sprint; se priorizaron los formularios ya identificados como críticos (gating por rol, cambio de contraseña con revocación de sesión, alertas/umbrales, creación de usuarios, búsqueda global) en vez de perseguir 100% de cobertura de componentes sin evidencia de que aporte tanto valor como el resto del roadmap.

## Sprint 17 — Cierre de RN-CAL-04 (alerta crítica por calibración no conforme)

**Objetivos:** al buscar el siguiente gap real tras el Sprint 16, se auditaron los riesgos abiertos de `00-analisis-critico-y-recomendaciones.md` y las reglas de negocio de `07-reglas-de-negocio.md` contra su implementación real (no solo contra lo documentado). Se encontró que **RN-CAL-04** — "un resultado de calibración 'No conforme' genera automáticamente una alerta crítica" — estaba documentado desde el Sprint 7 pero nunca conectado en el código: `RESULTADOS_CALIBRACION` aceptaba `"no_conforme"` como valor válido, pero `CalibracionService._crear_fila` no generaba ninguna alerta al recibirlo. Ningún test del proyecto cubría este caso.
**Historias:** RN-CAL-04 (`07-reglas-de-negocio.md`), sin RF nuevo — es cierre de una regla ya comprometida sobre un módulo existente (Calibraciones, Sprint 7).
**Entregables:**
- `CalibracionService._crear_fila` genera una alerta crítica (`AlertaService.generar_si_no_existe`) cuando `resultado == "no_conforme"`, con `origen_id=calibracion.id` — deliberadamente distinto del `origen_id=equipo_id` que ya usan las alertas de vencimiento del barrido periódico (`evaluador_service.py`) para el mismo `origen_tipo="calibracion"`, evitando que RN-ALT-01 (deduplicación) las colapse en una sola o que `resolver_por_origen` de una resuelva la otra por accidente.
- La alerta requiere resolución manual (`alertas.gestionar`) — no se auto-resuelve con una calibración posterior, ni "conforme" ni "no_conforme": un resultado fallido debe revisarse explícitamente, consistente con la letra de la propia regla ("no lo abre automáticamente — requiere confirmación humana").
- 4 pruebas nuevas (`test_calibraciones_rn04_sprint17.py`): alerta generada en no-conforme, ninguna alerta en conforme, coexistencia sin colisión con la alerta de vencimiento, y no-resolución accidental por un registro posterior.
- Limpieza menor: comentario obsoleto en `seed_roles_permisos.py` que referenciaba un TODO en `dependencies.py` ya resuelto en un sprint anterior y nunca limpiado.
**Riesgos:** ninguno — cambio contenido a un único call site, 218/218 pruebas de la suite completa del backend pasando, mypy y ruff limpios. Se investigó también "Verificaciones intermedias de equipos" (propuesta del arquitecto en `00-analisis-critico-y-recomendaciones.md` sección 4, listada en `17-roadmap.md` Fase 3) — a diferencia de RN-CAL-04, esa es una funcionalidad nueva sin RF/RN propios ya definidos, no una regla ya comprometida sin implementar; queda pendiente de diseño y decisión explícita del Product Owner antes de construirse, no se improvisa su modelo de datos en este sprint.

## Sprint 18 — Cierre de RN-EQ-03 (bloqueo de activación por calibración vencida)

**Objetivos:** siguiendo la misma auditoría "reglas documentadas vs. implementación real" que encontró RN-CAL-04 en el Sprint 17, se revisó el resto de `07-reglas-de-negocio.md` contra el código. **RN-EQ-03** — "un equipo no puede pasar a estado 'Operativo' si tiene una calibración en estado 'Vencido' marcada como crítica para su operación (configurable por categoría de equipo)" — estaba documentada desde el Sprint 3 pero `categorias_equipo` no tenía dónde guardar esa configuración "por categoría", así que la regla nunca pudo conectarse.
**Historias:** RN-EQ-03 (`07-reglas-de-negocio.md`), sin RF nuevo — mismo patrón que el Sprint 17: cierre de una regla ya comprometida, no invención de alcance.
**Entregables:**
- `categorias_equipo.bloquea_activacion_si_calibracion_vencida` (BOOLEAN, `DEFAULT false` — un Administrador debe optar explícitamente por categoría; no se activa retroactivamente para categorías existentes).
- `EquipoRepository.tiene_calibracion_vencida_bloqueante(equipo_id)` (nuevo puerto, implementado en infraestructura con un import directo del modelo `Calibracion` de Calibraciones — mismo patrón ya establecido de que el CRUCE de módulos ocurre en la capa de infraestructura vía SQLAlchemy, nunca en dominio/aplicación) — True solo si el equipo tiene categoría, esa categoría tiene el bloqueo activado, Y su última calibración registrada está vencida (`proxima_fecha` en el pasado). Un equipo sin categoría, con categoría sin bloqueo, o nunca calibrado ("gris", no "Vencido" — RN-CAL-01) nunca bloquea.
- `EquipoService.actualizar()` verifica esto cuando `estado_operativo == "operativo"`, antes de persistir — `409 calibracion_vencida_bloquea_activacion` si corresponde.
- CRUD de categorías (`ReferenciaService`, RF-CFG-05) extendido con el nuevo campo; UI en `CategoriasAreasSection.tsx` (checkbox "Bloquea activar el equipo si su calibración está vencida" en el formulario de alta/edición de categoría, indicador en el listado).
- 6 pruebas backend nuevas (`test_equipos_rn03_sprint18.py`): bloqueo activo con categoría configurada, sin bloqueo si la categoría no lo exige, sin categoría, equipo nunca calibrado (gris ≠ vencido), calibración vigente reemplaza a la vencida como "última", y que una edición que no pide pasar a "operativo" nunca dispara la regla.
**Riesgos:** ninguno — 224/224 pruebas del backend y 61/61 del frontend pasando, mypy y ruff limpios, typecheck y eslint del frontend limpios. Nota de proceso: `PATCH /equipos/{id}` es reemplazo completo (semántica PUT, no parche parcial) — detalle ya existente, no introducido por este sprint, pero que causó una prueba propia fallida al omitir `categoria_id` en el cuerpo; corregido en la prueba, documentado inline para quien escriba la próxima.

## Sprint 19 — Cierre de RN-DOC-03 (ventana de retención + purga de la papelera)

**Objetivos:** continuando la auditoría "reglas documentadas vs. implementación real" de los Sprints 17-18, se revisó Documentos. **RN-DOC-03** — "un documento eliminado puede restaurarse dentro de una ventana configurable (por defecto 30 días); pasado ese plazo, pasa a purga automática programada, no eliminación inmediata silenciosa" — estaba documentada desde el Sprint 5. Solo la mitad estaba construida: `enviar_a_papelera`/`restaurar` existían como soft delete reversible, pero `restaurar()` no tenía límite de tiempo (una fila eliminada hace un año era tan restaurable como una de ayer) y no existía ningún job de purga — sin él, cerrar solo el primer hueco habría dejado documentos vencidos atascados para siempre (ni restaurables ni purgados), peor que no tocar nada.
**Historias:** RN-DOC-03 (`07-reglas-de-negocio.md`), sin RF nuevo.
**Entregables:**
- `configuraciones_laboratorio.dias_retencion_papelera_documentos` (INT, `DEFAULT 30`), reutilizando el mismo endpoint `PATCH /configuracion/umbrales` que ya centraliza el resto de umbrales configurables por laboratorio (Sprint 12) — sin endpoint nuevo.
- `DocumentoService.restaurar()` ahora calcula los días transcurridos desde `eliminado_en` contra la retención configurada y responde `409 papelera_ventana_expirada` si ya venció (límite inclusivo: exactamente 30 días con la retención por defecto todavía permite restaurar).
- `DocumentoService.purgar_papelera_vencida()` (nuevo, invocado solo por el worker — no hay endpoint HTTP, es una acción programada del sistema sin usuario detrás, mismo criterio que `EvaluadorAlertasService`): elimina físicamente el documento, sus versiones y el/los binario(s) en MinIO — la única eliminación física de todo el proyecto, en contraste deliberado con el resto del ciclo de vida (siempre soft delete/append-only). Orden de borrado explícito por las FK sin `ON DELETE CASCADE`: se limpia `documentos.version_vigente_id` antes de poder borrar `documentos_versiones`, luego las tablas puente (`documentos_etiquetas`, `documentos_favoritos`), luego el documento.
- `AlmacenamientoMinIO.eliminar_objeto()` (nuevo) y `AlmacenamientoPort.eliminar_objeto` (puerto) — primer caso de borrado real de un objeto en todo el proyecto (todo lo demás sube/copia/descarga, nunca borra).
- Worker: cuarto paso del ciclo de barrido (junto a alertas, notificaciones y reportes), documentado en el docstring del módulo.
- UI: el campo de retención vive junto a los demás umbrales en `AlertasSection.tsx` (Configuración → Alertas), con su propia etiqueta para no confundirse con un umbral de alerta más.
- 4 pruebas backend nuevas (`test_documentos_rn03_sprint19.py`, corriendo contra Postgres y MinIO reales): bloqueo pasada la ventana, límite inclusivo exacto, ventana configurable por laboratorio, y purga real verificando que el documento expirado desaparece de la papelera, dejó de ser restaurable (404), y su binario ya no existe en MinIO (`S3Error` al intentar descargarlo) — mientras un documento activo y uno reciente en papelera quedan intactos.
**Errores encontrados y corregidos en el camino:** `datetime.utcnow() - documento.eliminado_en` reventaba con `TypeError: can't subtract offset-naive and offset-aware datetimes` — `eliminado_en` viene de una columna `TIMESTAMPTZ` (tz-aware) y `datetime.utcnow()` es naive. Corregido a `datetime.now(UTC)`, mismo patrón ya establecido en `auth_service.py` para comparaciones de expiración de sesión — encontrado por la suite completa de pruebas (dos pruebas preexistentes de Documentos fallaron primero), no por una prueba nueva.
**Riesgos:** ninguno de alto impacto — 228/228 pruebas del backend y 61/61 del frontend pasando, mypy/ruff/tsc/eslint limpios. La purga es irreversible por diseño (es justamente lo que pide la regla), así que corre exclusivamente desde el worker, nunca desde un endpoint que un usuario pueda invocar por accidente.

## Sprint 20 — Rediseño del Dashboard

**Objetivos:** el Dashboard inicial (Sprint 4) mostraba KPIs básicos pero no reflejaba el nivel de diseño ya validado en el resto de la plataforma. Se aprobó un mockup HTML y se implementó sobre datos reales.
**Historias:** ninguna nueva — rediseño de superficie sobre datos ya expuestos por Equipos, Calibraciones, Documentos, Mantenimientos y Auditoría.
**Entregables:**
- `DashboardService` (backend) agregando KPIs vía los repositorios existentes, sin duplicar lógica de negocio — 2 endpoints nuevos (`/dashboard/equipos-criticos`, `/dashboard/actividad-reciente`, este último protegido por `auditoria.ver`) y `/dashboard/kpis` extendido.
- 8 componentes nuevos en el frontend (KPI cards, estado de equipos, agenda de calibraciones, línea de tiempo de actividad, resumen de alertas, acciones rápidas, tabla de equipos críticos, tarjeta de asistente).
**Errores encontrados y corregidos en el camino:**
- Bug real de `recharts@3`: un único segmento con el 100% del total (caso común: "todos los equipos operativos") renderiza un arco degenerado invisible. Corregido reemplazando el gráfico de dona por SVG hecho a mano (`arcosDelDonut`, con pruebas propias) en vez de pelear con la librería.
- Bug de legibilidad en modo oscuro: colores pastel claros a baja opacidad se veían turbios sobre fondo oscuro — corregido usando el color semántico plano a baja opacidad (`bg-danger/10`) en vez de un hex claro con opacidad.
- Bugs de redacción en la línea de tiempo de actividad (contracciones faltantes, texto redundante), encontrados comparando contra los literales `accion`/`entidad_tipo` reales de cada `*_service.py`, no adivinando.
**Riesgos:** ninguno de alto impacto — 5 pruebas backend y 3 pruebas frontend nuevas, mypy/ruff/tsc/eslint limpios.

## Sprint 21 — Cierre de RF-USR-04 (forzar cambio de contraseña en el primer inicio de sesión)

**Objetivos:** continuando la auditoría "documentado vs. implementado" de los Sprints 17-19, se encontró que RF-USR-04 tenía su dato de soporte (`usuarios.debe_cambiar_password`) pero ningún punto del sistema lo hacía cumplir — un usuario creado con contraseña temporal podía usar toda la plataforma indefinidamente sin cambiarla.
**Historias:** RF-USR-04 (`03-requerimientos-funcionales.md`).
**Entregables:**
- El flag viaja en el JWT (mismo patrón ya usado para `roles`) — `get_usuario_actual` bloquea con `403 debe_cambiar_password_pendiente` si está activo; `get_usuario_actual_sin_bloqueo` (sin chequeo) reservado para los 3 endpoints exentos (`/auth/me`, cambiar-password propio, actualizar-perfil propio).
- Frontend: `ProtectedRoute` redirige a `/cambiar-password` mientras el flag esté activo; `CambiarPasswordForm` extraído como componente compartido entre esa pantalla nueva y el cambio voluntario ya existente en Configuración → Mi perfil.
- 5 pruebas backend nuevas (`test_rf_usr04_sprint21.py`), 3 pruebas frontend nuevas (`ProtectedRoute.test.tsx`).
**Errores encontrados y corregidos en el camino:**
- Regresión real: bloquear los endpoints por el flag rompía la edición de perfil propio para un usuario con contraseña pendiente — corregido agregando ese endpoint a la lista de exenciones antes de cerrar el sprint (detectado por la suite completa, no por una prueba nueva).
- Race condition real, encontrada en verificación manual en navegador: al cambiar la contraseña, `cerrarSesion()` limpiaba el usuario mientras el formulario seguía montado bajo `ProtectedRoute`; el redirect propio de `ProtectedRoute` (sin mensaje) le ganaba la carrera al `navigate(..., {state: mensaje})` explícito del formulario, y el aviso "Contraseña actualizada" nunca se veía. Corregido invirtiendo el orden (navegar primero, cerrar sesión después) — afecta también al cambio voluntario desde Perfil, mismo componente compartido.
**Riesgos:** ninguno de alto impacto — 238/238 pruebas backend y 67/67 frontend pasando, mypy/ruff/tsc/eslint limpios.

## Sprint 22 — Cierre de cifrado en reposo para documentos en MinIO (RNF-SEC, `16-seguridad.md`)

**Objetivos:** `16-seguridad.md` sección 5 exige explícitamente desde la Fase 1 "Documentos en MinIO cifrados en reposo (SSE)" — una de las adiciones de seguridad que el propio arquitecto marcó como no negociable para software médico/Enterprise (`00-analisis-critico-y-recomendaciones.md` sección 3.5), junto a rotación de refresh tokens con detección de reuso y bloqueo progresivo por intentos fallidos (ambas sí estaban implementadas). El adaptador de almacenamiento (`core/almacenamiento_minio.py`) no cifraba nada — ni las subidas del navegador vía URL prefirmada (el flujo normal de Documentos/Calibraciones/Mantenimientos) ni las subidas servidor-a-servidor del worker.
**Historias:** ninguna nueva — cierre de un requisito no funcional de seguridad ya comprometido desde la Fase 1, sin RF propio.
**Entregables:**
- Cifrado por defecto a nivel de bucket (SSE-S3) en los 4 buckets de la aplicación (`documentos`, `evidencias`, `reportes`, `logos`), configurado en `asegurar_bucket()` — al vivir a nivel de bucket y no de request, cifra por igual ambos flujos de subida sin tocar ninguno de los dos ni requerir cambios en el frontend.
- `docker-compose.yml`: `MINIO_KMS_SECRET_KEY` (modo de clave maestra estática integrado de MinIO, sin necesidad de un servicio KES/Vault externo) — verificado con el binario real de MinIO (`RELEASE.2025-09-07`) antes de comprometerse al enfoque, ya que requerir infraestructura nueva no verificada hubiera sido el mismo error de sobre-ingeniería que `00-analisis-critico-y-recomendaciones.md` ya advierte evitar.
**Verificación:** reinicio real de los contenedores `minio`/`backend`, confirmado con `mc encrypt info` que los 4 buckets quedaron con "Auto encryption 'sse-s3' enabled"; subida de un objeto de prueba nuevo mostrando `Encryption: SSE-S3` en sus metadatos, contra un objeto preexistente (subido antes del cambio) sin esa marca — el cifrado por defecto de bucket nunca es retroactivo, mismo comportamiento documentado de S3. 238/238 pruebas backend pasando contra el MinIO ya cifrado (incluidas las 31 de Documentos), mypy y ruff limpios.
**Riesgos:** ninguno de alto impacto para este entorno de desarrollo — en un despliegue real, la clave del KMS debe venir de un gestor de secretos, no de `docker-compose.yml` (se documenta inline en el propio archivo, misma convención ya existente para `MINIO_ROOT_PASSWORD`). Se investigaron también las otras dos adiciones de seguridad propuestas en la sección 3.5 (separación de permisos "PII de usuario" vs. "datos operativos", y RN-TEN-02/Superadmin) — la primera no representa un riesgo real hoy porque solo Administrador tiene *algún* permiso sobre Usuarios (`usuarios.administrar` es el único rol con acceso al módulo, ningún otro rol lo recibe); la segunda es una funcionalidad nueva sin RF propio y está explícitamente fuera de alcance de v1 según `17-roadmap.md` ("Superadmin... gestionado manualmente en v1") — ninguna de las dos se improvisa en este sprint.

## Sprint 23 — Cierre de RF-QR-03 (incidencias reportadas por QR visibles para triage)

**Objetivos:** RF-QR-03 (`03-requerimientos-funcionales.md`, Módulo 13), sección "Salidas": "incidencia creada (visible luego en el módulo de Mantenimientos como solicitud pendiente de triage)". El reporte de incidencia sin autenticación existía desde el Sprint 4, pero `IncidenciaQrRepository` solo tenía `crear()` — no existía ningún endpoint, método de servicio ni pantalla para listarlas o cambiarles de estado. Cada incidencia reportada quedaba escrita en la base de datos y era invisible para siempre; ni siquiera el propio Administrador podía verla. La migración original (`0004_qr.py`) ya otorgaba `UPDATE` sobre `incidencias_qr` al rol de aplicación desde el día 1, y el modelo de dominio ya declaraba los 3 estados (`pendiente`/`en_revision`/`resuelta`) — el hueco era puramente de capa de aplicación/presentación, nunca de datos.
**Historias:** RF-QR-03, sin RN nueva.
**Entregables:**
- `IncidenciaQrRepository` gana `listar_con_equipo` (join contra `equipos` para no obligar al llamador a resolverlos uno por uno) y `actualizar_estado`.
- `GET /qr/incidencias` (permiso `equipos.leer`, igual que el resto del listado de Mantenimientos) y `PATCH /qr/incidencias/{id}/estado` (permiso `mantenimientos.crear`, el mismo que registrar el mantenimiento al que la incidencia normalmente da lugar) — este último genera un registro de auditoría (`modulo="qr"`, `entidad_tipo="incidencia_qr"`), cerrando también RN-AUD-02 para esta acción.
- Frontend: nueva sección "Incidencias reportadas por QR" en `MantenimientosListPage` (vía `IncidenciasQrPendientes`, en el feature `qr` — mismo criterio de "el dominio vive en su propio feature" que ya usa `qrApi`/`useQrPublico`) — solo muestra pendientes/en revisión, con botón de un clic para avanzar el estado (pendiente → en revisión → resuelta).
- 8 pruebas backend nuevas (`test_qr_incidencias_sprint23.py`, incluida aislamiento multi-tenant vía RLS) y 4 pruebas frontend nuevas (`IncidenciasQrPendientes.test.tsx`).
**Errores encontrados y corregidos en el camino:**
- `ip_origen` es `INET` en Postgres — pasar `request.client.host` sin sanear (`"testclient"` bajo `TestClient`) reventaba con `DataError`. Ya existía el helper `core/ip.py::ip_valida` para exactamente este caso (usado en Equipos) pero el nuevo endpoint de triage no lo estaba usando — corregido antes de que llegara a producción.
**Verificación en vivo:** reporte real desde la vista pública de QR (pestaña sin sesión) → aparece de inmediato en Mantenimientos como "Pendiente de triage" con los datos del equipo y de quien reportó → "Marcar en revisión" → "Marcar resuelta" → desaparece de la lista de pendientes → confirmado en Auditoría (`módulo=qr`, `acción=actualizar_estado_incidencia`, IP real capturada). Como efecto colateral, esta pantalla también hizo visible por primera vez una incidencia real reportada en una sesión de pruebas anterior (Sprint 4) que hasta ahora había quedado atrapada sin ningún camino de lectura.
**Riesgos:** ninguno de alto impacto — 246/246 pruebas backend y 75/75 frontend pasando, mypy/ruff/tsc limpios (4 warnings de lint preexistentes de Calendario/Sprint 20, fuera de alcance).

## Sprint 24 — Cierre de la fotografía de equipos (RF-EQ-01/RF-QR-02)

**Objetivos:** RF-EQ-01 — el requisito fundacional del Módulo 3 (Equipos, Sprint 3) — pide explícitamente "fotografía" como campo de la ficha técnica, con validación de formato (JPG/PNG/WEBP) descrita en el propio requisito. La columna `foto_url` existe en la base de datos desde la migración 0002 (Sprint 3), pero nunca se conectó a ningún servicio, endpoint ni pantalla — quedó huérfana durante ~20 sprints. RF-QR-02 depende de este mismo campo ("mostrando: foto, estado actual…" en la vista pública), así que tampoco podía cumplirse sin cerrar primero este hueco.
**Historias:** RF-EQ-01, RF-QR-02, sin RN nueva (RN-EQ-04 se extiende sin reescribirse: la fotografía no se copia al duplicar, mismo criterio ya aplicado a `numero_serie`).
**Entregables:**
- `EquipoService` gana `solicitar_url_foto`/`url_foto`, reutilizando el mismo patrón ya probado del logo institucional (`ConfiguracionService`, Sprint 12): se persiste el `object_key` de MinIO, nunca una URL resuelta (que expiraría), y se firma una URL de vista previa bajo demanda en cada lectura. El dominio expone el campo como `foto_object_key`; la columna de base de datos conserva su nombre original `foto_url` (se documenta el porqué en el propio dataclass) para no forzar una migración de renombrado sin beneficio real.
- `POST /equipos/upload-url/foto` (bucket nuevo `fotos-equipos`, heredando cifrado en reposo por defecto del Sprint 22 sin cambios adicionales) — límite de 5MB, mismos formatos que el resto de imágenes del proyecto.
- `EquipoOut.foto_url` (resuelta) en todos los endpoints de lectura; `EquipoRequest.foto_object_key` en creación/edición; `RN-EQ-04` extendida — `duplicar()` nunca copia la fotografía de la unidad física original.
- `QrService.a_vista_publica` acepta la URL ya resuelta por el router (el servicio nunca toca MinIO directamente, mismo criterio que el resto del módulo) — la vista pública de QR ahora muestra la fotografía cuando existe.
- Frontend: bloque de subida en `EquipoFormPage` (mismo componente visual que el logo de `LaboratorioSection`: miniatura + botón + subida inmediata al seleccionar el archivo, no al enviar el formulario) y miniatura de 16×16 en `EquipoDetailPage`; `QrPublicPage` muestra la fotografía a ancho completo sobre los datos del equipo.
- 8 pruebas backend nuevas (`test_equipos_foto_sprint24.py`, subida real contra MinIO vía `httpx.put`, no mockeada): formato/tamaño rechazados, URL resuelta presente tras crear/actualizar, `foto_url: null` sin fotografía, exclusión al duplicar, y exposición correcta (o su ausencia) en la vista pública de QR.
**Verificación en vivo:** subida real de una imagen de prueba desde el formulario de creación → miniatura visible de inmediato en el formulario → tras crear, miniatura visible en la ficha del equipo → fotografía a ancho completo visible en la vista pública de QR sin autenticación — cierra el ciclo completo del requisito, no solo el backend.
**Riesgos:** ninguno de alto impacto — 254/254 pruebas backend y 71/71 frontend pasando, mypy/ruff/tsc limpios (mismos 4 warnings de lint preexistentes de Calendario/Sprint 20, fuera de alcance). No se abordó en este sprint la fotografía de perfil de usuario (RF-CFG-01, el mismo patrón de campo huérfano pero sin columna de base de datos siquiera) — es un gap real pero de menor impacto (no bloquea ningún otro requisito, a diferencia de la de Equipos con RF-QR-02) y queda para un sprint futuro.

## Sprint 25 — Cierre de la fotografía de perfil de usuario (RF-CFG-01)

**Objetivos:** RF-CFG-01 pide "Editar datos de perfil propio (nombre, correo, contraseña, foto)" desde el Sprint 12 — nombre/correo/contraseña ya estaban conectados, "foto" no tenía ni columna en base de datos (a diferencia del logo institucional o la fotografía de equipos del Sprint 24, que sí tenían su columna desde el inicio). Se identificó al cerrar el Sprint 24 como el mismo patrón de gap, de menor impacto por no bloquear otro requisito, y quedó anotado para este sprint.
**Historias:** RF-CFG-01, sin RN nueva.
**Entregables:**
- Migración 0014: `usuarios.foto_object_key` (nullable, sin valor por defecto — ningún usuario existente queda afectado).
- `UsuarioService` gana `solicitar_url_foto`/`url_foto`, mismo patrón que `EquipoService`/`ConfiguracionService` (Sprints 12 y 24) — límite 2MB (una foto de perfil, no de alta resolución), mismos formatos.
- `POST /usuarios/me/upload-url/foto`, bucket nuevo `fotos-usuarios` (cifrado en reposo heredado del Sprint 22 sin cambios adicionales).
- `foto_url` (resuelta) expuesta en `/auth/login`, `/auth/refresh`, `/auth/me` y `/usuarios/me` — el avatar debe reflejarse en cualquier lugar donde ya se mostraba la identidad del usuario, no solo en la pantalla de perfil.
- Frontend: bloque de subida en `PerfilSection` (mismo patrón visual que el logo institucional y la foto de equipos); `Navbar` reemplaza el ícono genérico de usuario por la fotografía real, tanto en el botón de perfil como en el menú desplegable.
- 8 pruebas backend nuevas (`test_usuarios_foto_sprint25.py`, subida real contra MinIO).
**Bug real encontrado y corregido en el camino (antes de que llegara a producción):** al construir el flujo de subida de foto de equipos en el Sprint 24, `EquipoOut` solo exponía `foto_url` (una URL prefirmada que expira), nunca el `object_key` estable. El formulario de edición, al no tener manera de "reenviar la foto actual sin tocarla", omitía el campo en cualquier PATCH que solo cambiara otro dato (p. ej. el nombre) — Pydantic completaba `None` por defecto, y `actualizar()` borraba la fotografía en cada edición no relacionada. El propio código de `Institucion`/`logo_object_key` (Sprint 12) ya documentaba exactamente este riesgo en un comentario que se pasó por alto al construir la ficha de Equipos. Corregido en ambos módulos (Equipos y, desde el diseño, Usuarios) exponiendo el `object_key` junto a la URL resuelta y reenviándolo siempre tal cual desde el formulario — con una prueba de regresión dedicada en cada módulo (`test_actualizar_otro_campo_sin_reenviar_foto_no_la_borra`, `test_respuestas_exponen_foto_object_key_estable`) para que no vuelva a pasar inadvertido.
**Verificación en vivo:** subida real de una fotografía desde Configuración → miniatura circular inmediata → avatar del Navbar actualizado en el acto → tras recargar la página, foto y nombre persistidos → edición del nombre sin volver a tocar la foto → foto conservada tanto en el formulario como en el Navbar tras guardar y recargar (verificación explícita del bug corregido).
**Riesgos:** ninguno de alto impacto — 262/262 pruebas backend (8 nuevas de este sprint + 2 de regresión) y 72/72 frontend pasando, mypy/ruff/tsc limpios.

## Sprint 26 — Cierre del manual de usuario de equipos (RF-EQ-01, segunda mitad)

**Objetivos:** al cerrar el Sprint 24 (fotografía de equipos) quedó anotado que RF-EQ-01 pide DOS archivos en la ficha técnica — "manual de usuario (archivo)" y "fotografía" — y solo se cerró la foto; el manual seguía sin columna, sin endpoint y sin pantalla. Confirmado que Documentos (el gestor documental del laboratorio) no tiene ningún vínculo con `equipo_id` — el manual de un equipo es un campo propio de su ficha técnica, no algo que ya estuviera cubierto por otro módulo con otro nombre.
**Historias:** RF-EQ-01, sin RN nueva.
**Entregables:**
- Migración 0015: `equipos.manual_object_key` (nullable).
- `EquipoService` gana `solicitar_url_manual`/`url_manual` — mismo patrón que la foto, pero resuelto con `url_descarga` (disposición attachment), no `url_vista_previa`: un manual es un documento de referencia para descargar, no una imagen para mostrar inline (mismo criterio que `MantenimientoService.url_informe`, Sprint 8). Requirió que `EquipoService` aceptara dos instancias de almacenamiento (`_almacenamiento_fotos`/`_almacenamiento_manuales`) — foto y manual viven en buckets separados, un tipo de contenido lógico por bucket.
- `POST /equipos/upload-url/manual`, bucket nuevo `manuales-equipos` (cifrado en reposo heredado del Sprint 22).
- **Decisión deliberadamente distinta a la foto en `duplicar()` (RN-EQ-04):** la fotografía no se copia (es de la unidad física original), pero el manual **sí se copia** — describe el modelo/tipo de equipo, no una unidad física específica, así que es tan válido para la copia como para el original. RN-EQ-04 solo excluye historial de calibraciones/mantenimientos, no campos de ficha técnica como este.
- Frontend: bloque de subida en `EquipoFormPage` (sin miniatura de imagen, muestra el nombre del archivo recién subido o un enlace "Descargar manual actual"); enlace "Descargar manual de usuario" en `EquipoDetailPage`.
- 6 pruebas backend nuevas (`test_equipos_manual_sprint26.py`, subida real contra MinIO), incluida una prueba de regresión explícita para el mismo bug de "omitir el object_key borra el archivo" corregido en el Sprint 25, y otra confirmando la copia intencional al duplicar (comportamiento opuesto al de la foto, verificado explícitamente para que no se confunda con un descuido).
**Verificación en vivo:** edición del equipo de fotografía del Sprint 24 (ya tenía foto) → subida real de un PDF → foto original preservada, manual mostrado como "Reemplazar manual" con el nombre del archivo → al guardar, auditoría registra `manual_object_key` como campo modificado → enlace "Descargar manual de usuario" visible en la ficha → descarga real verificada por código y tamaño de contenido, confirmando que el archivo servido es exactamente el subido.
**Riesgos:** ninguno de alto impacto — 268/268 pruebas backend (6 nuevas) y 72/72 frontend pasando, mypy/ruff/tsc limpios.

## Sprint 27 — Paginación real del listado general de Mantenimientos (RNF-PERF-03)

**Objetivos:** `RNF-PERF-03` (docs/04-requerimientos-no-funcionales.md): "Las listas con más de 50 elementos deben usar paginación o virtualización — nunca renderizar el listado completo de una vez." Equipos y Auditoría ya lo cumplían (paginación real y un `.limit()` respectivamente), pero `GET /mantenimientos` traía absolutamente todo el laboratorio sin límite alguno — ni siquiera un `.limit()` en la consulta SQL — y el frontend renderizaba la lista completa de una sola vez. Un laboratorio con más de unas pocas decenas de mantenimientos habría cargado esa lista completa en cada visita a la pantalla.
**Historias:** ninguna nueva — cierre de un requisito no funcional ya comprometido, sin RF propio.
**Entregables:**
- `FiltrosMantenimiento` gana `pagina`/`tamano_pagina` (mismo patrón que `FiltrosEquipo`); `MantenimientoRepository.listar()` ahora devuelve `PaginaMantenimientos` (`items`/`total`/`pagina`/`tamano_pagina`) en vez de una lista plana.
- `GET /mantenimientos` pagina de verdad (20 por página) cuando se consulta el laboratorio completo; una ficha de equipo individual (`equipo_id` presente) sigue trayendo todo su historial en una sola página — el límite es para la vista agregada, no para el historial de una ficha, que naturalmente es mucho más pequeño.
- `MantenimientosListPage` gana controles de paginación (Anterior/Página X de Y/Siguiente), mismo componente visual que `EquiposListPage`.
**Bug real encontrado y corregido antes de que llegara a producción:** al paginar `listar()`, cuatro consumidores internos que llamaban directo al repositorio se habrían roto o, peor, habrían quedado silenciosamente truncados a la primera página: los KPIs del Dashboard (conteo de mantenimientos correctivos abiertos), la exportación de datos del tenant (Sprint 13), el reporte de "historial de mantenimiento" (RF-REP-05) y la generación de eventos de Calendario. Los cuatro necesitan el conjunto **completo**, no una página — un KPI o un reporte que solo contara los primeros 20/200 registros de un laboratorio con más historial habría sido un error silencioso, no un error visible. Se agregó `MantenimientoRepository.listar_todos()` (sin paginar, mismo criterio que `EquipoRepository.listar_todos`, RF-EQ-08) y se migraron los cuatro consumidores a usarlo — con una prueba de regresión explícita verificando que los KPIs cuentan el total real, no la primera página.
**Verificación en vivo:** creación de 22 mantenimientos reales sobre un mismo equipo → el listado general del laboratorio muestra "Página 1 de 2" con controles Anterior/Siguiente funcionando correctamente → la ficha del equipo (historial por equipo) sigue mostrando los 22 registros completos, sin truncar.
**Riesgos:** ninguno de alto impacto — 271/271 pruebas backend (3 nuevas) y 72/72 frontend pasando, mypy/ruff/tsc limpios. No se tocó la paginación de otras listas del proyecto (quedan fuera de alcance de este sprint salvo que se confirme un problema real similar).

## Sprint 28 — Paginación real del Centro de Alertas (RNF-PERF-03, segundo hallazgo)

**Objetivos:** al auditar qué otras listas podían tener el mismo problema recién cerrado en Mantenimientos (Sprint 27), se encontró el mismo patrón exacto en Alertas: `GET /alertas` traía todo el laboratorio sin ningún `.limit()`. Es un caso real porque ninguna alerta se purga nunca (activa o resuelta, quedan todas) — un laboratorio con suficiente historial operativo termina acumulando cientos de filas.
**Historias:** ninguna nueva — mismo cierre de RNF ya comprometido, sin RF propio.
**Entregables:**
- `FiltrosAlerta` gana `pagina`/`tamano_pagina`; `AlertaRepository.listar()` devuelve `PaginaAlertas` en vez de una lista plana. A diferencia de Mantenimientos, aquí no hizo falta un `listar_todos()` separado — el único consumidor interno de `listar()` es el propio endpoint HTTP, nada más depende del conjunto completo.
- `GET /alertas` pagina de verdad (20 por página, configurable hasta 100).
- `AlertasPage` gana controles de paginación (mismo patrón ya usado en Equipos y Mantenimientos).
**Bug real encontrado y corregido de paso (no era el objetivo original del sprint, pero es el mismo síntoma):** tanto `NotificacionesBell` (el panel de la campana en el Navbar) como `AlertsSummary` (el widget del Dashboard) traían **todas** las alertas activas del laboratorio por la red y recién ahí recortaban a 8 y 4 respectivamente del lado del cliente (`.slice(0, N)`) — un sobre-fetch real e innecesario en cada apertura de cualquiera de las dos pantallas. Ambos se migraron a pedir `tamano_pagina` directamente al servidor.
**Verificación en vivo:** con datos reales del laboratorio de desarrollo — Centro de Alertas, panel de la campana y widget del Dashboard, los tres renderizando correctamente tras el cambio; el KPI "correctivos abiertos" del Dashboard (que depende de `MantenimientoRepository.listar_todos`, Sprint 27) sigue contando el total real, confirmando que ese fix anterior sigue intacto.
**Riesgos:** ninguno de alto impacto — 274/274 pruebas backend (3 nuevas) y 72/72 frontend pasando, mypy/ruff/tsc limpios. Se revisaron Calibraciones y Documentos por el mismo patrón — Documentos ya paginaba (Sprint 5) y las consultas de Calibraciones son una fila por equipo (acotadas por el número de equipos, no por eventos históricos), así que no comparten el mismo riesgo de crecimiento sin límite.

---

## Fase 0 — Auditoría integral y correcciones críticas (2026-07-31 a 2026-08-04)

**Objetivos:** antes de seguir cerrando gaps funcionales sprint a sprint, se realizó una auditoría completa del proyecto (arquitectura, backend, frontend, base de datos, seguridad, rendimiento, accesibilidad, documentación) actuando como Staff Software Engineer / Principal Architect. El informe resultante se priorizó en Críticos/Importantes/Mejoras/Riesgos futuros, y se cerraron los 5 hallazgos críticos (C1-C5) uno a la vez, con aprobación explícita entre cada uno.
**Historias:** ninguna — cierre de deuda técnica y de seguridad ya acumulada, no requisito funcional nuevo.
**Entregables (ver detalle completo en el Informe Final de Cierre de la Fase 0):**
- **C1** — el worker ya no bloquea el outbox de notificaciones completo cuando una sola notificación falla al enviarse (`app/worker/main.py`, commit y `marcar_fallida()` por notificación individual).
- **C2** — 8 componentes de frontend (Alertas, Mantenimientos, Usuarios, Auditoría, Calibraciones críticas, Documentos, campana de notificaciones, widget del Dashboard) dejaron de mostrar "sin datos" cuando en realidad la petición había fallado.
- **C3** — migración `0016`: 13 `CHECK constraint` nuevos en columnas de estado/tipo que solo estaban validadas en la capa de aplicación.
- **C4** — `docs/13-arquitectura.md` reescrito para describir únicamente la infraestructura que existe hoy (sin Nginx/TLS/balanceador/despliegue de producción, que no existen en el repositorio); todo lo planeado se movió a una sección explícita "Arquitectura futura".
- **C5** — rate limiting real en `/login` y `/refresh` (`app/core/rate_limit.py`, `app/core/config.py`), configurable por variable de entorno, compatible con un futuro reverse proxy vía `ProxyHeadersMiddleware`.
**Verificación:** cada corrección se verificó de forma aislada (mypy/ruff/pytest en backend, tsc/eslint/vitest/build en frontend cuando aplicaba) antes de pasar a la siguiente — ver el detalle de pruebas de cada una en el Informe Final de Cierre de la Fase 0.
**Riesgos:** ninguno de alto impacto introducido por las correcciones mismas — el detalle de riesgos residuales y deuda técnica pendiente (los hallazgos Importantes/Mejoras/Riesgos futuros del informe original que quedaron fuera del alcance de esta fase) se documenta en el Informe Final de Cierre.

---

## Nota de proceso

Cada sprint cierra con: demo funcional (no solo código mergeado), retroalimentación del Product Owner, y actualización de este documento si la realidad de construcción difiere de lo planificado — consistente con el principio de `00-analisis-critico-y-recomendaciones.md` de que este blueprint es v1.0, no un contrato inmutable.
