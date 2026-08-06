# 23 — Informe Final de Fase 2 (M1-M11)

**LabSync Pro Enterprise — cierre de la Fase 2, 2026-08-05**

Documento de cierre, estable y versionado — igual criterio que `21-informe-final-auditoria-v1.md` para Fase 0/1: síntesis final para archivo, no el registro incremental (ese es `20-auditoria-2026-07-31.md`, actualizado hallazgo por hallazgo durante el trabajo y ya reflejando el cierre de esta fase).

---

## 1. Resumen ejecutivo

Entre el 2026-08-04 y el 2026-08-05 se implementaron las 11 mejoras recomendadas (M1-M11) identificadas en la auditoría original del 2026-07-31, siguiendo la planificación aprobada en `22-planificacion-fase2.md` — una mejora a la vez, cada una con objetivo acotado, pruebas específicas, verificación completa (mypy/ruff/pytest o tsc/eslint/vitest/vite build según correspondiera) y aprobación explícita antes de continuar.

**Resultado medible:**
- **11/11 mejoras recomendadas resueltas**, sin ninguna regresión detectada en ningún paso.
- Backend: 318 → **350 pruebas** (+32), cobertura de `app/` sostenida en **95%** pese a añadir código sustancial (paginación real, manejo de `IntegrityError`, agregados del Dashboard, auth de WebSocket).
- Frontend: 103 → **121 pruebas** (+18), advertencias `eslint` preexistentes bajaron de 4 a 3 (efecto colateral de M10).
- Dashboard: **10 → 7 consultas SQL** (−30%) y **93.3 ms → 34.2 ms** (−63%) medido sobre un dataset representativo de 150 equipos — con resultado matemáticamente idéntico, verificado por comparación directa contra una réplica de la implementación anterior.
- **1 bug de producción real** encontrado y corregido durante la validación en vivo de M5 (no lo detectaron los tests automatizados) — ver sección 4.
- **2 correcciones al alcance de hallazgos previos**: M11 pasó de "6 hooks muertos" a "1 hook muerto + 6 funcionalidades de UI incompletas" (auditoría exhaustiva); confirmado que solo 3 de las "4" pantallas de M8 tenían el patrón duplicado.

## 2. Alcance de la Fase 2 y decisiones previas al trabajo

Antes de iniciar, se resolvieron 3 preguntas abiertas de la planificación (`22-planificacion-fase2.md` sección 6):
1. **`useEvidencias`/M11**: no era código muerto — funcionalidad de Mantenimientos a medio construir. Confirmado y ampliado: son 7 hooks sin consumidor, no 6, y solo 1 es código muerto real.
2. **M6**: se decidió eliminar `RecuperarPasswordRequest` como schema muerto, no construir un flujo de autoservicio de recuperación de contraseña.
3. **Alcance de Fase 2**: estrictamente M1-M11, sin intercalar I1/I3 pese a su prioridad "Alta" en la matriz de riesgo — quedan para una fase futura dedicada a los importantes pendientes.

**Orden de implementación aprobado y seguido:** M9 → M10 → M1 → M2 → M7 → M8 → M3 → M4 → M11 → M6 → M5.

## 3. Mejoras implementadas (M1-M11)

### M1 — Manejo explícito de `IntegrityError`
Handler global `@app.exception_handler(IntegrityError)` en `app/core/errors.py`, clasifica por código SQLSTATE de Postgres: `23505` (UNIQUE) → 409 `registro_duplicado`; `23503` (FOREIGN KEY) → 409 `referencia_invalida`; cualquier otra violación → 409 genérico con el detalle real en el log del servidor. Punto real sin proteger encontrado: `EquipoService.crear`/`actualizar` nunca validaban `categoria_id`/`area_id` antes de guardar.
**Archivos:** `app/core/errors.py`, `tests/test_integrity_error_handler.py` (nuevo, 5 tests).

