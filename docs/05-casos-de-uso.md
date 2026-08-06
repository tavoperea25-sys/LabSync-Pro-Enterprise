# 05 — Casos de Uso

Convención: `CU-<número>`. Se documentan los casos de uso representativos de mayor valor de negocio por rol; los CRUD simples de cada módulo (crear/editar/listar) siguen el mismo patrón de flujo y están cubiertos en detalle campo a campo en `03-requerimientos-funcionales.md`.

---

## Actor: Administrador

### CU-01 — Configurar el laboratorio y dar de alta usuarios

- **Actor:** Administrador
- **Objetivo:** dejar el laboratorio operativo con su información institucional, categorías de equipo y equipo humano registrado.
- **Flujo principal:**
  1. El Administrador inicia sesión por primera vez con credenciales provistas por el operador de la plataforma.
  2. El sistema fuerza cambio de contraseña (RF-USR-04).
  3. El Administrador completa datos institucionales (nombre, logo, umbrales de alerta) en Configuración.
  4. El Administrador crea las categorías de equipo y áreas del laboratorio.
  5. El Administrador invita usuarios por correo, asignando rol a cada uno.
  6. Cada usuario invitado recibe un enlace de activación y define su contraseña.
- **Flujos alternativos:**
  - 3a. El Administrador omite la configuración institucional y la completa después — el sistema permite operar con valores por defecto.
  - 5a. El Administrador asigna más de un rol a un mismo usuario (ej. Calidad + Metrología).
- **Errores:**
  - Correo de invitación ya registrado en el tenant → el sistema rechaza con mensaje claro.
  - Rol inexistente seleccionado → validación de formulario bloquea el envío.
- **Resultado esperado:** laboratorio configurado y equipo humano con acceso operativo, cada uno con el rol correcto.

### CU-02 — Auditar una acción sospechosa

- **Actor:** Administrador
- **Objetivo:** investigar quién modificó un registro crítico y cuándo.
- **Flujo principal:**
  1. El Administrador entra al módulo de Auditoría.
  2. Filtra por módulo (ej. Calibraciones), rango de fechas y usuario.
  3. Revisa el detalle de la acción: valor anterior, valor nuevo, IP, fecha y hora.
  4. Exporta el resultado filtrado a PDF para conservar evidencia.
- **Flujos alternativos:** ninguno relevante — es un flujo de solo lectura.
- **Errores:** filtro sin resultados → el sistema muestra estado vacío explicativo, no un error.
- **Resultado esperado:** trazabilidad completa de la acción investigada, exportable como evidencia.

---

## Actor: Director Técnico

### CU-03 — Revisar cumplimiento antes de una auditoría externa

- **Actor:** Director Técnico
- **Objetivo:** verificar el estado general de cumplimiento del laboratorio antes de una visita de auditoría ISO 15189.
- **Flujo principal:**
  1. El Director Técnico entra al Dashboard y revisa el % de cumplimiento mensual y los KPIs de vencimientos.
  2. Identifica equipos con calibración vencida o próxima a vencer (semáforo rojo/amarillo).
  3. Para cada equipo crítico, genera el "paquete de auditoría" (RF-REP-07).
  4. Genera el reporte consolidado de indicadores de cumplimiento para presentar a la dirección.
- **Flujos alternativos:**
  - 2a. No hay equipos en estado crítico → el sistema muestra un estado de cumplimiento positivo destacado.
- **Errores:**
  - Un equipo no tiene ninguna calibración registrada → se muestra como "Sin información" (gris), no se omite silenciosamente del reporte.
- **Resultado esperado:** el laboratorio llega a la auditoría con evidencia organizada y sin sorpresas de último momento.

### CU-04 — Aprobar un documento de calidad

- **Actor:** Director Técnico (o Calidad, según configuración del laboratorio)
- **Objetivo:** aprobar formalmente una nueva versión de un procedimiento antes de que entre en vigencia.
- **Flujo principal:**
  1. Calidad sube una nueva versión de un procedimiento y la marca "en revisión".
  2. El Director Técnico recibe notificación de documento pendiente de aprobación.
  3. Revisa el documento (previsualización) y lo aprueba, quedando registrado como responsable de aprobación con fecha.
  4. El sistema marca automáticamente la versión anterior como obsoleta.
- **Flujos alternativos:**
  - 3a. El Director Técnico rechaza el documento con un comentario — vuelve a estado "en revisión" y notifica a Calidad.
- **Errores:** intento de aprobar un documento sin fecha de vigencia definida → el sistema bloquea la aprobación hasta completar el campo.
- **Resultado esperado:** un único documento vigente por procedimiento, con historial completo de aprobación.

---

## Actor: Calidad

### CU-05 — Gestionar el ciclo de vida de un documento

- **Actor:** Calidad
- **Objetivo:** mantener la documentación de calidad siempre vigente y trazable.
- **Flujo principal:**
  1. Calidad sube un documento nuevo o una nueva versión de uno existente.
  2. Define fecha de emisión, fecha de vencimiento y solicita aprobación.
  3. El sistema notifica al aprobador correspondiente (ver CU-04).
  4. Cuando el documento se acerca a su vencimiento, Calidad recibe alerta preventiva (RF-ALT-02) y gestiona la renovación.
