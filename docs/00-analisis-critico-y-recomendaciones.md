# 00 — Análisis Crítico y Recomendaciones del Arquitecto Principal

**Documento:** Blueprint LABSYNC PRO ENTERPRISE
**Rol:** Chief Software Architect
**Estado:** Para revisión y aprobación del Product Owner
**Precede a:** todos los demás documentos de la Fase 1

---

## 1. Propósito de este documento

Antes de diseñar una sola pantalla o tabla, este documento evalúa el pedido original con ojo crítico: qué es sólido, qué es riesgoso, qué está sobredimensionado para el punto en el que está el producto hoy, y qué falta. Las decisiones que aquí se toman (multi-tenancy, monolito modular, RBAC granular, almacenamiento, auditoría) son vinculantes para el resto de la documentación — todos los documentos 01-19 son consistentes con lo que se decide aquí.

Este documento también dice explícitamente **qué NO se recomienda hacer todavía**, aunque el pedido original lo mencione (Kubernetes, microservicios, app móvil nativa, IA). No porque no tengan valor, sino porque construirlos antes de tener carga real que los justifique es la causa más común de que un proyecto Enterprise se hunda en complejidad accidental antes de tener un solo cliente pagando.

---

## 2. Punto de partida real (no asumido)

El proyecto existente en este repositorio es una página de login estática (HTML/CSS/JS, sin build step, animaciones vía Motion CDN) construida y ya auditada en accesibilidad. **No existe todavía ningún backend, base de datos, ni frontend en React.** Esto importa para el roadmap: la Fase 1 documental no tiene código previo del cual partir salvo las decisiones de marca visual (paleta verde institucional, tipografía) ya validadas en el login, que se preservan como punto de partida del Design System (ver `11-design-system.md`) en lugar de reinventarse desde cero.

---

## 3. Evaluación por dimensión

### 3.1 Alcance

**Hallazgo:** el pedido combina, en una sola fase de diseño, un ERP clínico-metrológico completo (14+ módulos), una arquitectura SaaS multi-tenant internacional, seguridad de nivel bancario, y planificación Scrum completa. Cada uno de estos es, por sí solo, un proyecto de varios meses.

**Riesgo:** si los 19 documentos se escriben con el mismo nivel de detalle que un producto ya en producción, el blueprint se vuelve obsoleto antes de terminar de escribirse — la realidad de construcción siempre revela ajustes. Documentación "perfecta" antes de código real es un antipatrón conocido (Big Design Up Front).

**Recomendación:** tratar este blueprint como **v1.0 — sujeto a revisión al final de cada sprint**, no como contrato inmutable. Se marca explícitamente en `19-checklist.md` y `18-sprints.md` un checkpoint de "revisión de arquitectura" al cierre de la primera vertical completa (Equipos), antes de replicar el patrón a los demás módulos.

### 3.2 Complejidad vs. madurez del producto

**Hallazgo:** el pedido original menciona Kubernetes, microservicios futuros, arquitectura multi-tenant para "miles de laboratorios", integración con Microsoft 365 y Google Workspace, IA, y app móvil offline-first — todo en la Fase 1, para un producto con cero clientes todavía.

**Riesgo real:** esto es sobre-ingeniería prematura. Diseñar para "miles de laboratorios" antes de tener el primero valida supuestos que probablemente cambiarán (qué se factura, qué se comparte entre tenants, qué reportes importan). El costo de mantenimiento de una arquitectura de microservicios/K8s sin el tráfico que la justifique es altísimo: cada servicio nuevo es un pipeline de CI/CD, un esquema de logging, un punto de fallo y un onboarding más para el equipo.

**Recomendación (decisión arquitectónica vinculante):**
- **Monolito modular** (no microservicios) como punto de partida — ver `13-arquitectura.md`. Los módulos se estructuran con límites de dominio claros (feature-based, Clean Architecture) precisamente para que *puedan* extraerse a servicios independientes el día que el tráfico lo justifique, sin reescribir lógica de negocio.
- **Docker Compose** para todos los entornos hasta que exista evidencia operativa (más de un nodo saturado, necesidad real de auto-scaling) que justifique Kubernetes. Migrar a K8s sin esa evidencia es costo puro sin beneficio medible.
- Multi-tenancy: sí, desde el día 1 (ver 3.4), porque cambiar de single-tenant a multi-tenant después es una migración de datos de altísimo riesgo. Pero **sin** la infraestructura de escalado horizontal que "miles de laboratorios" implicaría — esa capa se añade cuando el número real de tenants lo exija.
- Integraciones (Microsoft 365, Google Workspace, lectores de código de barras, IA) se documentan como **roadmap de fase 3+** (`17-roadmap.md`), no como requisito de v1. Se diseña la arquitectura de forma que agregarlas después sea barato (ver "Puertos y adaptadores" en `13-arquitectura.md`), pero no se construyen ahora.

