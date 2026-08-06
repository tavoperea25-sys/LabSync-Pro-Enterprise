# 19 — Checklist del Proyecto

Checklist de referencia, aplicable como gate en cada sprint (no solo al final del proyecto).

---

## Arquitectura
- [ ] Módulo nuevo respeta separación domain/application/infrastructure/presentation.
- [ ] Ninguna regla de negocio vive en un router/controller — solo en la capa de dominio/aplicación.
- [ ] El módulo podría, en teoría, extraerse a un servicio independiente sin tocar otros módulos.
- [ ] No se introdujo Kubernetes/microservicios sin evidencia operativa que lo justifique (ver `00-analisis-critico-y-recomendaciones.md`).

## Backend
- [ ] Endpoint nuevo documentado en `15-api-design.md` (o el documento vivo que lo reemplace) antes/junto con su implementación.
- [ ] Validación de entrada con Pydantic en el límite del endpoint.
- [ ] Permiso requerido declarado explícitamente, verificado en servidor.
- [ ] `laboratorio_id` derivado del JWT, nunca de un parámetro de la petición.
- [ ] Cobertura de pruebas ≥80% en dominio/servicios del módulo.

## Frontend
- [ ] Componente usa únicamente tokens de `11-design-system.md` (sin valores hardcodeados).
- [ ] Componente reutiliza la librería de `12-component-library.md` en lugar de reimplementar un primitivo existente.
- [ ] Vista probada en 375px, 768px, 1024px y 1440px sin scroll horizontal.
- [ ] Vista probada en modo claro y modo oscuro.
- [ ] Type-checking estricto sin `any` no justificado.

## UX
- [ ] Flujo validado contra el user flow correspondiente en `09-user-flows.md`.
- [ ] Estados de carga, vacío y error diseñados explícitamente (no solo el "happy path").
- [ ] Microinteracciones en el rango 150–300ms, con `prefers-reduced-motion` respetado.

## Testing
- [ ] Pruebas de aislamiento multi-tenant pasando para todo endpoint nuevo que toque una tabla con `laboratorio_id`.
- [ ] Pruebas end-to-end del flujo crítico del módulo (no solo pruebas unitarias aisladas).
- [ ] Regresión visual o funcional verificada contra el módulo previamente estable antes de merge.

## Seguridad
- [ ] Row Level Security activa y verificada para toda tabla nueva con datos de tenant.
- [ ] Ninguna contraseña, token o secreto aparece en logs.
- [ ] Rate limiting aplicado en endpoints públicos o sensibles a abuso (login, recuperación, incidencias QR).
- [ ] Registro en auditoría de toda creación/edición/eliminación relevante (RF-AUD-01).

## Accesibilidad (checklist heredado y aplicado del login ya auditado)
- [ ] Elemento nativo usado en lugar de ARIA cuando existe (`<button>`, `<a href>`, `<select>`).
- [ ] `:focus-visible` estilado, nunca `outline: none` sin reemplazo verificado.
- [ ] Cada control tiene nombre accesible (label visible o `aria-label` en íconos).
- [ ] Errores de formulario asociados vía `aria-describedby` + `aria-invalid`, sin `role="alert"` redundante en errores atados a un control (lección aplicada de la auditoría del login).
- [ ] Objetivos táctiles ≥24×24px (AA), ≥44×44px cuando el contexto es táctil.
- [ ] Contraste verificado ≥4.5:1 (texto normal) en ambos modos de tema.
- [ ] Navegación completa por teclado sin trampas de foco no intencionales.

## DevOps
- [ ] `docker compose up` levanta el entorno completo sin pasos manuales adicionales.
- [ ] CI en verde (lint, type-check, tests, build) antes de merge.
- [ ] Health check expuesto para todo servicio nuevo.
- [ ] Logs estructurados (JSON) con `trace_id` de correlación.

## Documentación
- [ ] Este blueprint actualizado si la implementación reveló un ajuste necesario (no se documenta silenciosamente algo distinto de lo implementado).
- [ ] README del repositorio refleja cómo levantar el entorno actual, no una versión desactualizada.

## Checklist de cierre de fase (aplicar al final de cada fase de `17-roadmap.md`)
- [ ] Demo funcional de punta a punta de los módulos de la fase.
- [ ] Checkpoint de arquitectura ejecutado (¿el patrón se sostiene? ¿hay que ajustar antes de replicarlo?).
- [ ] Riesgos abiertos de `00-analisis-critico-y-recomendaciones.md` revisados — ¿siguen abiertos, se resolvieron, o cambiaron de prioridad?
