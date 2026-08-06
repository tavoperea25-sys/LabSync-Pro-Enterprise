# 21 — Informe Final de Auditoría v1.0

**LabSync Pro Enterprise — Auditoría integral 2026-07-31, cierre de Fase 0 y Fase 1 (2026-08-04)**

Documento de cierre, versionado y estable — a diferencia de `20-auditoria-2026-07-31.md` (el registro vivo, actualizado hallazgo por hallazgo durante el trabajo), este documento es la síntesis final para revisión y aprobación antes de iniciar la siguiente fase (M1-M11). No se modifica código en este documento ni en su preparación.

---

## 1. Resumen ejecutivo

Entre el 31-jul-2026 y el 04-ago-2026 se auditó LabSync Pro Enterprise de punta a punta (arquitectura, backend, frontend, base de datos, seguridad, rendimiento, accesibilidad, escalabilidad y documentación). El informe original catalogó 42 hallazgos (5 críticos, 12 importantes, 11 mejoras recomendadas, 9 opcionales, 5 riesgos de escalabilidad). Se abordaron los 5 críticos y 5 de los 12 importantes, cada uno con su propia verificación completa y aprobación explícita antes de continuar al siguiente — más 2 hallazgos que no estaban en el informe original y aparecieron durante la propia ejecución (ver sección 6).

**Resultado medible:**
- Backend: de 274 a **318 pruebas**, cobertura total 93%→95%, cero regresiones en ningún paso.
- Frontend: de 72 a **103 pruebas**, bundle JS inicial reducido en **59%** (1.127 kB → 463 kB), cero regresiones.
- **1 bug de producción real** encontrado y corregido que no estaba en el informe original (C6), más 1 hallazgo de rendimiento adicional medido y registrado para la siguiente fase (I13) — ambos aparecieron escribiendo pruebas de recuperación/medición, no por inspección de código.
- Documentación de arquitectura, base de datos y API reescrita para reflejar exactamente lo que existe hoy, con lo planeado a futuro separado explícitamente en su propia sección.

## 2. Métricas globales

| Métrica | Valor |
|---|---|
| Hallazgos del informe original (todas las severidades) | 42 (5 críticos + 12 importantes + 11 recomendadas + 9 opcionales + 5 riesgos) |
| Hallazgos abordados en Fase 0 + Fase 1 | 12 (6 críticos incl. C6 + 6 importantes incl. I13) |
| Hallazgos corregidos | 11 |
| Hallazgos medidos y registrados, pendientes de corrección | 1 (I13) |
| Bugs de producción descubiertos durante la ejecución (no en el informe original) | 1 (C6) |
| Hallazgos de rendimiento descubiertos durante la ejecución (no en el informe original) | 1 (I13 — una medición, no un bug) |
| Pruebas backend añadidas | 44 (274 → 318) |
| Pruebas frontend añadidas | 31 (72 → 103) |
| **Total de pruebas nuevas** | **75** |
| Regresiones detectadas en el estado final entregado | 0 |
| Builds fallidos en el estado final entregado | 0 |
| Cobertura de backend | 93% → 95% (única medición del periodo; no había línea base anterior a esta auditoría) |
| Bundle JS inicial (frontend) | −59% crudo / −55% gzip (I8) |
| Duración calendario | 2026-07-31 (auditoría original) a 2026-08-04 (cierre de Fase 0 y Fase 1) — no se registró tiempo-persona exacto por sesión |

---

## 3. Estado inicial del proyecto (antes de la auditoría)

LabSync Pro Enterprise es una plataforma SaaS multi-tenant (Row Level Security por laboratorio) para gestión de equipos de laboratorio clínico — FastAPI + PostgreSQL 16 en el backend, React 19 + TypeScript en el frontend, MinIO para almacenamiento de archivos, un worker separado para el outbox de notificaciones y reportes asíncronos. Al momento de iniciar la auditoría (28 sprints ya completados, ver `18-sprints.md`):

