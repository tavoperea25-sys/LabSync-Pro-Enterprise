# 15 — API Design

REST sobre HTTP(S), versionada explícitamente (`/api/v1`), JSON como formato de intercambio (`application/json`), excepto subida/descarga de archivos que usan URLs prefirmadas de MinIO (el API nunca transporta el binario). WebSocket en `/ws/v1/...` para canales en tiempo real.

> **Nota de vigencia (auditoría 2026-07-31, hallazgo I11):** este documento se auditó ruta por ruta contra los 14 routers reales de `app/modules/*/presentation/*.py` (2026-08-04). Se retiraron dos endpoints que nunca existieron (`recuperar-password`/`restablecer-password`), se agregó la sección de Dashboard (faltaba por completo) y se completaron los endpoints reales de Mantenimientos, Alertas, Usuarios y QR, que estaban resumidos de forma engañosa. Sigue siendo un **resumen**, no una referencia exhaustiva tipo OpenAPI — los CRUD estándar (`GET`/`POST`/`PATCH`/`DELETE` sobre el recurso y `GET /{id}`) no se listan uno por uno salvo que tengan una particularidad; lo que se corrigió es que ya no se documentan endpoints inexistentes ni se omiten los que sí importan (paginación, subida de archivos, endpoints de solo-lectura con URL propia). Nota sobre `HTTPS` en el encabezado: hoy el entorno real no tiene terminación TLS (ver `13-arquitectura.md` sección 11) — el diseño de la API es agnóstico a eso, funciona igual sobre HTTP en desarrollo.

---

## 1. Autenticación

Todas las rutas bajo `/api/v1/*` salvo las listadas como públicas requieren header `Authorization: Bearer <access_token>`. El `laboratorio_id` (tenant) se deriva del token, **nunca** se acepta como parámetro de la petición.

| Método | Ruta | Descripción | Público |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Autentica y emite tokens — rate limited (RNF-SEG, `10/minute` por defecto, configurable) | Sí |
| POST | `/api/v1/auth/refresh` | Rota el refresh token y emite nuevo access token — rate limited (`30/minute` por defecto) | Sí (requiere cookie de refresh válida) |
| POST | `/api/v1/auth/logout` | Revoca la sesión activa | No |
| GET | `/api/v1/auth/me` | Datos del usuario autenticado — accesible incluso con `debe_cambiar_password=true` pendiente (RF-USR-04), a diferencia del resto de endpoints | No |

**Corrección de una versión anterior de este documento:** listaba `POST /auth/recuperar-password` y `POST /auth/restablecer-password` como endpoints públicos existentes — **no existen**. Hay un schema Pydantic (`RecuperarPasswordRequest`) definido en el backend que sugiere que se planeó este flujo, pero no está conectado a ningún router. El reseteo de contraseña hoy es **asistido por un administrador**: `PATCH /api/v1/usuarios/{id}` con una contraseña temporal + `debe_cambiar_password=true` fuerza el cambio en el siguiente login del usuario (ver sección "Usuarios y roles" más abajo). Autoservicio no asistido de recuperación (olvidé mi contraseña, sin admin de por medio) es un gap real, no solo de documentación.

**Request `POST /auth/login`:**
```json
{ "laboratorio_slug": "mi-laboratorio", "correo": "usuario@laboratorio.com", "password": "••••••••", "recordarme": true }
```
(`laboratorio_slug` es obligatorio — el tenant no se resuelve solo por el correo, ya que el mismo correo puede existir en más de un laboratorio; no estaba en el ejemplo de una versión anterior de este documento)

**Response 200:**
```json
{ "access_token": "eyJ...", "expira_en": 900, "usuario": { "id": "...", "nombre_completo": "...", "correo": "...", "roles": ["metrologia"], "debe_cambiar_password": false, "foto_url": null, "foto_object_key": null } }
```
(el refresh token se entrega como cookie `httpOnly`, `secure` en producción, `SameSite=strict`, no en el cuerpo de la respuesta)

**Response 401 (formato de error estándar, ver sección 4):**
```json
{ "error": { "codigo": "credenciales_invalidas", "mensaje": "Usuario o contraseña incorrectos." } }
```

**Response 429** tras 5 intentos fallidos sobre la misma cuenta (RF-AUTH-06, bloqueo progresivo — distinto del 429 de rate limiting por IP):
```json
{ "error": { "codigo": "cuenta_bloqueada", "mensaje": "..." } }
```