### 3.3 Riesgos regulatorios (específicos del dominio)

**Hallazgo:** el producto se dirige a laboratorios clínicos bajo ISO 15189 e ISO/IEC 17025. Estas normas no son un adorno de marketing — imponen requisitos técnicos concretos que el pedido original menciona de forma superficial ("reportes para auditoría ISO 15189") pero que deben ser de primer orden en el modelo de datos:

- **Trazabilidad metrológica**: toda calibración debe poder demostrar su cadena de trazabilidad a un patrón nacional/internacional, no solo "fecha y resultado".
- **Incertidumbre de medición**: es un campo obligatorio en calibraciones metrológicas serias, no opcional (el pedido original ya lo incluye — se preserva y se refuerza).
- **Integridad de registros**: ISO 15189 exige que los registros de calidad no puedan alterarse sin dejar rastro. Esto obliga a un **log de auditoría inmutable** (append-only, sin UPDATE/DELETE ni para administradores) — ver `15-base-de-datos.md` y `16-seguridad.md`.
- **Control de documentos obsoletos**: un documento vencido nunca debe poder mostrarse como vigente por accidente (regla de negocio explícita en `07-reglas-de-negocio.md`).

**Recomendación:** estos requisitos se promueven de "detalle de implementación" a **regla de negocio de primer nivel**, documentada explícitamente y no negociable en sprints de optimización.

### 3.4 Arquitectura de datos: multi-tenancy

**Hallazgo:** el pedido pide escalar "desde 1 laboratorio hasta miles". Existen tres estrategias clásicas: base de datos por tenant, esquema por tenant, o fila por tenant (columna `laboratorio_id` + Row Level Security de PostgreSQL).

**Análisis:**
| Estrategia | Aislamiento | Costo operativo a miles de tenants | Migraciones |
|---|---|---|---|
| DB por tenant | Máximo | Inviable (miles de bases de datos que mantener/migrar) | Debe replicarse por cada DB |
| Esquema por tenant | Alto | Difícil de escalar más allá de cientos | Igual, por esquema |
| Fila + RLS | Medio-alto (con RLS bien aplicado) | Bajo — una sola base de datos, migraciones únicas | Una sola migración |

**Recomendación (decisión vinculante):** **fila por tenant con Row Level Security de PostgreSQL** activado por defecto en todas las tablas con datos de laboratorio, aplicado a nivel de conexión (variable de sesión `app.current_tenant_id`) para que un bug de aplicación no pueda filtrar datos entre tenants aunque olvide el `WHERE`. Se documenta como no-negociable en `14-base-de-datos.md` y `16-seguridad.md`. Se deja como escotilla de escape documentada (no implementada en v1) la posibilidad de mover a un tenant grande a su propia base de datos si algún día lo requiere por contrato o compliance.

### 3.5 Seguridad

**Hallazgo:** el pedido pide JWT + Refresh Tokens, RBAC, CSRF, CORS, rate limiting — todo correcto, pero mezclado sin jerarquía de urgencia.

**Recomendación:** ver `16-seguridad.md` para el detalle completo. Los puntos que se **añaden** por criterio propio del arquitecto (no estaban explícitos en el pedido) porque son estándar en software médico/Enterprise serio:
- Rotación de refresh tokens con detección de reuso (token reuse detection) — mitiga robo de tokens.
- Política de bloqueo progresivo tras intentos fallidos de login (no solo "política de complejidad de contraseña").
- Cifrado en reposo de documentos sensibles en MinIO (SSE) además de HTTPS en tránsito.
- Separación de permisos "leer PII de usuario" vs "leer datos operativos" dentro del RBAC — un Técnico no debería poder exportar la base de usuarios aunque tenga acceso operativo.

### 3.6 Experiencia de usuario

**Hallazgo:** el pedido es ambicioso y coherente en UX (Linear/Stripe/Notion como referencia). Es alcanzable — el login ya construido demuestra el nivel de calidad esperado y sirve de ancla de estilo.

**Recomendación:** reutilizar el design system ya validado del login (paleta verde `#0F5132`, tipografía Fraunces/Inter) como base, **fusionándolo** con la paleta ampliada de estados (éxito/advertencia/error/información) pedida ahora para LabSync Pro — ver `11-design-system.md`. No se reinicia desde cero; se extiende.

