# 03 — Requerimientos Funcionales

Convención: cada requisito funcional se identifica como `RF-<módulo>-<número>`. Los roles usados en "Permisos" son los definidos en `10-gestion-usuarios` (ver `06-historias-de-usuario.md` y `16-seguridad.md`): **Administrador (A)**, **Director Técnico (DT)**, **Calidad (C)**, **Metrología (M)**, **Técnico (T)**, **Consulta (CO)**. Todos los módulos operan dentro del contexto de un único laboratorio (tenant) — ningún usuario ve datos de otro laboratorio salvo el rol de plataforma `Superadmin` (ver `16-seguridad.md`).

---

## Módulo 1 — Autenticación

**Objetivo:** permitir el acceso seguro de usuarios registrados a su laboratorio, con verificación de credenciales, gestión de sesión y recuperación de contraseña.

| ID | Requisito |
|---|---|
| RF-AUTH-01 | El sistema debe permitir iniciar sesión con usuario y contraseña, validando ambos contra el laboratorio (tenant) resuelto por subdominio o selector explícito. |
| RF-AUTH-02 | El sistema debe emitir un access token JWT de corta duración (15 min) y un refresh token de larga duración (7 días, rotativo) al autenticar exitosamente. |
| RF-AUTH-03 | El sistema debe permitir mostrar/ocultar la contraseña ingresada. |
| RF-AUTH-04 | El sistema debe ofrecer la opción "Recordarme", que extiende la vida del refresh token. |
| RF-AUTH-05 | El sistema debe permitir solicitar recuperación de contraseña vía correo (envío a través del outbox de notificaciones). |
| RF-AUTH-06 | El sistema debe bloquear progresivamente el inicio de sesión tras intentos fallidos consecutivos (ver `16-seguridad.md`). |
| RF-AUTH-07 | El sistema debe cerrar la sesión invalidando el refresh token activo. |
| RF-AUTH-08 | El modelo de datos debe soportar un segundo factor de autenticación (MFA) aunque no se active en v1 (campo `mfa_habilitado`, sin flujo de UI todavía). |

- **Entradas:** usuario, contraseña, laboratorio (tenant).
- **Procesos:** validación de credenciales, verificación de estado de cuenta (activo/bloqueado), emisión de tokens, registro en auditoría.
- **Salidas:** sesión autenticada (tokens) o mensaje de error específico sin revelar si el usuario existe.
- **Permisos:** público (previo a autenticación).
- **Validaciones:** formato de usuario, longitud mínima de contraseña, estado de cuenta no bloqueada, tenant activo.

---

## Módulo 2 — Dashboard Ejecutivo

**Objetivo:** ofrecer una vista consolidada del estado de cumplimiento del laboratorio en tiempo real.

| ID | Requisito |
|---|---|
| RF-DASH-01 | Mostrar KPI cards: equipos activos, equipos fuera de servicio, calibraciones próximas a vencer, calibraciones vencidas, documentos vigentes, documentos por vencer, mantenimientos pendientes, % de cumplimiento mensual. |
| RF-DASH-02 | Mostrar gráficas interactivas (donut de estado de equipos, línea de tendencia de cumplimiento, barras comparativas por área/categoría). |
| RF-DASH-03 | Mostrar un calendario resumido de los próximos 7 días. |
| RF-DASH-04 | Mostrar una timeline de actividad reciente (últimas acciones relevantes del laboratorio). |
| RF-DASH-05 | Mostrar alertas prioritarias (críticas) de forma destacada. |
| RF-DASH-06 | Permitir configurar qué widgets se muestran y en qué orden (por usuario). |
| RF-DASH-07 | Los datos del dashboard deben poder actualizarse en tiempo real vía WebSocket cuando cambien (nueva alerta, calibración registrada), con fallback a recarga periódica. |

- **Entradas:** ninguna directa (agregación de datos de otros módulos).
- **Procesos:** agregación y cálculo de KPIs (ver fórmulas en `07-reglas-de-negocio.md`), suscripción a eventos en tiempo real.
- **Salidas:** vista consolidada con KPIs, gráficas y timeline.
- **Permisos:** A, DT, C, M ven el dashboard completo; T ve una vista reducida centrada en sus tareas asignadas; CO ve una vista de solo lectura sin acciones.
- **Validaciones:** ninguna de entrada; los cálculos deben excluir registros soft-deleted.