---

## 2. Endpoints por módulo (resumen — CRUD estándar sigue el mismo patrón salvo excepciones anotadas)

### Dashboard — sección ausente por completo de una versión anterior de este documento
| Método | Ruta | Notas |
|---|---|---|
| GET | `/api/v1/dashboard/kpis` | Contadores agregados (equipos activos, próximas calibraciones, documentación pendiente, mantenimientos, % cumplimiento documental) |
| GET | `/api/v1/dashboard/equipos-criticos` | Equipos con calibración vencida/próxima a vencer, `?limite=` (máx. 50) |
| GET | `/api/v1/dashboard/actividad-reciente` | Últimas entradas de `logs_auditoria` del tenant, formateadas para el widget del Dashboard |

### Equipos
| Método | Ruta | Notas |
|---|---|---|
| GET | `/api/v1/equipos` | Filtros reales: `q`, `categoria_id`, `area_id`, `estado_operativo`; paginación `pagina`/`tamano_pagina` (nombres en español — una versión anterior de este documento decía `page`/`page_size`, y mencionaba un filtro `estado_calibracion` que no existe) |
| POST | `/api/v1/equipos` | Crea; genera QR automáticamente |
| GET | `/api/v1/equipos/{id}` | |
| PATCH | `/api/v1/equipos/{id}` | Edición parcial; genera entrada de auditoría con diff |
| DELETE | `/api/v1/equipos/{id}` | Soft delete |
| POST | `/api/v1/equipos/{id}/duplicar` | RF-EQ-05 — copia la ficha técnica, no el historial de calibraciones/mantenimientos ni la fotografía (sí copia el manual, RN-EQ-04) |
| GET | `/api/v1/equipos/{id}/historial` | Auditoría filtrada por esta entidad |
| GET | `/api/v1/equipos/export` | `?formato=xlsx` (por defecto) — mismos filtros que el listado |
| POST | `/api/v1/equipos/upload-url/foto` | RF-EQ-01, Sprint 24 — URL prefirmada de subida; no documentado antes |
| POST | `/api/v1/equipos/upload-url/manual` | RF-EQ-01, Sprint 26 — URL prefirmada de subida; no documentado antes |
| GET/POST/PATCH/DELETE | `/api/v1/categorias-equipo`, `/api/v1/areas` | CRUD completo (RF-CFG-05) — ver nota en "Configuración" más abajo |

### Calibraciones
| Método | Ruta | Notas |
|---|---|---|
| POST | `/api/v1/calibraciones/upload-url` | URL prefirmada de subida del certificado — no documentado antes |
| POST | `/api/v1/calibraciones` | Calcula `proxima_fecha` y dispara recálculo de semáforo del equipo |
| GET | `/api/v1/calibraciones?equipo_id=` | Sin paginación — acotado por el número de calibraciones de un equipo, no por el total del tenant |
| GET | `/api/v1/calibraciones/{id}` | |
| GET | `/api/v1/calibraciones/{id}/certificado-url` | URL prefirmada de descarga — no documentado antes |
| POST | `/api/v1/calibraciones/{id}/corregir` | Crea entrada referenciando la original (RN-CAL-02) — no hay `PUT`/`DELETE` |
| GET | `/api/v1/calibraciones/criticas` | Listado de equipos próximos a vencer/vencidos, ordenado por urgencia |

### Documentos
| Método | Ruta | Notas |
|---|---|---|
| POST | `/api/v1/documentos/upload-url` | Devuelve URL prefirmada de subida a MinIO |
| POST | `/api/v1/documentos` | Confirma la subida y crea el registro |
| POST | `/api/v1/documentos/{id}/versiones` | Nueva versión de un documento existente — no documentado antes |
| GET | `/api/v1/documentos?carpeta_id=&q=&favoritos=` | Paginado (`pagina`, `tamano_pagina`) desde Sprint 5 — no mencionado antes |
| GET | `/api/v1/documentos/recientes` | No documentado antes |
| GET | `/api/v1/documentos/papelera` | No documentado antes |
| GET | `/api/v1/documentos/{id}` | Incluye historial de versiones |
| GET | `/api/v1/documentos/{id}/vista-previa` | URL de previsualización inline (imágenes/PDF) — distinta de la de descarga, no documentado antes |
| GET | `/api/v1/documentos/{id}/versiones/{version}/download-url` | URL prefirmada de descarga, corta duración |
| POST | `/api/v1/documentos/{id}/aprobar` \| `/rechazar` | Solo roles con permiso `documentos.aprobar` |
| POST | `/api/v1/documentos/{id}/copiar` | No documentado antes |
| POST | `/api/v1/documentos/{id}/favorito` | Alternar favorito — no documentado antes |
| GET/POST/DELETE | `/api/v1/documentos/{id}/etiquetas[/{etiqueta_id}]` | No documentado antes |
| DELETE | `/api/v1/documentos/{id}` | Envío a papelera |
| POST | `/api/v1/documentos/{id}/restaurar` | Dentro de la ventana configurada (RN-DOC-03) |
| GET/POST/PATCH/DELETE | `/api/v1/carpetas[/{id}]` | CRUD de carpetas — no documentado antes como endpoints propios |
| GET | `/api/v1/etiquetas` | Catálogo de etiquetas del tenant — no documentado antes |