### M2 — Tuning explícito del pool de SQLAlchemy
`pool_size`/`max_overflow`/`pool_timeout` quedan en los mismos valores por defecto de SQLAlchemy, ahora explícitos y justificados con la cuenta real (2 procesos × (5+10) + 1 conexión de `ws_gateway` = 31, muy por debajo del `max_connections` de Postgres). Único valor que cambió de verdad: `pool_recycle` de `-1` (nunca) a `1800` (30 min).
**Archivos:** `app/core/config.py`, `app/core/database.py`, `.env.example`, `tests/test_database_pool.py` (nuevo, 2 tests).

### M3 — Paginación real en `GET /auditoria` y `GET /usuarios`
Ambos endpoints pasaron de una lista plana con límite fijo a `{items, total, pagina, tamano_pagina}` (mismo patrón que Equipos). Se corrigió además una inestabilidad de ordenamiento que Equipos ya tenía sin desempate (`creado_en` no es única) — Auditoría y Usuarios sí quedaron con desempate por `id`. Sin modo de transición dual: no hay consumidores externos de esta API, así que backend y frontend se actualizaron atómicamente.
**Archivos:** `app/core/pagination.py` (nuevo), módulos `auditoria` y `auth` (ports/repositories/schemas/router), frontend `features/auditoria` y `features/usuarios` completos. **Tests:** 14 backend + 2 frontend.

### M4 — Optimización de consultas del Dashboard
Tres full scans identificados y reemplazados por agregados SQL: (1) `calibraciones.listar_criticos()` + `listar_proximas()` — llamaban por separado a la misma consulta interna, fusionadas en una sola; (2) `mantenimientos.listar_todos()` ×2 sin `LIMIT` → un `GROUP BY tipo`; (3) `documentos.listar_todos()` (hasta 5000 filas) → un `CASE`+`GROUP BY` que replica `estado_efectivo()` en SQL. Deliberadamente **no** se tocó `equipos_criticos()` (necesita filas reales, no un conteo; la tabla de equipos está acotada por inventario físico, no como los mantenimientos que no tenían límite alguno).
**Evidencia medida:** 10 → 7 consultas SQL, 93.3 ms → 34.2 ms (dataset de 150 equipos/120 calibraciones/250 documentos/300 mantenimientos), resultado idéntico verificado por comparación directa con la implementación anterior.
**Archivos:** `dashboard/application/dashboard_service.py`, `mantenimientos` y `documentos` (ports/repositories), `tests/test_dashboard_optimizacion_m4.py` (nuevo, 6 tests).

### M5 — Token de WebSocket fuera del query string
El token pasó de `?token=` a un subprotocolo del handshake (`Sec-WebSocket-Protocol`), invisible para logs de acceso estándar y para un futuro reverse proxy. Alternativas evaluadas y descartadas: ticket de un solo uso (exige un almacén con expiración que no tiene dónde vivir sin Redis, atado a un solo proceso), reusar la cookie del refresh token (mezclaría credenciales de vida larga y corta), migrar todo a cookies httpOnly (rediseño desproporcionado, abre superficie de CSRF nueva).
**Bug real encontrado en la validación en vivo** (no lo detectó `TestClient`): el servidor no confirmaba de vuelta el subprotocolo ofrecido, y el navegador trataba eso como conexión fallida aunque el backend la aceptara. Corregido (`ws.accept(subprotocol=...)`).
**Archivos:** `alertas/presentation/websocket_router.py`, `core/ws_gateway.py`, frontend `NotificacionesProvider.tsx`, `tests/test_websocket_notificaciones.py` (nuevo, 5 tests — este endpoint no tenía ninguno antes).

### M6 — Eliminación de `RecuperarPasswordRequest`
Schema Pydantic sin ningún router/servicio/test que lo usara — eliminado sin reemplazo, sin construir ningún flujo de recuperación de contraseña.
**Archivos:** `auth/presentation/schemas.py`.

