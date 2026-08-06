# 22 — Planificación de la Fase 2 (M1-M11)

**Planificación aprobada (2026-08-04) — las 3 preguntas abiertas de la sección 6 quedaron resueltas antes de iniciar. Orden de implementación definitivo en la sección 5. No se ha modificado código de la aplicación para preparar este documento.**

Línea base: `21-informe-final-auditoria-v1.md` v1.1 (aprobado 2026-08-04, Fase 0 y Fase 1 cerradas). Proceso vigente para cada intervención de esta fase: un objetivo por iteración, alcance acotado, pruebas específicas del cambio, verificación completa (mypy/ruff/pytest o tsc/eslint/vitest/vite build según corresponda), documentación de cualquier decisión de arquitectura o de alcance, y aprobación explícita antes de continuar con la siguiente tarea.

---

## 1. Alcance de esta planificación

Cubre exclusivamente M1-M11 (mejoras recomendadas del informe original), tal como se solicitó. No incluye I1-I7 (importantes pendientes) ni O1-O9 ni R1-R5.

**Nota para tener en cuenta al aprobar el orden:** la matriz de riesgo del informe (`21-informe-final-auditoria-v1.md` sección 12) ubicó a I1 y I3 en prioridad "Alta" — por encima de cualquier M-item. Si se prefiere, esos dos podrían intercalarse al inicio de la Fase 2 en vez de esperar a una fase separada; se deja como decisión abierta y no se asume aquí, ya que el encargo fue planificar M1-M11 específicamente.

## 2. M1-M11 — impacto, esfuerzo, complejidad y riesgo

| ID | Descripción | Impacto | Esfuerzo | Complejidad | Riesgo de la intervención |
|---|---|---|---|---|---|
| M9 | `AlertasSection` sin `aria-invalid`/`aria-describedby` | Medio (accesibilidad, WCAG) | Bajo | Baja | Bajo |
| M10 | `VistaMes` sin memoizar el filtrado de eventos | Bajo-Medio (rendimiento con muchos eventos) | Bajo | Baja | Bajo |
| M7 | `docker-entrypoint.sh` con `--reload` y sin `--workers` | Medio (preparación operativa) | Bajo | Baja | Bajo |
| M1 | `IntegrityError` no manejado explícitamente | Medio-Alto (errores 500 en vez de 4xx claros) | Bajo-Medio | Media | Bajo |
| M11 | 1 hook realmente muerto (`useCrearDocumento`) — ver sección 6, cifra corregida de "6" a "7 hooks sin consumidor" tras verificación | Bajo (limpieza de 1 archivo) | Bajo | Baja | Bajo |
| M2 | Pool de SQLAlchemy sin tuning explícito | Medio (escalabilidad futura, no urgente hoy) | Bajo | Baja | Bajo-Medio (mala configuración puede agotar conexiones) |
| M8 | Duplicación ×4 de "subir foto con preview" | Medio (mantenibilidad, corrige leak de `URL.createObjectURL` de paso) | Medio | Media | Bajo-Medio (4 pantallas a re-verificar) |
| M3 | `GET /auditoria`/`GET /usuarios` sin paginación real | Medio-Alto (crece con el volumen de datos) | Medio | Media | Medio (cambio de contrato de API, requiere actualizar consumidores del frontend) |
| M4 | Dashboard con múltiples `listar_todos()` por carga | Alto (primera pantalla que ve cada usuario) | Medio-Alto | Alta | Medio (cambios de query, requiere verificar exactitud de métricas) |
| M6 | `RecuperarPasswordRequest` — schema muerto. **Decisión tomada:** se elimina (ver sección 6) | Bajo | Bajo | Baja | Bajo |
| M5 | Token de WebSocket como parámetro de query | Bajo-Medio (exposición en logs/referrer) | Medio-Alto | Alta | Medio (autenticación de WS es fácil de romper en silencio) |

**Nota M11 (resuelta — ver sección 6):** la verificación exhaustiva encontró 7 hooks sin consumidor, no 6. De esos 7, solo 1 (`useCrearDocumento`) es código muerto real — los otros 6 apuntan a funcionalidad de UI nunca conectada, con backend y API ya implementados. M11 en Fase 2 queda acotado a eliminar únicamente `useCrearDocumento`; los 6 restantes se registran como hallazgos nuevos en `20-auditoria-2026-07-31.md` (sección "Mejoras recomendadas — adicionales"), fuera del alcance de esta fase.

**Nota M6 (resuelta — ver sección 6):** se decidió eliminar `RecuperarPasswordRequest` como código muerto; no se construye un flujo de autoservicio de recuperación de contraseña en esta fase.

## 3. Dependencias entre tareas