---

## Módulo 3 — Equipos

**Objetivo:** mantener el inventario completo y la ficha técnica de cada equipo biomédico del laboratorio.

| ID | Requisito |
|---|---|
| RF-EQ-01 | Registrar un equipo con: código interno (único por laboratorio), nombre, categoría, marca, modelo, número de serie, fabricante, proveedor, fecha de adquisición, estado operativo, área/laboratorio, responsable, manual de usuario (archivo), fotografía, observaciones. |
| RF-EQ-02 | Generar automáticamente un código QR único al crear el equipo. |
| RF-EQ-03 | Editar cualquier campo de un equipo existente, registrando el cambio en auditoría. |
| RF-EQ-04 | Eliminar un equipo mediante soft delete (nunca eliminación física) — ver regla de negocio RN-EQ-01. |
| RF-EQ-05 | Duplicar un equipo existente como plantilla para uno nuevo. |
| RF-EQ-06 | Buscar equipos por cualquier campo indexado (código, nombre, número de serie) con resultados instantáneos. |
| RF-EQ-07 | Filtrar equipos por categoría, estado operativo, área, responsable, y estado de calibración (semáforo). |
| RF-EQ-08 | Exportar el listado filtrado de equipos a PDF y Excel. |
| RF-EQ-09 | Mostrar el historial completo de cambios de un equipo (quién, cuándo, qué cambió). |
| RF-EQ-10 | Adjuntar documentos relacionados a un equipo (manuales, certificados, fichas técnicas) enlazando con el módulo Documentos. |
| RF-EQ-11 | Mostrar en la ficha del equipo su estado de calibración vigente (semáforo) y su próxima fecha de mantenimiento. |

- **Entradas:** datos del formulario de ficha técnica, archivo de fotografía, archivo de manual.
- **Procesos:** validación de unicidad de código interno, generación de QR, cálculo de estado agregado (última calibración + próximo mantenimiento).
- **Salidas:** ficha técnica del equipo, listado filtrable, exportaciones.
- **Permisos:** A, DT, M pueden crear/editar; T puede editar campos operativos limitados (estado, observaciones) según configuración de rol; C y CO solo lectura.
- **Validaciones:** código interno único por laboratorio, campos obligatorios (código, nombre, categoría, estado operativo), tipo de archivo permitido para fotografía (JPG/PNG/WEBP) y manual (PDF).

---

## Módulo 4 — Gestor Documental

**Objetivo:** centralizar la documentación de calidad del laboratorio con control de versiones, vigencia y aprobación.

| ID | Requisito |
|---|---|
| RF-DOC-01 | Subir uno o varios archivos simultáneamente (drag & drop) con barra de progreso individual. |
| RF-DOC-02 | Soportar los formatos: PDF, DOCX, XLSX, PPTX, CSV, TXT, JPG, PNG, WEBP. |
| RF-DOC-03 | Organizar documentos en carpetas y subcarpetas ilimitadas. |
| RF-DOC-04 | Etiquetar documentos con una o más etiquetas y categorías. |
| RF-DOC-05 | Marcar documentos como favoritos (por usuario). |
| RF-DOC-06 | Mostrar documentos recientes y documentos compartidos con el usuario. |
| RF-DOC-07 | Previsualizar el documento sin descargarlo (PDF e imágenes; para DOCX/XLSX/PPTX, vista de metadatos si no hay previsualización nativa disponible). |
| RF-DOC-08 | Descargar el documento de forma segura (URL firmada de corta duración, nunca acceso directo al bucket). |
| RF-DOC-09 | Renombrar, mover entre carpetas y copiar documentos. |
| RF-DOC-10 | Eliminar documentos a una papelera (soft delete) con posibilidad de restaurar dentro de una ventana configurable. |
| RF-DOC-11 | Versionar automáticamente cada archivo subido con el mismo nombre/documento lógico, manteniendo historial completo de versiones descargable. |
| RF-DOC-12 | Marcar el estado de cada documento: vigente, obsoleto, en revisión — con fecha de emisión, fecha de vencimiento y responsable de aprobación. |
| RF-DOC-13 | Impedir que un documento vencido se muestre o exporte como vigente (ver RN-DOC-01). |
| RF-DOC-14 | Registrar quién aprobó cada versión y cuándo (base para firma electrónica simple, ver `00-analisis-critico-y-recomendaciones.md`). |