- Backend: 274 pruebas pasando, 93% de cobertura (medida por primera vez durante esta auditoría, en I12 — no existía una medición de línea base anterior).
- Frontend: 72 pruebas pasando, sin code-splitting de rutas (bundle único de 1.127 kB).
- mypy y ruff en verde (salvo 33 errores `E501` preexistentes en archivos de test no relacionados, nunca corregidos por no ser parte del alcance de ningún hallazgo — ver sección 11, Decisiones de alcance).
- Documentación de arquitectura (`13`), base de datos (`14`) y API (`15`) desactualizada respecto al código real en múltiples puntos, sin que hubiera un mecanismo para detectarlo sistemáticamente.

## 4. Hallazgos detectados en la auditoría original (2026-07-31)

Metodología: 3 agentes de investigación en paralelo (backend/API/seguridad; frontend/UX/accesibilidad/rendimiento; base de datos/escalabilidad/vigencia de documentación), sintetizados en un informe único con 6 secciones.

| Severidad | Cantidad original | Resueltos a la fecha |
|---|---|---|
| Crítico (C1-C5) | 5 | 5 de 5 |
| Importante (I1-I12) | 12 | 5 de 12 (I8-I12) |
| Mejora recomendada (M1-M11) | 11 | 0 — alcance de la próxima fase |
| Mejora opcional (O1-O9) | 9 | 0 — alcance de la próxima fase |
| Riesgo futuro de escalabilidad (R1-R5) | 5 | 0 — documentados, no urgentes hoy |

---

## 5. Estado final de cada hallazgo del informe original

### 5.1 Críticos — Fase 0 (C1-C5)

**C1 — Outbox de notificaciones bloqueable indefinidamente** ✅ Resuelto
Una notificación que fallaba al enviarse (p. ej. payload > 8000 bytes de `pg_notify`) revertía todo el lote y volvía a quedar primera en el ciclo siguiente — bloqueo indefinido de la cola del tenant. Corregido con commit y manejo de excepción por notificación individual; `marcar_fallida()` (existía, nunca se invocaba) ahora se llama y saca el ítem tóxico de la cola.

**C2 — Fallos de red mostrados como "sin datos"** ✅ Resuelto
8 componentes de frontend no distinguían `isError` de "0 resultados" — un fallo de red podía leerse como "no hay alertas activas". Corregido replicando el patrón `isError` ya usado en `EquiposListPage`.

**C3 — CHECK constraints faltantes en columnas de estado/tipo** ✅ Resuelto
13 columnas "tipo enum" en 8 tablas eran `VARCHAR` libre sin restricción real en base de datos. Corregido con la migración `0016` (13 `CHECK constraint`), validada contra los datos reales antes de aplicarse.

**C4 — Documentación de arquitectura describía infraestructura inexistente** ✅ Resuelto
`docs/13-arquitectura.md` documentaba una capa Nginx/TLS y un `docker-compose.prod.yml` que nunca se construyeron. Corregido reescribiendo las secciones afectadas y agregando una sección explícita "Arquitectura futura" (ver sección 10, Decisiones de arquitectura).

**C5 — Sin rate limiting en `/login` y `/refresh`** ✅ Resuelto
Único endpoint de autenticación sin protección por IP. Corregido con rate limiting configurable + compatibilidad con reverse proxy futuro (`ProxyHeadersMiddleware`), sin abrir una vía de spoofing de IP.

### 5.2 Importantes — Fase 1 (I8-I12)

**I8 — Ausencia de code-splitting a nivel de ruta (frontend)** ✅ Resuelto
Las 18 páginas se importaban de forma estática. Corregido con `React.lazy()` + `Suspense` de doble capa (uno externo, uno dentro del shell de navegación para que sidebar/navbar no desaparezcan al cambiar de ruta). Bundle inicial −59%.