### Mantenimientos
Una versión anterior de este documento resumía todo el módulo en una línea ("patrón CRUD estándar... `POST /{id}/cerrar`"); la realidad es más amplia:

| Método | Ruta | Notas |
|---|---|---|
| GET | `/api/v1/mantenimientos?equipo_id=` | Paginado (`pagina`,`tamano_pagina`) para el listado general del tenant desde Sprint 27 — el historial por equipo sigue trayendo todo en una página |
| POST | `/api/v1/mantenimientos` | |
| GET | `/api/v1/mantenimientos/{id}` | |
| POST | `/api/v1/mantenimientos/{id}/iniciar` \| `/cerrar` \| `/cancelar` | `/cerrar` valida `fecha_ejecutada` (RN-MANT-02); `/cancelar` exige un motivo |
| GET | `/api/v1/mantenimientos/hoy` | "Mis mantenimientos de hoy" del usuario autenticado |
| GET | `/api/v1/mantenimientos/inactividad` | Reporte de tiempo de inactividad por equipo |
| POST | `/api/v1/mantenimientos/upload-url/evidencia` \| `/upload-url/informe` | URLs prefirmadas de subida |
| POST/GET | `/api/v1/mantenimientos/{id}/evidencias` | Adjuntar y listar evidencia fotográfica |
| GET | `/api/v1/mantenimientos/evidencias/{adjunto_id}/url` | URL de descarga de una evidencia puntual |
| POST | `/api/v1/mantenimientos/{id}/informe` | Asignar el informe (PDF) del mantenimiento |
| GET | `/api/v1/mantenimientos/{id}/informe-url` | |

### Alertas
| Método | Ruta | Notas |
|---|---|---|
| GET | `/api/v1/alertas?estado=activa` | Paginado (`pagina`, `tamano_pagina`, máx. 100) desde Sprint 28 — no mencionado antes |
| GET | `/api/v1/alertas/contar-activas` | Usado por el badge de la campana de notificaciones — no documentado antes |
| POST | `/api/v1/alertas/{id}/leer` | Marcar como leída, distinto de resolver — no documentado antes |
| POST | `/api/v1/alertas/{id}/resolver` | Resolución manual |
| POST | `/api/v1/alertas/evaluar` | Dispara manualmente la evaluación de vencimientos para el tenant (permiso `alertas.gestionar`) — normalmente corre sola vía el worker cada 5 minutos; no documentado antes |
| WS | `/ws/v1/notificaciones` | Ver sección WebSocket más abajo |

### Calendario
`GET /api/v1/calendario/eventos?desde=&hasta=` agrega eventos de todos los módulos + `POST`/`PATCH`/`DELETE /api/v1/calendario/eventos[/{id}]` para eventos institucionales manuales + `GET /api/v1/calendario/tipos-evento` (catálogo). Una versión anterior de este documento tenía la ruta base como `/api/v1/calendario` sin el segmento `/eventos`.

### Búsqueda global
`GET /api/v1/busqueda?q=` (una versión anterior de este documento decía `/api/v1/buscar` — la ruta real usa `busqueda`) → resultados agrupados por tipo, ya filtrados por los permisos del usuario autenticado.

