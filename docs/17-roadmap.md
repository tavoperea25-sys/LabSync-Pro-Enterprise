# 17 — Roadmap

---

## Fase 1 — Documentación (Blueprint)
**Objetivo:** este mismo conjunto de 19 documentos, revisado y aprobado por el Product Owner.
**Duración estimada:** ya completada con esta entrega.
**Dependencias:** ninguna.
**Prioridad:** crítica — bloquea el inicio de cualquier código.

## Fase 2 — MVP (Fundación + primer módulo vertical completo)
**Objetivo:** demostrar el patrón arquitectónico de punta a punta con un módulo real, no solo scaffolding vacío.
**Alcance:**
- Autenticación completa (login, refresh, recuperación, RBAC básico).
- Multi-tenancy funcional con RLS verificado por pruebas automatizadas.
- Módulo Equipos completo (CRUD, QR, búsqueda, filtros, exportación).
- Módulo Documentos completo (upload, versionado, carpetas).
- Dashboard con los KPIs que ya son calculables con estos dos módulos.
- Migración del login existente al frontend React (reutilizando el design system ya validado, no reconstruyéndolo desde cero).
**Duración estimada:** 6-8 semanas con un equipo full-stack pequeño (2-3 personas).
**Dependencias:** Fase 1 aprobada.
**Prioridad:** crítica.
**Checkpoint de arquitectura:** al cerrar esta fase se revisa si el patrón (Clean Architecture por módulo, RLS, outbox) se sostiene bien en la práctica antes de replicarlo al resto de módulos — ver `00-analisis-critico-y-recomendaciones.md`, sección 3.1.

## Fase 3 — Ciclo de vida operativo
**Objetivo:** completar el ciclo de cumplimiento que es la razón de ser del producto.
**Alcance:**
- Módulo Calibraciones (semáforo, trazabilidad metrológica).
- Módulo Mantenimientos.
- Centro de Alertas y Notificaciones (outbox + WebSocket + fallback polling).
- Calendario Operacional.
- Verificaciones intermedias de equipos (mejora propuesta en `00-analisis-critico-y-recomendaciones.md`).
**Duración estimada:** 6 semanas.
**Dependencias:** Fase 2.
**Prioridad:** alta.

## Fase 4 — Gobernanza y evidencia de auditoría
**Objetivo:** que un laboratorio piloto pueda preparar una auditoría ISO 15189 real usando únicamente LabSync Pro.
**Alcance:**
- Auditoría y trazabilidad (bitácora completa, append-only).
- Búsqueda global (omnibox).
- Gestión de Usuarios y Permisos completa (RBAC granular en UI de administración).
- Reportes (incluido el "paquete de auditoría" consolidado).
- Firma electrónica simple en aprobación de documentos (mejora propuesta).
**Duración estimada:** 5 semanas.
**Dependencias:** Fase 3.
**Prioridad:** alta.

## Fase 5 — Pulido Enterprise y lanzamiento comercial v1
**Objetivo:** llevar el producto a estándar de venta a clientes reales.
**Alcance:**
- Modo claro/oscuro completo en todos los módulos.
- Accesibilidad WCAG 2.2 AA verificada en toda la plataforma (no solo en el login).
- Observabilidad (logs centralizados, health checks, alertas de infraestructura).
- Onboarding de nuevos laboratorios (proceso de alta de tenant, aunque sea gestionado manualmente en v1).
- Exportación de datos del tenant (portabilidad).
**Duración estimada:** 4 semanas.
**Dependencias:** Fase 4.
**Prioridad:** alta.

---

## Fase 6+ — Expansión (post-v1, explícitamente fuera del alcance actual)

Priorizada por valor/costo estimado, no por orden de mención en el pedido original:

| Iniciativa | Valor esperado | Costo relativo | Prioridad sugerida |
|---|---|---|---|
| API pública + webhooks salientes | Alto (habilita integraciones sin construirlas todas) | Medio | Alta |
| Exportación "paquete de auditoría" avanzada (ZIP multi-equipo) | Alto | Bajo | Alta |
| App móvil (o PWA instalable antes que nativa) | Medio-alto en campo | Medio | Media |
| Modo offline de solo lectura ampliado | Medio | Medio | Media |
| Integración con lectores de código de barras | Medio (nicho, valioso donde aplica) | Bajo | Media |
| Panel de "salud del sistema" para Administrador | Medio (percepción de calidad) | Bajo | Media |
| Integración Microsoft 365 / Google Workspace | Medio (depende del cliente) | Alto | Baja — evaluar por demanda real |
| Kubernetes / escalado horizontal avanzado | Alto, pero solo si hay evidencia operativa | Alto | Condicional — no calendarizada, se activa por umbral de carga |
| Arquitectura de microservicios | Bajo hasta que el monolito modular muestre límites reales | Muy alto | Condicional — no calendarizada |
| Inteligencia artificial (predicción de fallas, asistente) | Alto potencial, alta incertidumbre | Alto | Baja — requiere datos históricos que hoy no existen |
| Multi-idioma (activar i18n ya arquitectado) | Depende de mercado objetivo | Bajo (si se arquitectó desde v1) | Condicional a expansión geográfica |

**Nota del arquitecto:** las iniciativas marcadas "Condicional" se dejan deliberadamente sin fecha — comprometerse a un roadmap fijo para Kubernetes o microservicios sin evidencia de carga real sería repetir el error de sobre-ingeniería identificado en `00-analisis-critico-y-recomendaciones.md`.