- **Flujos alternativos:** 4a. Calidad marca el documento como obsoleto manualmente si el procedimiento fue descontinuado, sin esperar el vencimiento automático.
- **Errores:** subir un archivo con formato no soportado → el sistema rechaza antes de completar la subida.
- **Resultado esperado:** cero documentos vencidos mostrándose como vigentes en cualquier momento.

---

## Actor: Metrología

### CU-06 — Registrar una calibración y verificar el semáforo resultante

- **Actor:** Metrología
- **Objetivo:** dejar registrada una calibración recién realizada y confirmar que el sistema recalculó correctamente el estado del equipo.
- **Flujo principal:**
  1. Metrología busca el equipo en el módulo Equipos o desde el listado de "próximos a vencer".
  2. Registra la calibración: fecha, laboratorio proveedor, certificado, resultado, incertidumbre.
  3. Adjunta el certificado PDF.
  4. El sistema calcula automáticamente la próxima fecha de calibración y el nuevo estado semafórico.
  5. Metrología confirma en la ficha del equipo que el semáforo pasó a verde.
- **Flujos alternativos:**
  - 2a. El resultado de la calibración es "no conforme" → el sistema genera automáticamente una alerta crítica y sugiere abrir un mantenimiento correctivo.
- **Errores:** certificado con fecha de calibración futura → el sistema rechaza el registro con mensaje explicativo.
- **Resultado esperado:** el equipo refleja su estado real de vigencia inmediatamente después del registro, sin pasos manuales adicionales.

---

## Actor: Técnico

### CU-07 — Ejecutar un mantenimiento y cerrar la orden

- **Actor:** Técnico
- **Objetivo:** ejecutar un mantenimiento programado y dejar evidencia de su cierre.
- **Flujo principal:**
  1. El Técnico ve en su Dashboard reducido las tareas asignadas del día (mantenimientos programados).
  2. Abre la orden de mantenimiento y registra hallazgos, repuestos usados y tiempo de inactividad.
  3. Adjunta evidencia fotográfica y el informe si aplica.
  4. Cierra la orden — el sistema actualiza el estado operativo del equipo a "Operativo" si estaba "En mantenimiento".
- **Flujos alternativos:**
  - 4a. El Técnico determina que el equipo requiere una calibración correctiva adicional — crea la referencia cruzada hacia el módulo de Calibraciones.
- **Errores:** intento de cerrar sin registrar fecha ejecutada → el sistema bloquea el cierre.
- **Resultado esperado:** historial de mantenimiento completo y equipo con estado operativo actualizado.

### CU-08 — Reportar novedad desde el código QR de un equipo

- **Actor:** Técnico (o cualquier persona del laboratorio, incluso sin cuenta)
- **Objetivo:** reportar rápidamente una falla detectada en campo.
- **Flujo principal:**
  1. Se escanea el QR físico del equipo con un celular.
  2. Se abre la vista pública responsive con el estado actual del equipo.
  3. Se pulsa "Reportar novedad", se describe el problema y se indica contacto de quien reporta.
  4. El sistema crea una incidencia visible para Metrología/Técnicos como solicitud pendiente de triage.
- **Flujos alternativos:** sin conectividad, se muestra la última versión cacheada del estado del equipo (solo lectura, sin poder reportar hasta recuperar conexión).
- **Errores:** QR corresponde a un equipo dado de baja → se muestra claramente ese estado en lugar de datos operativos activos.
- **Resultado esperado:** la novedad queda registrada y visible para el equipo técnico sin necesidad de que quien la reporta tenga cuenta en el sistema.

---

## Actor: Consulta

### CU-09 — Consultar el estado de un equipo sin capacidad de edición

- **Actor:** Consulta
- **Objetivo:** verificar información operativa sin riesgo de modificarla accidentalmente.
- **Flujo principal:**
  1. El usuario de Consulta busca el equipo mediante la búsqueda global.
  2. Revisa su ficha técnica, estado de calibración y documentos vigentes asociados.
  3. Exporta un reporte de solo lectura si lo necesita.
- **Flujos alternativos:** ninguno — todos los controles de edición están deshabilitados/ocultos para este rol.
- **Errores:** intento de acceder a una URL de edición directamente → el sistema responde 403 y registra el intento en auditoría.
- **Resultado esperado:** visibilidad completa de solo lectura, sin superficie de riesgo de modificación accidental.

---

## Matriz de trazabilidad (resumen)

| Caso de Uso | Requisitos funcionales relacionados | Historia de usuario relacionada |
|---|---|---|
| CU-01 | RF-USR-01 a RF-USR-07, RF-CFG-03/04/05 | HU-ADMIN-01, HU-ADMIN-02 |
| CU-02 | RF-AUD-01 a RF-AUD-04 | HU-ADMIN-03 |
| CU-03 | RF-DASH-01 a RF-DASH-05, RF-REP-04, RF-REP-07 | HU-DT-01 |
| CU-04 | RF-DOC-12, RF-DOC-14 | HU-CAL-01 |
| CU-05 | RF-DOC-01 a RF-DOC-14 | HU-CAL-02 |
| CU-06 | RF-CAL-01 a RF-CAL-07 | HU-MET-01 |
| CU-07 | RF-MANT-01 a RF-MANT-05 | HU-TEC-01 |
| CU-08 | RF-QR-01 a RF-QR-04 | HU-TEC-02 |
| CU-09 | RF-EQ-06, RF-EQ-07, RF-REP-08 | HU-CO-01 |