- **Entradas:** archivo(s), metadatos (carpeta, etiquetas, categoría, fecha de vigencia, responsable de aprobación).
- **Procesos:** subida a MinIO vía URL prefirmada, cálculo de nueva versión, actualización de estado de vigencia (job programado), registro en auditoría.
- **Salidas:** documento almacenado, historial de versiones, URL de descarga firmada.
- **Permisos:** C y A gestionan el ciclo de vida completo (incluida aprobación); DT y M pueden subir documentos de su área; T solo lectura y subida a carpetas específicas asignadas; CO solo lectura de documentos vigentes.
- **Validaciones:** tamaño máximo de archivo (configurable, ej. 50 MB), tipo MIME permitido, fecha de vencimiento posterior a fecha de emisión.

---

## Módulo 5 — Calibraciones

**Objetivo:** registrar y controlar automáticamente el estado de vigencia de las calibraciones de cada equipo, con trazabilidad metrológica.

| ID | Requisito |
|---|---|
| RF-CAL-01 | Registrar una calibración con: equipo asociado, fecha de calibración, frecuencia, laboratorio proveedor, número de certificado, resultado, incertidumbre de medición, responsable, observaciones, certificado PDF adjunto. |
| RF-CAL-02 | Calcular automáticamente la próxima fecha de calibración según la frecuencia definida. |
| RF-CAL-03 | Calcular automáticamente los días restantes y el estado semafórico (verde/amarillo/rojo/gris) según las reglas de negocio RN-CAL-01 a RN-CAL-04. |
| RF-CAL-04 | Mostrar la tendencia histórica de resultados de calibración de un equipo (gráfica de línea). |
| RF-CAL-05 | Listar los equipos críticos próximos a vencer, ordenados por urgencia. |
| RF-CAL-06 | Adjuntar el certificado de calibración en PDF, descargable de forma segura. |
| RF-CAL-07 | Impedir la eliminación física de una calibración registrada (solo corrección con nueva entrada y motivo, preservando la original en auditoría). |

- **Entradas:** datos del formulario de calibración, archivo de certificado.
- **Procesos:** cálculo de próxima fecha, cálculo de estado semafórico (recalculado diariamente por job programado y en cada lectura), generación de alerta si cruza umbral.
- **Salidas:** registro de calibración, estado semafórico del equipo, alerta automática si corresponde.
- **Permisos:** M y A pueden crear/editar; DT y C solo lectura con permiso de exportar reportes; T solo lectura; CO solo lectura.
- **Validaciones:** equipo debe existir y estar activo, fecha de calibración no puede ser futura, frecuencia debe ser un valor positivo, incertidumbre debe ser numérica cuando aplica.

---

## Módulo 6 — Mantenimientos

**Objetivo:** registrar y programar el mantenimiento preventivo, correctivo y predictivo de los equipos.

| ID | Requisito |
|---|---|
| RF-MANT-01 | Registrar un mantenimiento con: equipo asociado, tipo (preventivo/correctivo/predictivo/calibración correctiva), fecha programada, fecha ejecutada, técnico responsable, descripción, repuestos utilizados, tiempo de inactividad, costo, evidencias fotográficas, informe PDF. |
| RF-MANT-02 | Programar mantenimientos preventivos recurrentes según frecuencia definida por equipo o categoría. |
| RF-MANT-03 | Cambiar el estado del equipo a "Fuera de servicio" o "En mantenimiento" automáticamente al iniciar un mantenimiento correctivo, y de vuelta a "Operativo" al cerrarlo. |
| RF-MANT-04 | Calcular el tiempo de inactividad total por equipo en un periodo (para indicadores de disponibilidad). |
| RF-MANT-05 | Adjuntar evidencias fotográficas e informe PDF al cierre del mantenimiento. |

