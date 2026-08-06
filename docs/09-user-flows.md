# 09 — User Flows

Notación: cada paso indica pantalla → acción → resultado. Los flujos marcados (*) tienen manejo de error explícito documentado debajo.

---

## Flow 1 — Login *

```
/login
  → usuario ingresa credenciales
  → [válidas] → /dashboard (redirección a la última vista intentada si venía de un deep link protegido)
  → [inválidas] → error inline en el campo correspondiente, foco automático, sin redirección
  → usuario marca "Recordarme" → refresh token de vida extendida
  → usuario hace clic en "¿Olvidaste tu contraseña?" → Flow 2
```

**Errores:** credenciales inválidas (mensaje genérico, no revela si el usuario existe o no), cuenta bloqueada por intentos fallidos (mensaje específico con tiempo de espera), tenant inactivo (mensaje de contacto a soporte).

## Flow 2 — Recuperación de contraseña *

```
/login → "¿Olvidaste tu contraseña?"
  → /recuperar-contraseña → ingresa correo
  → sistema encola correo con enlace de un solo uso (outbox)
  → mensaje neutro: "Si el correo existe, recibirás instrucciones" (no confirma ni niega existencia — mitiga user enumeration)
  → usuario abre el enlace → define nueva contraseña (validada contra política de complejidad)
  → redirección a /login con mensaje de éxito
```

**Errores:** enlace expirado o ya usado → mensaje claro con opción de solicitar uno nuevo.

## Flow 3 — Registrar un equipo nuevo

```
/equipos → botón "Nuevo equipo"
  → /equipos/nuevo (formulario por secciones: Identificación, Ubicación y responsable, Documentación)
  → completa campos obligatorios (validación inline al salir de cada campo, no solo al enviar)
  → sube fotografía (drag & drop u opción de archivo)
  → guarda
  → sistema genera código QR automáticamente
  → redirección a /equipos/:id (ficha recién creada) con confirmación visual (toast)
```

**Errores:** código interno duplicado → error inline específico en ese campo, sin perder el resto de datos ingresados.

## Flow 4 — Subir un documento con control de versión

```
/documentos/carpeta/:id → arrastra archivo(s) al área de drop
  → barra de progreso por archivo
  → [nombre coincide con documento existente] → modal: "¿Nueva versión de [documento] o archivo nuevo?"
      → Nueva versión → se asocia como versión N+1, versión anterior pasa a estado gestionado por Calidad
      → Archivo nuevo → se crea como documento independiente
  → completa metadatos: categoría, etiquetas, fecha de vigencia, aprobador
  → guarda → documento visible en la carpeta con badge de estado (en revisión / vigente)
```

**Errores:** formato no soportado → rechazo antes de iniciar la subida (validación de extensión y MIME en cliente y servidor); archivo excede tamaño máximo → mensaje con el límite exacto.

## Flow 5 — Registrar una calibración

```
/equipos/:id → pestaña "Calibraciones" → "Registrar calibración"
  → formulario: fecha, laboratorio proveedor, certificado (upload), resultado, incertidumbre, frecuencia
  → guarda
  → sistema calcula próxima fecha + estado semafórico
  → ficha del equipo se actualiza en tiempo real (semáforo, próxima fecha)
  → [si resultado = "No conforme"] → banner de alerta con acción sugerida "Abrir mantenimiento correctivo"
```

## Flow 6 — Descargar un certificado desde el Dashboard

```
/dashboard → KPI "Calibraciones vencidas" (clic)
  → /calibraciones/criticos (listado filtrado automáticamente)
  → clic en un registro → /calibraciones/:id
  → botón "Descargar certificado" → URL firmada de corta duración → descarga directa
```

## Flow 7 — Generar un reporte

```
/reportes → selecciona tipo de reporte
  → configura filtros (periodo, categoría, área)
  → [conjunto pequeño] → genera y descarga inmediatamente
  → [conjunto grande, RNF-PERF-04] → se encola como job async → notificación in-app cuando está listo → descarga desde el centro de notificaciones o /reportes/historial
```

## Flow 8 — Buscar con el omnibox

```
cualquier pantalla → Cmd/Ctrl+K
  → overlay de búsqueda con foco automático en el input
  → escribe consulta (mínimo 2 caracteres) → resultados agrupados por tipo en tiempo real
  → navega con flechas ↑↓, Enter para abrir, Esc para cerrar
  → clic/Enter en resultado → navega directamente al detalle, overlay se cierra
```

## Flow 9 — Editar un equipo (con auditoría)

```
/equipos/:id → "Editar" (visible solo si el rol tiene permiso)
  → /equipos/:id/editar → formulario prellenado
  → modifica campos → guarda
  → sistema registra en auditoría: campo(s) modificado(s), valor anterior, valor nuevo
  → redirección a /equipos/:id con confirmación
```

**Errores:** conflicto de edición concurrente (otro usuario editó el mismo registro mientras tanto) → el sistema detecta por versión/timestamp y ofrece revisar los cambios del otro usuario antes de sobrescribir.

## Flow 10 — Escanear QR y reportar novedad (sin autenticación)

```
cámara del celular escanea QR físico
  → /qr/:token (vista pública, sin sidebar)
  → muestra estado actual, última/próxima calibración, documentos públicos
  → "Reportar novedad" → formulario corto (descripción + contacto)
  → envía → confirmación visual → incidencia visible para Metrología/Técnicos
```

**Errores:** token inválido/revocado → página de error clara, no un 404 genérico; equipo dado de baja → banner explícito antes de cualquier otro dato.

## Flow 11 — Cambiar de laboratorio (usuario con acceso a más de uno, si aplica en el futuro)

Fuera de alcance v1 — un usuario pertenece a un único tenant en esta fase (ver `01-vision-del-producto.md`, Fuera de alcance).