### Usuarios y roles
| Método | Ruta | Notas |
|---|---|---|
| GET/POST | `/api/v1/usuarios` | Sin paginación (volumen típico de usuarios por laboratorio es acotado) |
| GET/PATCH | `/api/v1/usuarios/{id}` | |
| POST | `/api/v1/usuarios/{id}/desactivar` \| `/activar` | `/desactivar` bloqueado por RN-USR-02 si es el último Administrador activo; el frontend pide confirmación explícita antes de llamar a `/desactivar` (hallazgo de auditoría I10) |
| PUT | `/api/v1/usuarios/{id}/roles` | Reemplaza el conjunto completo de roles — no documentado antes |
| GET | `/api/v1/usuarios/{id}/sesiones` | |
| DELETE | `/api/v1/usuarios/{id}/sesiones/{sesion_id}` | Revoca una sesión puntual — no documentado antes |
| GET | `/api/v1/roles` | Catálogo de roles del tenant + roles de sistema |

Sin flujo de invitación por correo — el Administrador crea la cuenta con una contraseña temporal y `debe_cambiar_password=true` fuerza el cambio en el primer login (ver `usuario_service.py`). Autoservicio (RF-CFG-01, cualquier usuario autenticado sobre sí mismo, sin requerir `usuarios.administrar`): `PATCH /api/v1/usuarios/me` (nombre/correo), `POST /api/v1/usuarios/me/cambiar-password` (revoca todas las sesiones del usuario, igual que RN-USR-01) y `POST /api/v1/usuarios/me/upload-url/foto` (RF-CFG-01, Sprint 25 — no documentado antes).

### Auditoría
`GET /api/v1/auditoria?modulo=&usuario_id=&accion=&desde=&hasta=` + `GET /api/v1/auditoria/valores-filtro` + `GET /api/v1/auditoria/export?formato=csv|xlsx|pdf` — sin endpoints de escritura expuestos (la escritura es interna, no vía API pública). Sin paginación real (límite fijo de 2000 filas tanto en el listado como en la exportación) — inconsistente con el resto de listados grandes del sistema (hallazgo de auditoría, pendiente).

### Reportes
| Método | Ruta | Notas |
|---|---|---|
| GET | `/api/v1/reportes/tipos` | Los 7 tipos disponibles y sus formatos válidos por tipo |
| POST | `/api/v1/reportes/generar` | `{tipo, formato, filtros}`; si el volumen supera el umbral (RNF-PERF-04) responde 201 con `estado="pendiente"` (el worker lo completa); si no, genera y sube en la misma petición y responde `estado="listo"` |
| GET | `/api/v1/reportes/historial` | Historial del laboratorio, más reciente primero |
| GET | `/api/v1/reportes/{id}` | Estado actual de un reporte puntual |
| GET | `/api/v1/reportes/{id}/descargar` | URL prefirmada de descarga; 404 si todavía no está `listo` |

### Configuración
RF-CFG-03/04 (Administrador únicamente, permiso `configuracion.gestionar`); RF-CFG-01 (perfil propio) vive en Usuarios, RF-CFG-02 (tema) es enteramente cliente, RF-CFG-05 (categorías/áreas) vive en Equipos por ser sus tablas — ver notas ahí.
| Método | Ruta | Notas |
|---|---|---|
| GET | `/api/v1/configuracion` | Umbrales de alerta y política de contraseña; valores por defecto si el laboratorio nunca configuró nada |
| PATCH | `/api/v1/configuracion/umbrales` | Enteros positivos (422 si no) — afecta a Calibraciones, Alertas y Reportes en la siguiente consulta, no requiere reinicio |
| PATCH | `/api/v1/configuracion/politica-password` | `politica_password: {...} \| null`; `null` restaura la política fija por defecto |
| PATCH | `/api/v1/configuracion/mapeo-estados-mantenimiento` | RN-MANT-01, Sprint 14 — no documentado antes |
| GET / PATCH | `/api/v1/configuracion/institucion` | Nombre y logo del laboratorio |
| POST | `/api/v1/configuracion/institucion/logo-upload-url` | URL prefirmada de subida a MinIO (PNG/JPG/WEBP, máx. 2MB) |
| GET | `/api/v1/configuracion/exportar-datos` | Sprint 13, portabilidad de datos del tenant — ZIP de CSVs (equipos, documentos, calibraciones, mantenimientos, usuarios, categorías, áreas); nunca incluye `password_hash` ni archivos binarios; síncrono |

Categorías/áreas de equipo (RF-CFG-05) — CRUD completo en `/api/v1/categorias-equipo` y `/api/v1/areas`, mismo permiso `configuracion.gestionar`; `DELETE` responde 409 si algún equipo activo todavía referencia la categoría/área.

