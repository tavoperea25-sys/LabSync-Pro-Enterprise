# 01 — Visión del Producto

## LABSYNC PRO ENTERPRISE
**Eslogan:** "Gestión inteligente para laboratorios modernos"

---

## 1. Problema que resuelve

Los laboratorios clínicos y de metrología que operan bajo ISO 15189 / ISO 17025 gestionan hoy, en la mayoría de los casos, su documentación de calidad, el historial de equipos y el calendario de calibraciones/mantenimientos en una combinación de hojas de Excel, carpetas compartidas y papel. Esto genera:

- **Vencimientos no detectados a tiempo** (calibraciones, documentos, mantenimientos) que ponen en riesgo la acreditación del laboratorio.
- **Trazabilidad frágil**: reconstruir el historial completo de un equipo para una auditoría toma horas o días de búsqueda manual entre archivos dispersos.
- **Cero visibilidad ejecutiva**: la dirección técnica no tiene un indicador único de "qué tan cerca estamos de perder la acreditación" en un momento dado.
- **Riesgo de error humano** en el seguimiento manual de fechas y estados, con consecuencias regulatorias y clínicas.

LabSync Pro centraliza equipos, documentos, calibraciones, mantenimientos y auditoría en una sola plataforma con alertas automáticas, de forma que ningún vencimiento crítico dependa de que alguien recuerde revisarlo en una hoja de cálculo.

---

## 2. Público objetivo

### Perfil primario
Laboratorios clínicos y de salud pública (públicos y privados) acreditados o en proceso de acreditación bajo ISO 15189, con entre 5 y 200 equipos biomédicos activos y un equipo de calidad/metrología de 1 a 10 personas.

### Perfil secundario
Laboratorios de metrología y calibración (ISO/IEC 17025), y — a mediano plazo, como expansión natural del mismo modelo de datos — hospitales y clínicas con departamentos de ingeniería biomédica que gestionan equipos fuera de un laboratorio clínico estricto.

### Roles de usuario dentro de cada organización cliente
Administrador, Director Técnico, Calidad, Metrología, Técnico y Consulta (ver detalle completo en `10-gestion-usuarios` dentro de `03-requerimientos-funcionales.md` y roles en `06-historias-de-usuario.md`).

---

## 3. Objetivos del producto

1. Eliminar el uso de hojas de cálculo y carpetas dispersas como sistema de registro de calidad.
2. Garantizar que ningún vencimiento crítico (calibración, documento, mantenimiento) pase inadvertido.
3. Reducir de días a minutos el tiempo de preparación de un laboratorio para una auditoría externa.
4. Dar a la Dirección Técnica un panel de cumplimiento en tiempo real, no un reporte trimestral reconstruido a mano.
5. Operar como SaaS multi-cliente desde el diseño inicial, para que un mismo despliegue pueda servir a múltiples laboratorios de forma aislada y segura.

---

## 4. Alcance (v1 — ver `17-roadmap.md` para fases posteriores)

- Autenticación y gestión de usuarios/roles (RBAC) por laboratorio.
- Gestión de equipos biomédicos con ficha técnica completa.
- Gestor documental con versionado, vigencia y control de aprobación.
- Módulo de calibraciones con cálculo automático de estado (semáforo) y trazabilidad metrológica.
- Módulo de mantenimientos (preventivo, correctivo, predictivo).
- Centro de alertas y notificaciones in-app (con outbox preparado para email/push).
- Calendario operacional unificado.
- Búsqueda global tipo omnibox.
- Auditoría y trazabilidad de toda acción del sistema.
- Reportes exportables (PDF/Excel/CSV), incluyendo reportes orientados a auditoría ISO 15189.
- Código QR por equipo con vista pública responsive de solo lectura.
- Modo claro/oscuro.
- Arquitectura multi-tenant (aislamiento por laboratorio vía Row Level Security).

---

## 5. Fuera de alcance (v1)

Explícitamente diferido a fases posteriores (ver `17-roadmap.md`), para evitar que la Fase 1 se disperse:

- Aplicación móvil nativa (iOS/Android) — v1 es web responsive, incluida la vista QR desde móvil.
- Modo offline-first completo (solo se contempla caché de solo lectura para la vista QR).
- Integraciones nativas con Microsoft 365 / Google Workspace.
- Inteligencia artificial (predicción de fallas, asistentes conversacionales).
- Arquitectura de microservicios y orquestación Kubernetes (se inicia como monolito modular en Docker Compose; ver `00-analisis-critico-y-recomendaciones.md` sección 3.2).
- Facturación/planes de suscripción self-service (v1 asume alta de tenant gestionada manualmente por el operador de la plataforma).
- MFA (se deja el modelo de datos preparado, pero no se implementa en v1 — ver `16-seguridad.md`).

---

## 6. Beneficios

- **Para el laboratorio**: reduce el riesgo de perder la acreditación por un vencimiento no detectado; reduce drásticamente el tiempo de preparación de auditorías.
- **Para la Dirección Técnica**: visibilidad ejecutiva en tiempo real del estado de cumplimiento.
- **Para Calidad**: control documental centralizado con historial de versiones a prueba de auditoría.
- **Para Metrología/Técnicos**: flujo de trabajo claro de calibraciones y mantenimientos, con recordatorios automáticos en lugar de seguimiento manual.
- **Para el operador de la plataforma (LabSync como negocio)**: modelo SaaS multi-tenant escalable a muchos laboratorios sobre una sola base de código y una sola base de datos.

---

## 7. Propuesta de valor

> "Todo el ciclo de vida de tus equipos, documentos y calibraciones, en un solo lugar que nunca olvida una fecha — con la trazabilidad que un auditor ISO 15189 va a pedirte."

---

## 8. Diferenciadores frente a otras soluciones

| Frente a... | Diferenciador de LabSync Pro |
|---|---|
| Hojas de Excel / Google Sheets | Alertas automáticas, RBAC real, auditoría inmutable, sin riesgo de "se borró una celda sin que nadie lo note". |
| Software de gestión documental genérico (SharePoint, Drive) | Modelo de datos nativo para calibraciones, metrología e ISO 15189 — no es documentación genérica reconvertida. |
| ERPs hospitalarios grandes y costosos | Enfocado y liviano: se implementa en semanas, no en meses, con una experiencia de usuario de nivel SaaS moderno (Linear/Stripe/Notion) en lugar de UI de ERP heredado de los 2000. |
| Sistemas de gestión de activos genéricos (no clínicos) | Trazabilidad metrológica, incertidumbre de medición y reportes de auditoría ISO 15189 nativos, no adaptados. |

---

## 9. Escalabilidad futura

El producto se diseña desde v1 como multi-tenant (ver `00-analisis-critico-y-recomendaciones.md` y `14-base-de-datos.md`), de forma que escalar de 1 a cientos de laboratorios sea una cuestión de capacidad de infraestructura, no de reescritura de arquitectura. Los límites de módulo (Clean Architecture, feature-based) se definen para que cualquier módulo de alto tráfico (ej. Documentos) pueda extraerse a un servicio independiente en el futuro sin romper el resto del sistema. El roadmap de expansión (integraciones, app móvil, IA, API pública) se detalla en `17-roadmap.md`.