- **Entradas:** datos del formulario de mantenimiento, archivos de evidencia.
- **Procesos:** actualización de estado operativo del equipo, cálculo de tiempo de inactividad, generación de alerta de mantenimiento próximo.
- **Salidas:** registro de mantenimiento, actualización de estado del equipo, indicador de disponibilidad.
- **Permisos:** M, T y A pueden crear/editar mantenimientos; DT y C solo lectura; CO solo lectura.
- **Validaciones:** equipo debe existir, fecha ejecutada no puede ser anterior a fecha programada sin justificación, técnico responsable debe ser un usuario activo del laboratorio.

---

## Módulo 7 — Alertas y Notificaciones

**Objetivo:** notificar proactivamente vencimientos y eventos críticos sin depender de revisión manual.

| ID | Requisito |
|---|---|
| RF-ALT-01 | Generar alerta crítica automática cuando: una calibración vence, un equipo pasa a fuera de servicio, un documento obligatorio vence. |
| RF-ALT-02 | Generar alerta preventiva automática cuando: una calibración vence en ≤30 días (configurable), un mantenimiento vence en ≤15 días (configurable), un documento vence en ≤30 días (configurable). |
| RF-ALT-03 | Mostrar notificaciones tipo toast para eventos ocurridos durante la sesión activa. |
| RF-ALT-04 | Mantener un centro de alertas persistente, con estado leído/no leído. |
| RF-ALT-05 | Encolar cada alerta en un outbox de notificaciones, preparado para envío por correo electrónico y push (no implementado en v1, ver `00-analisis-critico-y-recomendaciones.md`). |
| RF-ALT-06 | Permitir marcar alertas como atendidas/resueltas. |

- **Entradas:** eventos generados por otros módulos (calibración, mantenimiento, documento).
- **Procesos:** evaluación de umbrales (job programado diario + evaluación on-write), inserción en outbox, push en tiempo real vía WebSocket a usuarios conectados.
- **Salidas:** alertas in-app, entradas en outbox para canales futuros.
- **Permisos:** todos los roles ven las alertas relevantes a su ámbito; A y DT ven todas las alertas del laboratorio.
- **Validaciones:** no duplicar alertas para el mismo evento/umbral ya notificado.

---

## Módulo 8 — Calendario Operacional

**Objetivo:** ofrecer una vista unificada de todos los eventos operativos del laboratorio.

| ID | Requisito |
|---|---|
| RF-CAL2-01 | Mostrar en el calendario: calibraciones, mantenimientos, auditorías, capacitaciones, vencimientos documentales, eventos institucionales. |
| RF-CAL2-02 | Ofrecer vistas de día, semana, mes y agenda. |
| RF-CAL2-03 | Permitir crear eventos institucionales manuales (auditorías, capacitaciones) directamente en el calendario. |
| RF-CAL2-04 | Permitir filtrar el calendario por tipo de evento y por área/responsable. |
| RF-CAL2-05 | Permitir navegar desde un evento del calendario directamente al registro de origen (equipo, documento, calibración). |

- **Entradas:** eventos generados por otros módulos + eventos manuales.
- **Procesos:** agregación de eventos de múltiples módulos en una vista unificada.
- **Salidas:** vista de calendario interactiva.
- **Permisos:** todos los roles ven el calendario; solo A, DT y C pueden crear eventos institucionales manuales.
- **Validaciones:** fecha de evento manual no puede ser nula; título obligatorio.

---

## Módulo 9 — Búsqueda Global

**Objetivo:** encontrar cualquier entidad del sistema desde un único punto de entrada.

| ID | Requisito |
|---|---|
| RF-SEARCH-01 | Ofrecer un omnibox accesible mediante atajo de teclado (Cmd/Ctrl+K) desde cualquier pantalla. |
| RF-SEARCH-02 | Buscar simultáneamente en: equipos, documentos, certificados, usuarios, calibraciones, mantenimientos, auditorías. |
| RF-SEARCH-03 | Agrupar resultados por tipo de entidad. |
| RF-SEARCH-04 | Permitir navegación completa por teclado (flechas, Enter) sin usar el mouse. |
| RF-SEARCH-05 | Restringir resultados según los permisos del usuario que busca (nunca mostrar resultados a los que no tiene acceso). |