**I9 — Omnibox sin focus trap ni devolución de foco** ✅ Resuelto
`aria-modal="true"` sin contención de foco real ni devolución de foco al cerrar. Corregido con trampa de foco manual (Tab/Shift+Tab) y devolución de foco centralizada en la limpieza de un `useEffect`.

**I10 — Desactivar usuario sin confirmación** ✅ Resuelto
Única acción destructiva de la app sin confirmación explícita. Corregido reutilizando fielmente el patrón visual ya existente (Equipos/Documentos) y añadiendo el mecanismo de foco/teclado ya validado en I9.

**I11 — `docs/14-base-de-datos.md`/`docs/15-api-design.md` desactualizados** ✅ Resuelto
Auditoría columna por columna y ruta por ruta contra el código real. Corregidos nombres de columna incorrectos, una tabla completa ausente (`reportes_generados`), dos endpoints de auth documentados que nunca existieron, una sección de Dashboard completa ausente, y afirmaciones falsas sobre restricciones de base de datos que no existían.

**I12 — Cobertura de tests desigual** ✅ Resuelto
Cobertura dirigida a casos de error, condiciones límite y rutas de recuperación en `mantenimiento_service.py` (76%→99%), `mantenimientos/presentation/router.py` (81%→100%), `worker/main.py` (78%→90%) y `qr/presentation/router.py` (83%→96%). Este trabajo llevó al descubrimiento de C6 (ver sección 6).

### 5.3 Importantes pendientes (I1-I7) — fuera del alcance de esta ronda

| ID | Hallazgo |
|---|---|
| I1 | Presigned URL de subida sin límite de tamaño/tipo real a nivel de infraestructura |
| I2 | Inconsistencia `datetime.utcnow()` (naive) vs `datetime.now(UTC)` (aware) |
| I3 | Tests de aislamiento multi-tenant faltantes (Mantenimientos, QR) |
| I4 | ~20 índices FK faltantes |
| I5 | N+1 sin memoizar en `calendario_service._eventos_mantenimiento` |
| I6 | Worker: 4 fases del ciclo en un único `try/except` |
| I7 | `backend` sin `restart:` en `docker-compose.yml` |

---

## 6. Hallazgos descubiertos durante la ejecución

A diferencia de la sección 5 (hallazgos que ya estaban en el informe original del 2026-07-31), estos dos aparecieron **mientras se corregían otros hallazgos** — ninguno de los 3 agentes de auditoría original los había detectado. Se documentan por separado a propósito, para que quede claro qué vino de la auditoría inicial y qué se descubrió después gracias al propio trabajo de corrección y prueba.

**C6 — Reportes válidos podían quedar marcados "fallido" sin razón real** ✅ Resuelto
Encontrado el 2026-08-04 al escribir una prueba de aislamiento para `_procesar_reportes_pendientes` durante I12: el mismo bug de fondo que C1 (falta de `set_tenant_context` al reiniciar cada iteración de un bucle tras un commit), en una función que C1 nunca tocó. Un reporte válido podía terminar marcado `fallido` con un error opaco solo por su posición en el lote. Reproducido de forma determinista, corregido con el mismo patrón exacto de C1, con aprobación explícita antes de tocar código (ver nota de proceso en `20-auditoria-2026-07-31.md`).

**I13 — `EquipoDetailPage` arrastra `recharts` en un chunk de 389 KB** 🆕 Pendiente
Encontrado al medir el impacto de I8 con `vite build` — no es un bug (nada se rompe), es un hallazgo de rendimiento: `CalibracionesSection` → `TendenciaCalibraciones.tsx` es el único punto del proyecto que importa `recharts`; cualquier usuario que abra una ficha de equipo descarga esos 389 KB aunque nunca despliegue el gráfico. Severidad menor — recomendado como candidato temprano de la siguiente fase (lazy-load del componente de gráfico, mismo patrón ya validado en I8).

---

## 7. Archivos modificados por cada intervención