### M7 — `docker-entrypoint.sh` listo para producción
Bifurcación por `ENTORNO`: `desarrollo` (default) mantiene `--reload`; `produccion` usa `--workers` (parametrizable vía `WORKERS_UVICORN`, default 4) sin `--reload`. No se construyó ningún manifiesto de despliegue nuevo — sigue sin existir un entorno de producción real (`docs/13-arquitectura.md` sección 11), solo se dejó el script listo para cuando exista.
**Archivos:** `backend/docker-entrypoint.sh`, `.env.example`, nota en `docs/13-arquitectura.md`. **Validación:** en vivo contra Docker real, ambos modos.

### M8 — Componente compartido `SubirFotoConPreview`
Centraliza el ciclo de vida de `URL.createObjectURL`/`revokeObjectURL` — antes triplicado y **sin ninguna llamada a `revokeObjectURL`** (fuga de memoria por cada foto subida en la sesión). Corrección al conteo original: son 3 pantallas con el patrón duplicado (Equipos, Perfil, Logo institucional), no 4.
**Archivos:** `shared/components/ui/subir-foto-con-preview.tsx` (nuevo), `EquipoFormPage.tsx`, `PerfilSection.tsx`, `LaboratorioSection.tsx`. **Tests:** 7 nuevos. **Validación:** en vivo, subida real en las 3 pantallas.

### M9 — Accesibilidad de `AlertasSection`
Los 4 campos de umbrales pasaron de un único mensaje de error compartido a `aria-invalid`/`aria-describedby` por campo, usando el soporte que el componente `Input` compartido ya tenía y nadie usaba.
**Archivos:** `features/configuracion/components/AlertasSection.tsx`. **Tests:** 1 nuevo + 1 actualizado.

### M10 — Memoización de `VistaMes`
El filtrado de eventos por celda (O(42 × eventos) en cada render) pasó a un agrupamiento por día memoizado con `useMemo`, con desempate por `id` añadido (Equipos, que ya paginaba, no lo tenía). Efecto colateral: extraer la lógica a `VistaMes.logic.ts` (necesario para no romper `react-refresh/only-export-components`) bajó las advertencias `eslint` preexistentes de 4 a 3.
**Archivos:** `VistaMes.tsx`, `VistaMes.logic.ts` (nuevo). **Tests:** 12 nuevos.

### M11 — Eliminación de `useCrearDocumento`
Único hook realmente muerto de los 7 identificados (ver sección 4). `SubidaDropzone.tsx` ya llamaba a `crearDocumento()` directo desde la API, sin pasar por el hook.
**Archivos:** `features/documentos/hooks/useDocumentos.ts`.

## 4. Hallazgos descubiertos durante la Fase 2

A diferencia de los M1-M11 (ya catalogados en la auditoría original), estos aparecieron durante la propia ejecución:

- **Corrección al alcance de M11** — la cifra "6 hooks sin consumidor" del informe original era incorrecta: son **7**. Investigación exhaustiva de los ~90 hooks exportados encontró que solo 1 (`useCrearDocumento`) es código muerto real; los otros 6 tienen backend y API completos pero ninguna pantalla los consume — apuntan a un área de Documentos (carpetas/etiquetas) y Mantenimientos (evidencias) a medio construir. Registrados como hallazgos nuevos para una fase futura de UI (ver `20-auditoria-2026-07-31.md` sección 3).
- **Bug de WebSocket en M5** — el servidor no confirmaba el subprotocolo negociado en el handshake, causando que conexiones que el backend aceptaba fueran tratadas como fallidas por el navegador. No lo detectó la suite automatizada (`TestClient` no reproduce esa exigencia del navegador real); solo la validación funcional en vivo lo encontró. Corregido en el mismo cambio.
- **`PermisoInsuficiente` (403) sin cobertura** — encontrado al medir la cobertura de `app/core/errors.py` durante M1 (quedó en 97%, no 100%, por esta única rama). Preexistente, no relacionado con M1 — no se corrigió, queda registrado.

## 5. Pruebas añadidas por hallazgo

| Hallazgo | Backend | Frontend |
|---|---|---|
| M1 | 5 | — |
| M2 | 2 | — |
| M3 | 14 | 2 |
| M4 | 6 | — |
| M5 | 5 | — |
| M6 | 0 | — |
| M7 | 0 (validado en vivo) | — |
| M8 | — | 7 |
| M9 | — | 1 (+1 actualizado) |
| M10 | — | 12 |
| M11 | 0 | 0 |
| **Total** | **32** | **18** |

