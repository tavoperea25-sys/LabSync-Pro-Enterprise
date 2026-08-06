# 04 — Requerimientos No Funcionales

Convención: `RNF-<categoría>-<número>`.

---

## 1. Rendimiento

| ID | Requisito |
|---|---|
| RNF-PERF-01 | El tiempo de respuesta del API para operaciones de lectura simples (GET por ID) debe ser ≤200ms en el percentil 95, bajo carga normal. |
| RNF-PERF-02 | Las vistas principales (Dashboard, listados) deben mostrar contenido significativo (LCP) en ≤1.5s en una conexión de banda ancha estándar. |
| RNF-PERF-03 | Las listas con más de 50 elementos deben usar paginación o virtualización — nunca renderizar el listado completo de una vez. |
| RNF-PERF-04 | Las exportaciones de reportes de gran volumen (>1000 registros) deben ejecutarse de forma asíncrona (job en background) con notificación de finalización, no de forma síncrona bloqueando la petición HTTP. |
| RNF-PERF-05 | Las imágenes (fotos de equipos, evidencias) deben servirse en formatos optimizados (WebP/AVIF) con carga diferida (lazy loading) fuera del viewport inicial. |

## 2. Seguridad

Ver detalle completo en `16-seguridad.md`. Resumen de requisitos no funcionales:

| ID | Requisito |
|---|---|
| RNF-SEC-01 | Toda comunicación cliente-servidor debe ocurrir exclusivamente sobre HTTPS/TLS 1.2+. |
| RNF-SEC-02 | Las contraseñas deben almacenarse con hash Argon2id (o bcrypt como alternativa aceptada), nunca en texto plano ni con hash reversible. |
| RNF-SEC-03 | El aislamiento de datos entre tenants debe garantizarse a nivel de base de datos (Row Level Security), no solo a nivel de aplicación. |
| RNF-SEC-04 | El sistema debe aplicar rate limiting por IP y por usuario en endpoints de autenticación. |
| RNF-SEC-05 | El sistema debe validar y sanear toda entrada de usuario en el backend, independientemente de la validación en el frontend. |
| RNF-SEC-06 | Los documentos almacenados deben cifrarse en reposo (SSE en MinIO). |

## 3. Escalabilidad

| ID | Requisito |
|---|---|
| RNF-ESC-01 | La arquitectura debe permitir agregar nuevos laboratorios (tenants) sin cambios de código ni migración manual de esquema. |
| RNF-ESC-02 | El backend debe ser stateless (sin sesión en memoria de proceso) para permitir múltiples réplicas detrás de un balanceador de carga. |
| RNF-ESC-03 | El almacenamiento de documentos debe soportar crecimiento horizontal (MinIO distribuido) sin migración de datos al escalar. |
| RNF-ESC-04 | Los módulos deben mantener límites de dominio claros (feature-based) que permitan extraer cualquiera a un servicio independiente sin reescritura de lógica de negocio. |

## 4. Disponibilidad

| ID | Requisito |
|---|---|
| RNF-DISP-01 | Disponibilidad objetivo de 99.5% mensual para el ambiente de producción (v1; se revisa al escalar a SLA contractual con clientes). |
| RNF-DISP-02 | El sistema debe degradar con gracia ante la caída de servicios no críticos (ej. si el servicio de notificaciones falla, la operación de negocio principal no debe fallar — ver patrón outbox en `13-arquitectura.md`). |
| RNF-DISP-03 | Deben existir backups automáticos diarios de la base de datos con retención mínima de 30 días, y backups del almacenamiento de documentos. |

## 5. Accesibilidad

| ID | Requisito |
|---|---|
| RNF-ACC-01 | Cumplimiento WCAG 2.2 nivel AA en la totalidad de la interfaz. |
| RNF-ACC-02 | Contraste mínimo 4.5:1 para texto normal y 3:1 para texto grande/elementos gráficos. |
| RNF-ACC-03 | Navegación completa por teclado en todos los flujos, incluidos componentes complejos (calendario, omnibox, tablas). |
| RNF-ACC-04 | Soporte de `prefers-reduced-motion` en toda animación no esencial. |
| RNF-ACC-05 | Objetivos táctiles mínimos de 24×24px (AA), recomendado 44×44px en contextos táctiles. |

## 6. Responsive

| ID | Requisito |
|---|---|
| RNF-RESP-01 | La interfaz debe funcionar sin scroll horizontal ni pérdida de funcionalidad en anchos desde 320px hasta 4K. |
| RNF-RESP-02 | Los módulos de uso frecuente en campo (QR, consulta de equipo, registro rápido de mantenimiento) deben estar optimizados prioritariamente para móvil. |
| RNF-RESP-03 | Las tablas de datos densas deben transformarse en vistas de tarjeta en breakpoints móviles, no comprimirse ilegiblemente. |

## 7. Mantenibilidad

| ID | Requisito |
|---|---|
| RNF-MANT-01 | El backend debe seguir Clean Architecture con separación explícita de capas (dominio, aplicación, infraestructura, presentación). |
| RNF-MANT-02 | El frontend debe organizarse por features, no por tipo de archivo, para que cada módulo de negocio sea autocontenible. |
| RNF-MANT-03 | Toda función pública de dominio/servicio debe tener pruebas automatizadas (cobertura mínima 80% en esa capa). |
| RNF-MANT-04 | El código debe pasar linting y type-checking estrictos (TypeScript strict mode, mypy/pyright en backend) como gate de CI obligatorio. |

## 8. Portabilidad

| ID | Requisito |
|---|---|
| RNF-PORT-01 | Todo el stack debe ejecutarse mediante contenedores Docker, sin dependencias instaladas directamente en el host. |
| RNF-PORT-02 | El entorno de desarrollo debe poder levantarse completo (`docker compose up`) sin pasos manuales adicionales. |

## 9. Internacionalización

| ID | Requisito |
|---|---|
| RNF-I18N-01 | Todo texto de interfaz debe externalizarse en archivos de recursos (no strings embebidos en componentes), aunque v1 solo publique español. |
| RNF-I18N-02 | Fechas, números y monedas deben formatearse según el locale configurado, no hardcodeados a un formato regional. |

## 10. Logs y Observabilidad

| ID | Requisito |
|---|---|
| RNF-LOG-01 | Todos los servicios deben emitir logs estructurados (JSON) con nivel, timestamp, tenant_id (cuando aplique) y trace_id de correlación. |
| RNF-LOG-02 | Los logs de aplicación no deben confundirse con el log de auditoría de negocio (`RF-AUD-01`) — son mecanismos separados con propósitos distintos: uno es para operar el sistema, el otro es un registro de negocio inmutable. |
| RNF-LOG-03 | Debe existir un endpoint de health check por servicio, consumible por el orquestador de contenedores. |

## 11. Backups y retención

| ID | Requisito |
|---|---|
| RNF-BKP-01 | Backups automáticos diarios de base de datos, retenidos 30 días en rotación estándar. |
| RNF-BKP-02 | Política de retención de logs de auditoría: **pendiente de definición por el Product Owner según normativa aplicable en cada jurisdicción de despliegue** (riesgo abierto documentado en `00-analisis-critico-y-recomendaciones.md`, sección 5). Como valor por defecto propuesto: retención indefinida para logs de auditoría (dado su rol en compliance), con posible archivado en frío tras 2 años. |
| RNF-BKP-03 | Debe existir un procedimiento documentado y probado de restauración (no solo de backup), verificado trimestralmente. |