| Hallazgo | Backend | Frontend | Documentación |
|---|---|---|---|
| C1 | `app/worker/main.py` | — | — |
| C2 | — | 8 componentes (`AlertasPage`, `NotificacionesBell`, `AlertsSummary`, `MantenimientosListPage`, `UsuariosListPage`, `AuditoriaPage`, `CriticosPage`, `DocumentosPage`) | — |
| C3 | `alembic/versions/0016_check_constraints_estados.py` (nuevo), `adjuntos/domain/entities.py` | — | — |
| C4 | — | — | `13-arquitectura.md`, `18-sprints.md` |
| C5 | `core/config.py`, `main.py`, `auth/presentation/router.py`, `.env.example`, `tests/conftest.py` | — | — |
| C6 | `app/worker/main.py` | — | — |
| I8 | — | `app/App.tsx`, `app/AppShell.tsx`, `app/RouteFallback.tsx` (nuevo) | — |
| I9 | — | `features/busqueda/components/Omnibox.tsx` | — |
| I10 | — | `features/usuarios/components/PanelUsuario.tsx` | — |
| I11 | — | — | `14-base-de-datos.md`, `15-api-design.md` |
| I12 | `app/worker/main.py` (vía C6) | — | — |

## 8. Pruebas añadidas por cada hallazgo

| Hallazgo | Pruebas nuevas | Archivo(s) |
|---|---|---|
| C1 | 1 | `test_worker_notificaciones.py` (nuevo) |
| C2 | 16 | 8 archivos de test nuevos, uno por componente |
| C3 | 13 | `test_check_constraints_estados.py` (nuevo) |
| C4 | 0 | cambio documental puro |
| C5 | 8 | `test_rate_limit_auth.py` + `test_proxy_headers.py` (nuevos) |
| C6 | (incluido en I12) | `test_worker_recuperacion_sprint29.py` |
| I8 | 0 | refactor puro, verificado contra las 88 pruebas ya existentes |
| I9 | 6 | `Omnibox.test.tsx` (ampliado 7→13) |
| I10 | 9 | `PanelUsuario.test.tsx` (nuevo) |
| I11 | 0 | cambio documental puro |
| I12 | 22 | `test_mantenimientos_errores_sprint29.py` (18), `test_worker_recuperacion_sprint29.py` (3), `test_qr_flow.py` (+1) |
| **Total backend** | **44** | 274 → 318 |
| **Total frontend** | **31** | 72 → 103 |

---

## 9. Métricas comparativas (antes / después)

### Backend

| Métrica | Antes de Fase 0 | Después de Fase 0 (C1-C5) | Después de Fase 1 (I8-I12) |
|---|---|---|---|
| mypy | 0 errores (182 archivos) | 0 errores | 0 errores |
| ruff | 33 `E501` preexistentes (no relacionados) | 33 (sin cambio) | 33 (sin cambio) |
| pytest | 274/274 | 296/296 | **318/318** |
| Cobertura total | *no medida* | *no medida* | 93%→**95%** (única medición del periodo, tomada en I12) |
| Build | N/A — sin paso de build propio; validado vía mypy/ruff/pytest en cada corrección | | |

### Frontend

| Métrica | Antes de Fase 0 | Después de C2 | Después de I9 | Después de I10 |
|---|---|---|---|---|
| tsc | 0 errores | 0 errores | 0 errores | 0 errores |
| eslint | 4 warnings preexistentes (no relacionados), 0 errores | igual | igual | igual |
| vitest | 72/72 | 88/88 | 94/94 | **103/103** |
| `vite build` | exitoso | exitoso | exitoso | exitoso |

### Bundle inicial (I8 — único hallazgo con impacto de bundle)

| | Antes | Después | Cambio |
|---|---|---|---|
| Chunks JS | 1 | 52 | — |
| JS inicial (crudo) | 1.127,42 kB | 462,90 kB | **−59%** |
| JS inicial (gzip) | 326,30 kB | 146,76 kB | **−55%** |
| Advertencia de chunk > 500 kB | Sí | No | — |

---

## 10. Decisiones de arquitectura tomadas durante esta auditoría