## 6. Métricas comparativas (antes / después de la Fase 2)

### Backend

| Métrica | Antes de Fase 2 | Después de Fase 2 |
|---|---|---|
| mypy | 0 errores (182 archivos) | 0 errores (183 archivos — `app/core/pagination.py` nuevo) |
| ruff (`app` + `tests`) | 20 `E501` preexistentes, no relacionados | mismos 20, **0 nuevos** introducidos por la Fase 2 (verificado archivo por archivo en cada hallazgo) |
| pytest | 318/318 | **350/350** |
| Cobertura de `app/` | 95% (medición única, tomada en I12) | **95%** (sostenida pese a añadir paginación, agregados del Dashboard, manejo de `IntegrityError` y auth de WebSocket) |

### Frontend

| Métrica | Antes de Fase 2 | Después de Fase 2 |
|---|---|---|
| tsc | 0 errores | 0 errores |
| eslint | 4 warnings preexistentes, 0 errores | **3 warnings** (bajó por M10), 0 errores |
| vitest | 103/103 | **121/121** |
| `vite build` | exitoso | exitoso |

### Bundle y rendimiento

| | Antes | Después |
|---|---|---|
| JS inicial (`index.js`) | 463,50 kB / gzip 147,00 kB | 463,51 kB / gzip 147,02 kB (sin cambio — Fase 2 no incluyó más code-splitting, eso es I13) |
| `ConfiguracionPage` (chunk) | 24,83 kB | 22,90 kB (−8%, deduplicación de M8) |
| `EquipoFormPage` (chunk) | 8,56 kB | 7,47 kB (−13%, deduplicación de M8) |
| Dashboard `resumen()` — consultas SQL | 10 (dataset de 150 equipos) | **7** (−30%) |
| Dashboard `resumen()` — tiempo | 93,3 ms | **34,2 ms** (−63%) |

## 7. Decisiones de arquitectura tomadas en la Fase 2

- **Ningún modo de transición dual para cambios de contrato de API** (M3): backend y frontend se actualizan atómicamente en el mismo cambio porque no hay consumidores externos — mismo criterio ya usado en Fase 0/1.
- **Agregados SQL solo donde no duplican lógica de negocio ya centralizada** (M4): se optimizaron mantenimientos y documentos (predicados simples), pero se dejó intacto el camino de `equipos_criticos()` que depende de `semaforo()` — una regla de negocio que el propio módulo de Dashboard documenta como "vivir solo en un lugar".
- **Subprotocolo de WebSocket en vez de un mecanismo de credenciales nuevo** (M5): se prefirió reubicar el mismo token en un transporte distinto sobre construir infraestructura de tickets o migrar el esquema de autenticación completo.
- **`docker-entrypoint.sh` listo para producción sin construir producción** (M7): el script soporta el modo sin `--reload`/con `--workers`, pero no se creó ningún manifiesto de despliegue — se documentó explícitamente en `docs/13-arquitectura.md` que ese manifiesto sigue sin existir.

## 8. Decisiones de alcance

- No se intercalaron I1/I3 en la Fase 2 pese a su prioridad "Alta" en la matriz de riesgo — se mantuvo el alcance acordado (M1-M11 estricto).
- No se optimizó `equipos_criticos()` en M4 (necesita filas reales, no un agregado; tabla acotada por inventario físico).
- No se construyó un flujo de recuperación de contraseña en M6, ni se migró el esquema de autenticación completo en M5.
- No se tocó `EquipoRepository.listar_todos()`/`MantenimientoRepository.listar_todos()`/`DocumentoRepository.listar_todos()` en sí mismos en M4 — siguen usados intactos por exportación, reportes y calendario.
- No se implementaron las 6 funcionalidades de UI incompletas encontradas al corregir el alcance de M11 (carpetas/etiquetas de Documentos, evidencias de Mantenimientos) — quedan registradas para una fase futura.
- No se extrajo un componente `Paginacion` compartido pese a que el patrón de M3 ya se duplica 3 veces (Equipos, Auditoría, Usuarios) — no era parte del alcance de M3, queda como candidato para una limpieza futura si se repite una cuarta vez.

