# 06 — Historias de Usuario

Formato Agile estándar con criterios de aceptación en Given/When/Then. Agrupadas por rol, con ID referenciado desde `05-casos-de-uso.md`.

---

## Administrador

### HU-ADMIN-01
**Como** Administrador
**Quiero** configurar los datos institucionales de mi laboratorio
**Para** que los reportes y la interfaz reflejen correctamente mi organización

**Criterios de aceptación:**
- Given que soy Administrador autenticado, When guardo el nombre, logo y umbrales de alerta institucionales, Then estos se aplican inmediatamente a reportes y notificaciones nuevas.
- Given que dejo un campo obligatorio vacío, When intento guardar, Then el sistema me indica exactamente qué campo falta.

### HU-ADMIN-02
**Como** Administrador
**Quiero** invitar usuarios y asignarles un rol
**Para** que cada persona del laboratorio tenga acceso acorde a su función

**Criterios de aceptación:**
- Given un correo no registrado en mi laboratorio, When lo invito con un rol, Then el usuario recibe un enlace de activación válido por 72 horas.
- Given un correo ya registrado en mi laboratorio, When intento invitarlo de nuevo, Then el sistema me lo indica sin revelar más información de la cuenta existente.

### HU-ADMIN-03
**Como** Administrador
**Quiero** filtrar y exportar la bitácora de auditoría
**Para** investigar una acción específica o presentar evidencia a un auditor

**Criterios de aceptación:**
- Given filtros de módulo, usuario y rango de fechas, When ejecuto la búsqueda, Then veo únicamente los registros que cumplen todos los filtros.
- Given un resultado filtrado, When exporto a PDF, Then el archivo conserva los mismos filtros aplicados y una marca de fecha de generación.

---

## Director Técnico

### HU-DT-01
**Como** Director Técnico
**Quiero** ver el porcentaje de cumplimiento y los equipos críticos en el Dashboard
**Para** anticipar riesgos antes de una auditoría externa

**Criterios de aceptación:**
- Given equipos con calibración vencida, When entro al Dashboard, Then los veo listados con prioridad visual (semáforo rojo) antes que los demás.
- Given que no hay equipos críticos, When entro al Dashboard, Then el indicador de cumplimiento se muestra en verde con un mensaje positivo, no vacío.

### HU-DT-02
**Como** Director Técnico
**Quiero** aprobar o rechazar documentos pendientes de revisión
**Para** garantizar que solo entren en vigencia documentos correctos

**Criterios de aceptación:**
- Given un documento en estado "en revisión", When lo apruebo, Then queda marcado como vigente y la versión anterior pasa a obsoleta automáticamente.
- Given un documento en estado "en revisión", When lo rechazo con un comentario, Then Calidad recibe notificación con el motivo.

---

## Calidad

### HU-CAL-01
**Como** responsable de Calidad
**Quiero** subir una nueva versión de un procedimiento
**Para** mantener actualizada la documentación sin perder el historial de versiones anteriores

**Criterios de aceptación:**
- Given un documento existente, When subo un archivo con el mismo nombre lógico, Then el sistema lo registra como nueva versión, no como documento duplicado.
- Given una nueva versión subida, When consulto el historial, Then veo todas las versiones anteriores con fecha y responsable de cada una.

### HU-CAL-02
**Como** responsable de Calidad
**Quiero** recibir alertas antes de que un documento venza
**Para** gestionar su renovación con tiempo suficiente

**Criterios de aceptación:**
- Given un documento a 30 días de su vencimiento, When se ejecuta la evaluación diaria de alertas, Then recibo una alerta preventiva en el centro de notificaciones.
- Given un documento ya vencido, When cualquier usuario lo visualiza, Then se muestra claramente marcado como vencido, nunca como vigente.

---

## Metrología

### HU-MET-01
**Como** responsable de Metrología
**Quiero** registrar una calibración y que el sistema calcule automáticamente la próxima fecha y el estado
**Para** no depender de cálculos manuales propensos a error

**Criterios de aceptación:**
- Given una calibración con frecuencia de 12 meses registrada hoy, When la guardo, Then la próxima fecha se calcula automáticamente a 12 meses.
- Given un equipo cuya calibración queda a 10 días de vencer, When se evalúan los umbrales, Then el estado semafórico pasa a amarillo automáticamente sin intervención manual.

### HU-MET-02
**Como** responsable de Metrología
**Quiero** ver la tendencia histórica de resultados de calibración de un equipo
**Para** anticipar si un equipo está degradando su desempeño metrológico

**Criterios de aceptación:**
- Given un equipo con más de una calibración registrada, When abro su ficha, Then veo una gráfica de línea con los resultados en el tiempo.
- Given un equipo con una sola calibración, When abro su ficha, Then el sistema muestra el dato disponible sin error por falta de histórico.

---

## Técnico

### HU-TEC-01
**Como** Técnico
**Quiero** ver mis mantenimientos programados del día
**Para** organizar mi trabajo sin tener que buscar manualmente en el sistema

**Criterios de aceptación:**
- Given mantenimientos asignados a mi usuario para hoy, When entro a mi Dashboard, Then los veo listados como primera prioridad visual.
- Given que cierro un mantenimiento correctivo, When confirmo el cierre, Then el estado operativo del equipo vuelve a "Operativo" automáticamente.

### HU-TEC-02
**Como** cualquier persona en campo (con o sin cuenta)
**Quiero** escanear el QR de un equipo y reportar una novedad
**Para** que el problema quede registrado sin depender de encontrar a alguien del laboratorio

**Criterios de aceptación:**
- Given un QR válido escaneado, When se abre la vista pública, Then veo el estado actual del equipo en menos de 2 segundos en una conexión móvil estándar.
- Given el formulario de "Reportar novedad" completado, When lo envío, Then se crea una incidencia visible para el equipo de Metrología/Técnicos sin requerir que yo tenga una cuenta.

---

## Consulta

### HU-CO-01
**Como** usuario de Consulta
**Quiero** ver la información operativa de equipos y documentos sin poder modificarla
**Para** informarme sin riesgo de alterar datos por error

**Criterios de aceptación:**
- Given mi rol de Consulta, When veo la ficha de un equipo, Then no existe ningún control de edición visible ni accesible.
- Given que intento acceder directamente a una URL de edición, When la solicito, Then el sistema responde con acceso denegado y registra el intento en auditoría.

---

## Transversal (todos los roles)

### HU-ALL-01
**Como** usuario autenticado de cualquier rol
**Quiero** que la interfaz respete mi preferencia de modo claro/oscuro y mis capacidades de accesibilidad
**Para** usar la plataforma cómodamente según mis necesidades

**Criterios de aceptación:**
- Given que activo el modo oscuro, When recargo la aplicación en otra sesión, Then mi preferencia persiste.
- Given que tengo activado `prefers-reduced-motion` en mi sistema operativo, When navego la aplicación, Then las animaciones no esenciales se desactivan automáticamente.