- **No implementar Nginx/TLS todavía (C4).** Se decidió documentar honestamente que esa capa no existe hoy, en vez de construirla como parte de una corrección de documentación. Queda en `13-arquitectura.md` sección 11 ("Arquitectura futura") como plan explícito, no como código pendiente de esta fase.
- **Code-splitting por ruta con `React.lazy`/`Suspense` de doble capa (I8).** Un límite externo para rutas sin navegación (login, QR público) y uno interno dentro del shell autenticado, para que la barra lateral y la navbar nunca desaparezcan al cambiar de pantalla — decisión de UX tomada junto con la de rendimiento.
- **Rate limiting configurable por variable de entorno, no hardcodeado (C5).** `Settings.rate_limit_login`/`rate_limit_refresh` en vez de constantes en el código, con `ProxyHeadersMiddleware` + lista de IPs de confianza preparada para un reverse proxy futuro sin abrir una vía de spoofing de IP mientras tanto.
- **Separar "arquitectura actual" de "arquitectura futura" en la documentación (C4, I11).** Toda afirmación sobre infraestructura o esquema que no fuera verificable línea por línea contra el código real se movió a una sección explícita de roadmap, en vez de dejarla mezclada con lo que sí existe.
- **Reutilizar patrones visuales existentes en vez de crear nuevos (I9, I10).** La trampa de foco/devolución de foco de I9 (Omnibox) se reutilizó tal cual en I10 (confirmación de desactivar usuario) en vez de diseñar un mecanismo distinto — mismo criterio para el propio `role="alertdialog"` de I10, tomado de Equipos/Documentos sin inventar un componente nuevo.

## 11. Decisiones de alcance

Durante esta auditoría se decidió conscientemente **no** hacer lo siguiente, para mantener cada corrección acotada a un solo hallazgo y evitar mezclar cambios no relacionados:

- No corregir los 33 errores `ruff` `E501` preexistentes en archivos de test no relacionados con ningún hallazgo.
- No optimizar el chunk de `recharts` durante I8 — se midió, se registró como I13, y se dejó para la siguiente fase en vez de expandir el alcance de I8 sobre la marcha.
- No modificar `docs/16-seguridad.md` durante C4, pese a tener el mismo patrón de afirmación desactualizada sobre HTTPS/Nginx — C4 se acotó estrictamente a `13-arquitectura.md`.
- No implementar infraestructura futura (Nginx, TLS, `docker-compose.prod.yml`, balanceador de carga) — se documentó que no existe, no se construyó como parte de ninguna corrección de esta fase.
- No agregar el `CHECK` de `laboratorios.estado` durante C3, al no haber sido detectado por la auditoría original — se registró como hallazgo nuevo para la siguiente fase en vez de ampliar el alcance de C3 retroactivamente.
- No extraer un componente `ConfirmDialog` compartido durante I10, pese a que ya era la tercera copia del mismo patrón — quedó registrado como mejora recomendada en vez de convertir I10 en una tarea de refactor.
- No aplicar el mecanismo de foco/teclado de I10 a las copias existentes en `EquipoDetailPage`/`DocumentoDetailPage` — I10 se acotó al flujo de desactivar usuario.
- No corregir el formato de respuesta 429 inconsistente (`slowapi` vs. el resto de la API) durante C5 — quedó documentado como riesgo conocido, no como parte de la corrección.
- No agregar `pytest-asyncio` ni un cliente WebSocket de prueba para cubrir `ws_gateway.py`/`websocket_router.py` durante I12 — se consideró un cambio de infraestructura de testing, no de cobertura dentro de lo ya soportado.
- No restringir `logs_auditoria.entidad_tipo` con un `CHECK` durante C3 — es deliberadamente un campo abierto para que cualquier módulo futuro pueda registrar auditoría sin requerir una migración de esquema.

## 12. Matriz de riesgo residual