Toda petición autenticada recibe/genera una cabecera `X-Request-ID` de correlación — ver `app/core/logging.py`; el mismo valor (como `trace_id`) aparece en los logs estructurados (JSON) del backend y del worker.

### QR
| Método | Ruta | Notas | Público |
|---|---|---|---|
| GET | `/api/v1/publico/qr/{token}` | Devuelve solo campos públicos del equipo — rate limited (`30/minute`) | Sí |
| POST | `/api/v1/publico/qr/{token}/incidencias` | Crea incidencia — rate limited más agresivamente (`5/minute`) | Sí |
| GET | `/api/v1/equipos/{id}/qr` | Token e URL pública del QR de un equipo — no documentado antes | No |
| GET | `/api/v1/equipos/{id}/qr-imagen` | Imagen PNG del código QR — no documentado antes | No |
| GET | `/api/v1/qr/incidencias` | Listado de incidencias reportadas, para triage — no documentado antes | No |
| PATCH | `/api/v1/qr/incidencias/{id}/estado` | Cambia el estado de una incidencia (`pendiente`→`en_revision`→`resuelta`) — no documentado antes | No |

### WebSocket
`WS /ws/v1/notificaciones` — requiere `token` (el access_token) como parámetro de query en el handshake (limitación del WebSocket del navegador, que no puede fijar la cabecera `Authorization` en la conexión inicial — ver `13-arquitectura.md`); emite eventos del canal de alertas del tenant. El cliente cae a *polling* cada 30s si la conexión falla (ver `13-arquitectura.md` sección 6).

---

## 3. Versionado

- Versión en el path (`/api/v1`), no en headers — más simple de depurar y cachear.
- Cambios *breaking* requieren `/api/v2`; cambios aditivos (nuevo campo opcional) no incrementan versión.
- Política de deprecación: una versión antigua se mantiene funcionando mínimo 6 meses tras publicarse la siguiente, con header `Deprecation` en las respuestas durante ese periodo. **Nota:** esta política todavía no se ha ejercitado nunca (el proyecto sigue en `/api/v1` desde el inicio) — es un compromiso a futuro, no algo verificable en el código hoy.

## 4. Formato de error estándar

```json
{
  "error": {
    "codigo": "documento_vencido_no_editable",
    "mensaje": "No se puede marcar como vigente un documento vencido.",
    "detalles": { "campo": "estado" }
  }
}
```
- 400: validación de entrada.
- 401: no autenticado / token expirado.
- 403: autenticado pero sin permiso (incluye intentos de cruzar tenant — RN-TEN-01).
- 404: recurso no encontrado (o perteneciente a otro tenant — nunca se distingue entre "no existe" y "no es tuyo", para no filtrar información).
- 409: conflicto de regla de negocio (ej. código interno duplicado, edición concurrente).
- 422: entidad válida en forma pero inválida en reglas de dominio.
- 429: rate limit excedido (por IP, en `/login`/`/refresh`/QR público) **o** bloqueo progresivo de cuenta (`cuenta_bloqueada`, ver sección 1) — mismo código HTTP, cuerpos distintos. El rate limiting por IP en `/login`/`/refresh` es nuevo (corrección del hallazgo crítico C5 de la auditoría 2026-07-31); antes de esa corrección, `cuenta_bloqueada` era la única causa posible de un 429 en autenticación.
- 500: error no controlado (nunca expone stack trace ni detalles internos al cliente; se loguea internamente con `trace_id`).

**Nota real, no presente en una versión anterior de este documento:** el 429 de rate limiting (slowapi) usa un formato de cuerpo distinto al resto — `{"error": "Rate limit exceeded: ..."}` (string plano), no el objeto `{"codigo","mensaje"}` de arriba. Es una inconsistencia conocida, no corregida todavía (fuera del alcance de la corrección del hallazgo C5).

## 5. Autenticación y autorización por endpoint

Cada endpoint declara explícitamente el/los permisos requeridos (dependency de FastAPI, ver `13-arquitectura.md`); la matriz completa rol↔permiso↔endpoint se mantiene como artefacto vivo en el backend (`app/core/permissions.py` y los seeds de roles/permisos), no duplicada manualmente en este documento para evitar que ambos se desincronicen — este documento referencia la matriz de alto nivel ya definida en `03-requerimientos-funcionales.md` (columna "Permisos" de cada módulo).