- **M3 → M4 (secuencial, no bloqueante):** M3 introduce el patrón de paginación real que hoy no existe en el proyecto. Resolverlo primero da un patrón/utilitario ya probado para reutilizar en M4, en vez de que M4 tenga que inventar su propio criterio de paginación/agregación desde cero. No son estrictamente dependientes (M4 podría hacerse sin M3), pero hacerlos en ese orden reduce el esfuerzo combinado.
- **M11 → resuelto.** Ya no depende de una decisión pendiente: queda acotado a eliminar `useCrearDocumento` únicamente.
- **M6 → resuelto.** Se elimina el schema muerto; sin dependencias.
- **M8 y la extracción de `ConfirmDialog` (hallazgo adicional de Fase 1, no numerado M1-M11):** mismo tipo de tarea (extraer un componente compartido de un patrón duplicado). No son dependientes entre sí, pero se recomienda no intercalarlas en la misma iteración para no mezclar dos extracciones distintas en un solo cambio.
- El resto (M9, M10, M7, M1, M2, M5) son independientes entre sí y del resto de la lista.

## 4. Riesgos específicos por intervención

- **M1:** riesgo de capturar `IntegrityError` de forma demasiado genérica y ocultar el detalle real del conflicto (p. ej. mapear todo a un mensaje único en vez de distinguir violación de unicidad vs. FK). Mitigación: mapear por tipo de restricción violada, con un test por cada constraint relevante ya creado en C3 (`0016_check_constraints_estados.py` y los `UNIQUE` existentes).
- **M2:** riesgo de sub- o sobre-dimensionar el pool sin datos reales de carga. Mitigación: valores conservadores basados en el volumen actual (no proyectado), documentados con su justificación, no copiados de un ejemplo genérico.
- **M3:** riesgo de romper a cualquier consumidor del frontend que hoy asuma una lista completa sin paginar. Mitigación: mapear primero todos los usos de esos dos endpoints en el frontend antes de cambiar el contrato del backend, y actualizarlos en el mismo cambio (no dejar el frontend roto entre commits).
- **M4:** el de mayor riesgo de todos — cambiar las queries del Dashboard puede alterar sutilmente el valor mostrado de una métrica sin que ningún test lo detecte si las pruebas nuevas no cubren casos límite reales (tenant vacío, un solo registro, filtros combinados). Mitigación: escribir los tests de verificación de valores *antes* de tocar la query (mismo criterio ya aplicado en I12).
- **M5:** cualquier cambio de autenticación de WebSocket es fácil de romper en producción sin que un test unitario lo note, porque el navegador real tiene restricciones (no permite headers custom en el handshake de WS) que un test con un cliente de test puede no replicar fielmente. Mitigación: verificación manual en navegador real además de los tests automatizados, igual que se hizo con I9/I10.
- **M6 (si se decide construir el flujo):** abre una superficie de autenticación nueva (tokens de recuperación, expiración, envío de correo) — el riesgo más alto de seguridad de toda la lista M1-M11 si se opta por esa rama. Si se decide eliminar el schema muerto, el riesgo es mínimo.
- **M7, M8, M9, M10, M11 (salvo `useEvidencias`):** riesgo bajo en todos los casos — cambios acotados a un archivo o un patrón ya validado en la Fase 1.

## 5. Orden de implementación — aprobado

El usuario ajustó el orden propuesto originalmente. Este es el orden final aprobado (2026-08-04):

| # | Tarea | Justificación |
|---|---|---|
| 1 | M9 — `aria-invalid`/`aria-describedby` en `AlertasSection` | Menor esfuerzo y riesgo de toda la lista; cierra una brecha de accesibilidad real (WCAG 4.1.3) sin tocar lógica de negocio. |
| 2 | M10 — memoizar `VistaMes` | Cambio trivial (`useMemo`), sin riesgo, mejora medible de rendimiento en calendarios con muchos eventos. |
| 3 | M1 — manejo explícito de `IntegrityError` | Impacto medio-alto en robustez de la API con esfuerzo contenido; endurece el manejo de errores que M3/M4 también van a ejercitar. |
| 4 | M2 — tuning del pool de SQLAlchemy | Se adelanta respecto a la propuesta original: al ir justo después de M1 y antes de M7/M8, el pool queda ajustado antes de cualquier tarea de mayor carga de queries (M3, M4). |
| 5 | M7 — `docker-entrypoint.sh` sin `--reload`/con `--workers` | Bajo esfuerzo y riesgo; sienta una base más realista para un entorno de despliegue real (ver "Arquitectura futura", `13-arquitectura.md` sección 11), sin construir esa infraestructura todavía. |
| 6 | M8 — extraer "subir foto con preview" compartido | Esfuerzo medio acotado a frontend; se resuelve antes de las tareas de backend más grandes (M3, M4). |
| 7 | M3 — paginación real en `/auditoria` y `/usuarios` | Establece el patrón de paginación que M4 puede reutilizar. |
| 8 | M4 — optimizar queries del Dashboard | Mayor impacto y riesgo de la lista; se apoya en M1/M2 (errores y pool ya ajustados) y M3 (patrón de paginación/consulta ya probado). |
| 9 | M11 — eliminar `useCrearDocumento` | Se pospone respecto a la propuesta original, ahora que su alcance real está resuelto (sección 6): es una limpieza trivial de 1 hook, sin urgencia de hacerse temprano. |
| 10 | M6 — eliminar `RecuperarPasswordRequest` | Decisión ya resuelta (sección 6): eliminar schema muerto. Tarea trivial, se deja cerca del final por preferencia del usuario, no por complejidad pendiente. |
| 11 | M5 — token de WebSocket en query param | La de mayor complejidad y menor urgencia actual; última de la lista. |