Combina los riesgos que quedaron de lo ya corregido (formato 429, `laboratorios.estado`, `docs/16`) con los hallazgos pendientes de la auditoría original (I1-I7, R1-R5) y lo descubierto en el camino (I13). Impacto/Probabilidad/Prioridad son una evaluación propia al cierre de esta fase, no parte del informe original — sirven para ordenar la sección 14 (recomendaciones).

| ID | Riesgo | Impacto | Probabilidad | Prioridad |
|---|---|---|---|---|
| I1 | Presigned URL de subida sin límite real de tamaño/tipo | Alto | Media | **Alta** |
| I3 | Sin tests de aislamiento multi-tenant (Mantenimientos, QR) | Alto | Baja | **Alta** |
| I2 | `datetime` naive/aware inconsistente (ya causó un bug una vez) | Medio | Media | Media |
| I6 | Worker: 4 fases del ciclo en un único `try/except` | Medio | Baja | Media |
| I7 | `backend` sin `restart:` en `docker-compose.yml` | Medio | Baja | Media |
| `docs/16-seguridad.md:35` | Mismo patrón de doc desactualizada que C4, no corregido | Alto | Baja | Media |
| R3 | Worker sin `FOR UPDATE SKIP LOCKED` (solo si se escala) | Alto | Baja | Media |
| I4 | ~20 índices FK faltantes | Bajo | Alta (crece con el volumen) | Media |
| I5 | N+1 sin memoizar en `calendario_service` | Bajo | Media | Baja |
| I13 | Chunk de 389 KB en `EquipoDetailPage` por `recharts` | Bajo | Alta | Baja |
| R1 | Migraciones concurrentes sin advisory lock (solo si se escala) | Alto | Baja | Baja |
| R2 | Rate limiting en memoria no compartido entre réplicas (solo si se escala) | Medio | Baja | Media |
| R4 | Sin límites de recursos en `docker-compose.yml` | Medio | Baja | Baja |
| R5 | Autodescripción de `ws_gateway.py` a verificar con múltiples réplicas | Bajo | Baja | Baja |
| — | Formato 429 inconsistente entre `slowapi` y el resto de la API | Bajo | Alta | Baja |
| `laboratorios.estado` | Sin `CHECK` (solo 2 valores en uso hoy) | Bajo | Baja | Baja |
| — | 33 errores `ruff` `E501` preexistentes, no relacionados | Bajo | Baja | Baja |

## 13. Deuda técnica pendiente

### Mejoras recomendadas (M1-M11 del informe original)
1. `IntegrityError` no manejado explícitamente en el backend.
2. Pool de conexiones de SQLAlchemy sin tuning explícito.
3. `GET /auditoria` y `GET /usuarios` sin paginación real (límite fijo en su lugar).
4. Dashboard con múltiples `listar_todos()` (full scan del tenant) en cada carga.
5. Token de WebSocket viaja como parámetro de query (limitación conocida del navegador).
6. `RecuperarPasswordRequest` — schema muerto, nunca conectado a un router.
7. `docker-entrypoint.sh` lanza Uvicorn con `--reload` y sin `--workers`.
8. Duplicación del bloque "subir foto con preview" ×4 en el frontend.
9. `AlertasSection` (Configuración) sin `aria-invalid`/`aria-describedby`.
10. `VistaMes` (Calendario) recalcula el filtrado de eventos sin memoizar.
11. 6 hooks de frontend exportados sin ningún consumidor.

**Encontradas durante Fase 1, adicionales al M1-M11 original** (no renumeradas para no romper la referencia a "M1-M11"):
- Extraer un componente `ConfirmDialog` compartido — hay 3 copias casi idénticas del mismo patrón tras I10 (Equipos, Documentos, Usuarios).
- Aplicar la trampa de foco/devolución de foco de I10 a las copias de Equipos/Documentos.