### 3.7 Rendimiento y costo de mantenimiento

**Hallazgo:** WebSockets para todo el sistema de alertas es correcto para tiempo real, pero si se implementa mal (una conexión persistente por usuario sin gestión de reconexión/backpressure) es una fuente común de fugas de memoria en producción.

**Recomendación:** WebSockets para el centro de notificaciones y el dashboard en vivo, con **fallback a polling** si la conexión falla, y un servicio de notificaciones desacoplado vía patrón *outbox* (una tabla `notificaciones_pendientes` que un worker procesa) en lugar de disparar WebSocket/email directamente desde la transacción de negocio — así un fallo de email nunca revierte ni bloquea la operación real (ej. registrar una calibración).

### 3.8 Facilidad de evolución futura

**Recomendación (mejoras propuestas no solicitadas explícitamente, ver también `17-roadmap.md`):**
- **API pública versionada** (`/api/v1/...`) desde el día 1, aunque el primer consumidor sea el propio frontend — evita romper contratos cuando se abra a integraciones.
- **Internacionalización arquitectónica desde v1** (strings externalizados, formato de fecha/número por locale) aunque el idioma inicial sea únicamente español — reescribir esto después es costoso; prepararlo ahora es barato.
- **Exportación de datos del tenant** (derecho de portabilidad) como requisito no funcional — relevante tanto por buenas prácticas SaaS como por regulaciones de datos de salud.
- **Panel de "salud del sistema"** para el rol Administrador (uso de almacenamiento, usuarios activos, última sincronización) — mejora de valor percibido de bajo costo de construcción, aprovechando datos que ya existen.

---

## 4. Funcionalidades adicionales propuestas (no solicitadas explícitamente)

Documentadas aquí para decisión del Product Owner; se marcan en `17-roadmap.md` como Fase 3+ salvo que se apruebe adelantarlas:

1. **Verificaciones intermedias de equipos** entre calibraciones formales (requisito real de ISO 17025, distinto de mantenimiento).
2. **Firma electrónica simple en aprobación de documentos** (registro de quién aprobó, cuándo, con qué versión) — refuerza el control documental ya pedido.
3. **Exportación de "paquete de auditoría"**: un solo ZIP/PDF consolidado con todo lo que un auditor ISO pediría de un equipo (ficha, calibraciones, mantenimientos, documentos vigentes) — altísimo valor percibido, bajo costo si el modelo de datos ya está bien normalizado.
4. **Modo offline de solo lectura para escaneo QR** (cachear la última ficha conocida del equipo) — valioso en laboratorios con conectividad débil, mucho más barato que "offline-first completo".
5. **API pública + webhooks salientes** (ej. "calibración vencida" dispara un webhook) antes que integraciones nativas puntuales con M365/Google Workspace — un webhook genérico cubre más casos con menos mantenimiento propio.

---

## 5. Riesgos que quedan abiertos (para decisión explícita del Product Owner)

| Riesgo | Impacto si no se decide | Recomendación del arquitecto |
|---|---|---|
| Nivel de aislamiento de datos entre tenants (RLS vs. algo más fuerte) | Fuga de datos entre laboratorios clientes — catastrófico para un producto de salud | Aprobar RLS + tests automatizados de aislamiento como criterio de aceptación obligatorio, no opcional |
| Retención de logs de auditoría (¿para siempre? ¿7 años?) | Costo de almacenamiento vs. cumplimiento normativo | Definir política de retención por norma aplicable (se deja como pregunta abierta en `04-requerimientos-no-funcionales.md`) |
| ¿Quién es el "superadmin" entre tenants (soporte del proveedor SaaS)? | Sin un rol de plataforma bien acotado, cualquier ingeniero de soporte podría ver datos de cualquier laboratorio | Se define un rol `Superadmin Plataforma` separado de los roles de laboratorio, con acceso auditado y justificación obligatoria por ticket |

---

## 6. Conclusión del análisis

El producto es viable y el nivel de ambición es correcto para un SaaS Enterprise de salud — pero **la secuencia importa más que el alcance**. Se recomienda aprobar este documento antes de continuar, ya que las decisiones de la sección 3 (monolito modular, RLS multi-tenant, RBAC granular, outbox para notificaciones, sin Kubernetes en v1) son la base de la que dependen consistentemente los documentos `13` a `16`.

**Siguiente paso:** con este documento aprobado, se continúa con `01-vision-del-producto.md`.