- **Entradas:** texto de búsqueda.
- **Procesos:** búsqueda indexada (PostgreSQL full-text search en v1; ver `13-arquitectura.md` para evolución futura a motor dedicado si el volumen lo justifica).
- **Salidas:** resultados agrupados y rankeados por relevancia.
- **Permisos:** resultados filtrados según RBAC del usuario.
- **Validaciones:** longitud mínima de consulta (2 caracteres) antes de ejecutar búsqueda.

---

## Módulo 10 — Gestión de Usuarios y Permisos

**Objetivo:** administrar usuarios, roles y permisos granulares del laboratorio.

| ID | Requisito |
|---|---|
| RF-USR-01 | Crear, editar y desactivar usuarios del laboratorio. |
| RF-USR-02 | Asignar uno o más roles a cada usuario (Administrador, Director Técnico, Calidad, Metrología, Técnico, Consulta). |
| RF-USR-03 | Modelar permisos como relación granular rol-permiso (no roles hardcodeados en código), permitiendo ajustar permisos por laboratorio si fuera necesario. |
| RF-USR-04 | Forzar cambio de contraseña en el primer inicio de sesión. |
| RF-USR-05 | Aplicar política de complejidad de contraseña configurable. |
| RF-USR-06 | Mostrar y permitir cerrar sesiones activas de un usuario (gestión de sesiones). |
| RF-USR-07 | Registrar en auditoría toda alta, baja o cambio de rol de usuario. |

- **Entradas:** datos del usuario, roles asignados.
- **Procesos:** validación de unicidad de correo/usuario por tenant, hash de contraseña, asignación de permisos derivados del rol.
- **Salidas:** usuario creado/editado, lista de sesiones activas.
- **Permisos:** solo A gestiona usuarios y roles; el resto de roles solo puede editar su propio perfil (`14-configuracion-perfil`).
- **Validaciones:** correo único por tenant, rol válido existente, contraseña cumple política mínima.

---

## Módulo 11 — Auditoría y Trazabilidad

**Objetivo:** registrar de forma inmutable toda acción relevante del sistema.

| ID | Requisito |
|---|---|
| RF-AUD-01 | Registrar en cada acción de creación, edición o eliminación: usuario, fecha y hora, dirección IP, módulo, acción realizada, valor anterior, valor nuevo. |
| RF-AUD-02 | Ofrecer una pantalla de auditoría avanzada con filtros por usuario, módulo, rango de fechas y tipo de acción. |
| RF-AUD-03 | Permitir exportar el resultado filtrado de auditoría a PDF/Excel/CSV. |
| RF-AUD-04 | Impedir la edición o eliminación de registros de auditoría por cualquier rol, incluido Administrador (append-only). |

- **Entradas:** eventos generados automáticamente por el resto de módulos.
- **Procesos:** escritura append-only en tabla de auditoría, sin exposición de operación UPDATE/DELETE a nivel de aplicación ni de base de datos (permisos de base de datos revocados para esas operaciones sobre la tabla).
- **Salidas:** bitácora consultable y exportable.
- **Permisos:** A y C pueden consultar/exportar auditoría completa del laboratorio; el resto de roles no tiene acceso a este módulo.
- **Validaciones:** ninguna de entrada directa (el registro es automático, no manual).

---

## Módulo 12 — Reportes

**Objetivo:** generar reportes profesionales exportables para gestión interna y auditorías externas.