### Mejoras opcionales (O1-O9)
`ESTADOS_OPERATIVOS_VALIDOS` re-export sin uso · logging sin `laboratorio_id` · 422 genérico para todo `ErrorDeDominio` · comentario impreciso en migración 0015 · `docs/14` sobre-especifica `ON DELETE RESTRICT` · `<textarea>` nativo en vez del componente compartido · subidas sin `AbortController` · `ThemeProvider` sin listener en caliente de `prefers-color-scheme` · i18n no implementado.

### Riesgos futuros de escalabilidad (R1-R5) — no urgentes con la carga actual
Ver matriz de la sección 12 para impacto/probabilidad/prioridad de cada uno.

## 14. Lecciones de esta auditoría

- **Los 2 hallazgos no anticipados (C6, I13) aparecieron al escribir pruebas de aislamiento/recuperación y al medir el resultado de un cambio, no por inspección de código.** Refuerza priorizar pruebas de error/recuperación por encima de pruebas de camino feliz en la siguiente fase, tal como ya se pidió explícitamente para I12.
- El patrón de bug de C1/C6 (`SET LOCAL` de tenant muerto tras un `COMMIT`, sin refijar al iniciar la siguiente iteración de un bucle) es específico de este proyecto y **puede repetirse en cualquier otro bucle del worker que no se haya revisado todavía** — vale la pena una revisión dirigida de `app/worker/main.py` completo bajo ese criterio específico, no solo de los dos casos ya encontrados.
- Cuando un hallazgo de documentación (I11) se corrige con el mismo rigor que uno de código (verificación línea por línea contra la fuente real), aparecen inconsistencias que ningún agente de auditoría por sí solo había detectado (2 referencias cruzadas propias corregidas durante la propia redacción de I11).

## 15. Recomendaciones priorizadas para la Fase 2

Ordenadas según la matriz de la sección 12:

1. **I1** (Alta) — cerrar la falta de límite real de tamaño/tipo en URLs prefirmadas de subida.
2. **I3** (Alta) — agregar `test_mantenimientos_isolation.py` y `test_qr_isolation.py`.
3. **Revisión dirigida de `app/worker/main.py`** buscando el mismo patrón de bug que C1/C6 en cualquier bucle restante no auditado.
4. **I2, I6, I7, `docs/16-seguridad.md:35`, R3** (Media) — según disponibilidad, ninguno bloqueante hoy.
5. **I13** — lazy-load de `TendenciaCalibraciones`/`recharts` dentro de `CalibracionesSection` (mismo patrón ya validado en I8, bajo riesgo, prioridad baja pero barata de resolver).
6. **I9/I10, extraer `ConfirmDialog` compartido** — ahora hay 3 copias del mismo patrón; el costo de extraerlo ya es menor que seguir manteniendo 3 copias.
7. **I4, I5** (Media/Baja) — según disponibilidad.
8. Resto de M1-M11 y O1-O9 según disponibilidad.
9. **R1, R2, R4, R5** — solo si se planea escalar horizontalmente antes de esa fase.

## 16. Roadmap propuesto — M1-M11

Agrupado por tipo de esfuerzo, no por orden de aparición en el informe original:

**Backend — correctitud y datos**
- M1. Manejo explícito de `IntegrityError`.
- M2. Tuning explícito del pool de SQLAlchemy.
- M6. Eliminar o conectar `RecuperarPasswordRequest` (decidir si se construye el flujo de autoservicio o se retira el schema muerto).

**Backend — consistencia de API**
- M3. Paginación real en `GET /auditoria` y `GET /usuarios`.
- M4. Reducir los `listar_todos()` del Dashboard (full scan en cada carga).
- M5. Revisar alternativas al token de WebSocket en query param.

**Infraestructura**
- M7. `docker-entrypoint.sh`: quitar `--reload`, agregar `--workers` explícito para un entorno de producción real (cuando exista, ver `13-arquitectura.md` sección 11).