## 9. Estado actualizado de la deuda técnica

| Categoría | Estado |
|---|---|
| M1-M11 (mejoras recomendadas originales) | ✅ **11/11 resueltas** |
| `ConfirmDialog` compartido (Fase 1) | ⏳ Pendiente |
| Trampa de foco de I10 en Equipos/Documentos (Fase 1) | ⏳ Pendiente |
| `laboratorios.estado` sin `CHECK` (Fase 1) | ⏳ Pendiente |
| 6 hooks — UI incompleta de Documentos/Mantenimientos (Fase 2) | ⏳ Pendiente, nuevo |
| `PermisoInsuficiente` (403) sin test (Fase 2) | ⏳ Pendiente, nuevo |
| I1-I7 (importantes originales, sin tocar) | ⏳ Pendientes |
| I13 (chunk de `recharts`, 389 KB) | ⏳ Pendiente |
| O1-O9 (mejoras opcionales) | ⏳ Pendientes |
| R1-R5 (riesgos futuros de escalabilidad) | 📋 Documentados, no urgentes |
| `docs/16-seguridad.md:35` (mismo patrón que C4) | ⏳ Pendiente |
| 33 errores `ruff` `E501` preexistentes | ⏳ Pendiente, no urgente |

## 10. Recomendaciones priorizadas para la siguiente fase

Según la matriz de riesgo ya establecida en `21-informe-final-auditoria-v1.md` sección 12 (no repetida aquí):

1. **I1** (Alta) — límite real de tamaño/tipo en URLs prefirmadas de subida.
2. **I3** (Alta) — tests de aislamiento multi-tenant en Mantenimientos y QR.
3. **I13** — lazy-load de `recharts`/`TendenciaCalibraciones` (mismo patrón ya validado en I8, barato de resolver).
4. **I2, I6, I7, R3, `docs/16-seguridad.md:35`** (Media) — según disponibilidad.
5. **Las 6 funcionalidades de UI incompletas encontradas en M11** — decidir producto por producto si se construyen (carpetas/etiquetas de Documentos, evidencias de Mantenimientos) o si los hooks se eliminan también.
6. **`ConfirmDialog` compartido** — ya son 3 copias del mismo patrón desde I10.
7. **I4, I5** (Media/Baja) — según disponibilidad.
8. Resto de O1-O9 según disponibilidad.
9. **R1, R2, R4, R5** — solo si se planea escalar horizontalmente antes de esa fase.

## 11. Conclusión

La Fase 2 cierra con las 11 mejoras recomendadas de la auditoría original resueltas, cada una verificada de forma independiente y con evidencia real (no solo razonamiento) donde el hallazgo lo permitía — en particular M4 (rendimiento del Dashboard, medido con datos reales antes/después) y M5 (un bug real de interoperabilidad con el navegador que solo la validación en vivo pudo encontrar). El proyecto mantiene cobertura de pruebas estable pese a un crecimiento real de código, y dos correcciones de alcance (M8, M11) muestran que el proceso de verificación exhaustiva antes de actuar sigue encontrando imprecisiones en el informe original en vez de propagarlas. Queda pendiente una fase dedicada a los hallazgos importantes originales (I1-I7), el hallazgo de rendimiento I13, y las funcionalidades de UI incompletas descubiertas al corregir el alcance de M11.

## 12. Historial de versiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-08-05 | Cierre de Fase 2 (M1-M11) — primera versión. |

---

*Este informe consolida `20-auditoria-2026-07-31.md` (registro vivo, actualizado incrementalmente durante toda la Fase 2) en un documento final de cierre. No hay cambios de código pendientes de este documento — todos los descritos aquí ya fueron implementados, verificados y aprobados hallazgo por hallazgo antes de esta síntesis.*