| ID | Requisito |
|---|---|
| RF-REP-01 | Generar reporte de inventario de equipos. |
| RF-REP-02 | Generar reporte de estado de calibraciones (vigentes/próximas/vencidas). |
| RF-REP-03 | Generar reporte de equipos vencidos (calibración o mantenimiento). |
| RF-REP-04 | Generar reporte de indicadores de cumplimiento (histórico mensual). |
| RF-REP-05 | Generar reporte de historial de mantenimiento por equipo o por periodo. |
| RF-REP-06 | Generar reporte de trazabilidad documental. |
| RF-REP-07 | Generar "paquete de auditoría ISO 15189" consolidado por equipo (ficha + calibraciones + mantenimientos + documentos vigentes) en un solo PDF/ZIP. |
| RF-REP-08 | Exportar cualquier reporte a PDF corporativo, Excel y CSV. |

- **Entradas:** filtros de periodo, equipo, categoría, área.
- **Procesos:** agregación de datos de los módulos correspondientes, renderizado a PDF con plantilla corporativa.
- **Salidas:** archivo descargable en el formato solicitado.
- **Permisos:** A, DT, C tienen acceso completo; M y T acceso a reportes de su ámbito; CO solo reportes de solo lectura permitidos por configuración.
- **Validaciones:** rango de fechas válido, al menos un filtro aplicado en reportes de gran volumen para evitar exportaciones excesivas.

---

## Módulo 13 — Código QR Inteligente

**Objetivo:** dar acceso rápido y responsive al estado de un equipo desde un dispositivo móvil.

| ID | Requisito |
|---|---|
| RF-QR-01 | Generar automáticamente un código QR único por equipo al crearlo. |
| RF-QR-02 | Al escanear, abrir una vista pública responsive de solo lectura (sin necesidad de iniciar sesión) mostrando: foto, estado actual, última calibración, próxima calibración, documentos asociados públicos, historial resumido. |
| RF-QR-03 | Incluir en la vista QR un botón "Reportar novedad" que crea una incidencia sin requerir autenticación completa (captura nombre/contacto de quien reporta). |
| RF-QR-04 | La vista QR debe funcionar con conectividad débil (respuesta ligera, assets mínimos) y cachear la última versión conocida para lectura offline (ver mejora propuesta en `00-analisis-critico-y-recomendaciones.md`). |

- **Entradas:** identificador de equipo embebido en el QR (token no adivinable, no el ID incremental de base de datos).
- **Procesos:** resolución del token a equipo, filtrado de datos públicos vs. privados, registro de incidencia si se reporta novedad.
- **Salidas:** vista pública responsive, incidencia creada (visible luego en el módulo de Mantenimientos como solicitud pendiente de triage).
- **Permisos:** acceso público de solo lectura a datos no sensibles; creación de incidencia sin autenticación pero con captura de contacto para trazabilidad.
- **Validaciones:** token de QR debe ser válido y no revocado; equipo no debe estar dado de baja (o debe mostrarse claramente como "dado de baja" si lo está).

---

## Módulo 14 — Configuración y Perfil

**Objetivo:** permitir a cada usuario gestionar su perfil y preferencias, y al Administrador configurar parámetros del laboratorio.

| ID | Requisito |
|---|---|
| RF-CFG-01 | Editar datos de perfil propio (nombre, correo, contraseña, foto). |
| RF-CFG-02 | Cambiar entre modo claro y modo oscuro, persistiendo la preferencia. |
| RF-CFG-03 | (Administrador) Configurar umbrales de alerta (días para "próximo a vencer") por tipo de evento. |
| RF-CFG-04 | (Administrador) Configurar datos institucionales del laboratorio (nombre, logo, información para reportes). |
| RF-CFG-05 | (Administrador) Configurar categorías de equipo, áreas y frecuencias de calibración por defecto. |

- **Entradas:** datos de perfil o de configuración institucional.
- **Procesos:** validación y persistencia de preferencias, aplicación inmediata de tema visual.
- **Salidas:** perfil actualizado, configuración institucional actualizada.
- **Permisos:** cada usuario gestiona su propio perfil; solo A gestiona configuración institucional.
- **Validaciones:** correo válido y único, umbrales de alerta deben ser enteros positivos.

---

## Resumen de trazabilidad módulo → objetivo de negocio

Ver matriz de trazabilidad completa entre requerimientos funcionales, historias de usuario y casos de uso en `05-casos-de-uso.md` y `06-historias-de-usuario.md`.
