# LABSYNC PRO ENTERPRISE — Blueprint (Fase 1)

**"Gestión inteligente para laboratorios modernos"**

Este es el blueprint oficial de LabSync Pro Enterprise: la documentación base sobre la que se construirá toda la plataforma. Ningún código de la nueva plataforma se escribe hasta que este blueprint esté revisado y aprobado (ver `00-analisis-critico-y-recomendaciones.md`, que explica por qué y define las decisiones de arquitectura vinculantes para todo lo demás).

**Estado general:** ⏳ Pendiente de revisión y aprobación del Product Owner.

---

## Cómo leer este blueprint

1. Empieza por **`00`** — es el análisis crítico que fija las decisiones de las que dependen todos los demás documentos (monolito modular, multi-tenancy por RLS, sin Kubernetes en v1). Si algo en `13-19` te parece inconsistente con el pedido original, la razón está documentada ahí.
2. `01-07` definen **qué** se construye y **por qué**.
3. `08-12` definen **cómo se ve y se siente**.
4. `13-16` definen **cómo se construye técnicamente**.
5. `17-19` definen **cuándo y en qué orden**.

---

## Índice

| # | Documento | Contenido | Estado |
|---|---|---|---|
| 00 | [Análisis crítico y recomendaciones](00-analisis-critico-y-recomendaciones.md) | Evaluación de riesgos, decisiones de arquitectura vinculantes, mejoras propuestas | ⏳ Para revisión |
| 01 | [Visión del producto](01-vision-del-producto.md) | Problema, público, alcance, propuesta de valor | ⏳ Para revisión |
| 02 | [Objetivos](02-objetivos.md) | Objetivos generales, específicos y medibles por fase | ⏳ Para revisión |
| 03 | [Requerimientos funcionales](03-requerimientos-funcionales.md) | Los 14 módulos, campo a campo, con permisos y validaciones | ⏳ Para revisión |
| 04 | [Requerimientos no funcionales](04-requerimientos-no-funcionales.md) | Rendimiento, seguridad, escalabilidad, accesibilidad, etc. | ⏳ Para revisión |
| 05 | [Casos de uso](05-casos-de-uso.md) | Flujos representativos por rol, con errores y resultado esperado | ⏳ Para revisión |
| 06 | [Historias de usuario](06-historias-de-usuario.md) | Formato Agile con criterios de aceptación Given/When/Then | ⏳ Para revisión |
| 07 | [Reglas de negocio](07-reglas-de-negocio.md) | Reglas no negociables por módulo | ⏳ Para revisión |
| 08 | [Sitemap](08-sitemap.md) | Mapa de navegación completo con permisos por ruta | ⏳ Para revisión |
| 09 | [User flows](09-user-flows.md) | Flujos paso a paso, incluidos casos de error | ⏳ Para revisión |
| 10 | [Wireframes](10-wireframes.md) | Desktop/Tablet/Mobile de las pantallas principales | ⏳ Para revisión |
| 11 | [Design system](11-design-system.md) | Paleta, tipografía, tokens — extiende el login ya construido | ⏳ Para revisión |
| 12 | [Component library](12-component-library.md) | Catálogo de componentes reutilizables con accesibilidad | ⏳ Para revisión |
| 13 | [Arquitectura](13-arquitectura.md) | Monolito modular, multi-tenancy, patrones, infraestructura | ⏳ Para revisión |
| 14 | [Base de datos](14-base-de-datos.md) | ERD completo, RLS, índices, restricciones | ⏳ Para revisión |
| 15 | [API design](15-api-design.md) | Endpoints, contratos, versionado, errores | ⏳ Para revisión |
| 16 | [Seguridad](16-seguridad.md) | Auth, RBAC, aislamiento multi-tenant, protección de datos | ⏳ Para revisión |
| 17 | [Roadmap](17-roadmap.md) | Fases 1-5 + expansión futura priorizada | ⏳ Para revisión |
| 18 | [Sprints](18-sprints.md) | 12 sprints planificados con riesgos por sprint | ⏳ Para revisión |
| 19 | [Checklist](19-checklist.md) | Gates de calidad por sprint y por cierre de fase | ⏳ Para revisión |

---

## Decisiones clave que debes aprobar o cuestionar primero

Antes de aprobar todo el blueprint, estas son las decisiones de mayor impacto que un Chief Software Architect tomó por criterio propio y que merecen tu confirmación explícita (detalle completo en `00-analisis-critico-y-recomendaciones.md`):

1. **Monolito modular, no microservicios**, en v1 — con arquitectura preparada para dividirse después.
2. **Docker Compose, no Kubernetes**, hasta que haya evidencia operativa real que lo justifique.
3. **Multi-tenancy por fila + Row Level Security**, no base de datos ni esquema por cliente.
4. **RBAC granular (roles↔permisos en base de datos)**, no roles hardcodeados en código.
5. **Tipografía del producto: Inter + Plus Jakarta Sans**, distinta de la Fraunces usada solo en el panel de marca del login (que se conserva ahí, no se propaga al resto de la UI).
6. Varias funcionalidades del pedido original (Kubernetes, microservicios, M365/Google Workspace, IA, app móvil nativa) se **difieren deliberadamente** a fases posteriores — no se eliminan, se secuencian.

## Siguiente paso

Revisar y aprobar (o solicitar ajustes a) este blueprint, empezando por `00-analisis-critico-y-recomendaciones.md`. Solo al aprobarse se inicia la Fase 2 (`17-roadmap.md`) con la primera línea de código.