**Adicionales de Fase 1 (no numerados M1-M11, mismo criterio de "un cambio a la vez"):** extraer `ConfirmDialog` compartido y aplicar el patrón de foco de I10 a `EquipoDetailPage`/`DocumentoDetailPage` — se recomienda intercalarlos cerca de M8 (misma naturaleza de tarea: extraer un patrón duplicado en el frontend) pero como iteraciones propias, no combinadas con M8 en un mismo cambio.

## 6. Preguntas abiertas — resueltas (2026-08-04)

### 6.1 M11 / hooks sin consumidor

**Investigación realizada** (no solo sobre `useEvidencias` — se auditaron los ~90 hooks exportados en `frontend/src/**/hooks/**`, comparando cada uno contra sus consumidores reales): la cifra del informe original ("6 hooks sin consumidor") era incorrecta — son **7**. De esos 7, solo **1 es código muerto real**; los otros 6 tienen backend y API ya implementados pero ninguna pantalla los consume, es decir, apuntan a funcionalidad de UI nunca terminada de conectar:

| Hook | Backend | Diagnóstico |
|---|---|---|
| `useCrearDocumento` (`useDocumentos.ts:77`) | `POST /documentos`, implementado | **Código muerto real.** `SubidaDropzone.tsx` llama a `crearDocumento()` directamente desde la API, sin pasar por este hook — el wrapper de React Query nunca se usa. Seguro de eliminar. |
| `useEvidencias` (`useMantenimientos.ts:33`) | `GET .../evidencias`, implementado | Funcionalidad faltante: se puede *subir* evidencia (`useAgregarEvidencia` sí está conectado en `MantenimientosSection.tsx`) pero no hay ninguna pantalla que *liste* lo ya subido. |
| `useDocumentosRecientes` (`useDocumentos.ts:17`) | `GET /documentos/recientes`, implementado | Funcionalidad faltante: no existe ningún widget de "documentos recientes" en Dashboard ni en Documentos. |
| `useEtiquetas` (`useDocumentos.ts:33`) | `GET /etiquetas`, implementado | Funcionalidad faltante: no hay filtro/autocompletado de etiquetas en `DocumentosPage`; el parámetro de filtro existe en la API pero ningún control lo usa. |
| `useCarpeta` (`useDocumentos.ts:44`) | `GET /carpetas/{id}`, implementado | Funcionalidad faltante: no hay panel de detalle de carpeta. |
| `useRenombrarCarpeta` (`useDocumentos.ts:197`) | `PATCH /carpetas/{id}`, implementado | Funcionalidad faltante: se puede crear una carpeta pero no renombrarla desde la UI. |
| `useEliminarCarpeta` (`useDocumentos.ts:205`) | `DELETE /carpetas/{id}`, implementado | Funcionalidad faltante: se puede crear una carpeta pero no eliminarla desde la UI. |

**Resolución:** M11, dentro de esta fase, queda acotado a eliminar únicamente `useCrearDocumento`. Los 6 restantes **no se implementan en Fase 2** — se registran como hallazgos nuevos en `20-auditoria-2026-07-31.md` para que no se pierdan, ya que en conjunto describen un área de Documentos con gestión de carpetas/etiquetas a medio construir (backend completo, frontend incompleto).

### 6.2 M6 — decisión de producto

**Resuelto:** se elimina `RecuperarPasswordRequest` como código muerto. No se construye un flujo de autoservicio de recuperación de contraseña en esta fase; el reset manual por administrador existente se mantiene como está.

### 6.3 Alcance de Fase 2

**Resuelto:** Fase 2 se mantiene estrictamente en M1-M11. I1 e I3 (prioridad "Alta" en la matriz de riesgo) no se intercalan — quedan para una fase futura dedicada a los importantes pendientes (I1-I7).

---

*Documento de planificación. No se ha modificado código del proyecto en su preparación. Pendiente de revisión y aprobación antes de iniciar la primera iteración de la Fase 2.*