**Frontend — duplicación y accesibilidad**
- M8. Extraer el componente compartido de "subir foto con preview" (resuelve duplicación ×4 y el leak de `URL.createObjectURL` de paso).
- M9. `aria-invalid`/`aria-describedby` en `AlertasSection`.
- M10. Memoizar el filtrado de `VistaMes`.
- M11. Limpiar los 6 hooks de frontend sin consumidor (confirmar primero con producto si `useEvidencias` es un gap de UI real, no solo código muerto).

**Duración estimada:** cada ítem es acotado (1 archivo o un grupo pequeño de archivos relacionados) — se recomienda mantener el mismo criterio de esta fase: un hallazgo a la vez, con su propia verificación completa (mypy/ruff/pytest o tsc/eslint/vitest/build según corresponda) y aprobación antes de continuar al siguiente.

## 17. Estado final consolidado

| ID | Hallazgo | Origen | Estado |
|---|---|---|---|
| C1 | Outbox de notificaciones bloqueable | Auditoría original | ✅ Resuelto |
| C2 | Error de red mostrado como "sin datos" | Auditoría original | ✅ Resuelto |
| C3 | CHECK constraints faltantes | Auditoría original | ✅ Resuelto |
| C4 | Documentación de infraestructura ficticia | Auditoría original | ✅ Resuelto |
| C5 | Sin rate limiting en `/login`/`/refresh` | Auditoría original | ✅ Resuelto |
| C6 | Reportes válidos marcados "fallido" por bug de tenant | Descubierto en ejecución | ✅ Resuelto |
| I8 | Sin code-splitting de rutas | Auditoría original | ✅ Resuelto |
| I9 | Omnibox sin focus trap / devolución de foco | Auditoría original | ✅ Resuelto |
| I10 | Desactivar usuario sin confirmación | Auditoría original | ✅ Resuelto |
| I11 | Docs de BD/API desactualizadas | Auditoría original | ✅ Resuelto |
| I12 | Cobertura de tests desigual | Auditoría original | ✅ Resuelto |
| I13 | `EquipoDetailPage` — chunk de 389 KB por `recharts` | Descubierto en ejecución | 🆕 Pendiente |
| I1-I7 | Importantes restantes | Auditoría original | ⏳ Pendientes |
| M1-M11 | Mejoras recomendadas (+2 encontradas en el camino) | Auditoría original + descubiertas | ⏳ Pendientes |
| O1-O9 | Mejoras opcionales | Auditoría original | ⏳ Pendientes |
| R1-R5 | Riesgos futuros de escalabilidad | Auditoría original | 📋 Documentados |

**Fase 0: 6/6 resueltos (5 originales + C6). Fase 1: 5/6 resueltos (I13 pendiente, severidad menor).**

---

## 18. Conclusión

Tras la finalización de las fases 0 y 1, el proyecto se encuentra en un estado significativamente más robusto que al inicio de la auditoría. Se corrigieron todos los hallazgos críticos identificados inicialmente —más uno adicional descubierto durante la propia ejecución (C6)— y cinco de los seis hallazgos importantes abordados en esta etapa, manteniendo estabilidad funcional y sin introducir regresiones observadas en las pruebas ejecutadas. Permanecen pendientes mejoras relacionadas principalmente con rendimiento, escalabilidad y deuda técnica, cuya prioridad se detalla en la matriz de riesgo (sección 12) y el roadmap propuesto (sección 16).

## 19. Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-08-04 | Cierre de Fase 0 y Fase 1 — versión original entregada para revisión. |
| 1.1 | 2026-08-04 | Incorporados ajustes de revisión: separación de hallazgos originales vs. descubiertos durante la ejecución (sección 6), matriz de riesgo residual con impacto/probabilidad/prioridad (sección 12), métricas globales (sección 2), conclusión ejecutiva (sección 18), decisiones de arquitectura (sección 10) y de alcance (sección 11), este historial de versiones. |

---

*Este informe consolida `20-auditoria-2026-07-31.md` (registro vivo con el detalle completo de cada corrección) en un documento final para revisión. Ninguna corrección de código se realizó como parte de la preparación de este informe ni de su revisión.*
