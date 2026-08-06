# 07 — Reglas de Negocio

Convención: `RN-<módulo>-<número>`. Estas reglas son de cumplimiento obligatorio en la capa de dominio del backend — nunca deben depender únicamente de validación en el frontend.

---

## Equipos

- **RN-EQ-01**: un equipo con historial (calibraciones, mantenimientos o documentos asociados) nunca puede eliminarse físicamente; solo puede darse de baja (soft delete / estado "De baja"), preservando todo su historial para auditoría.
- **RN-EQ-02**: el código interno de un equipo es único dentro de su laboratorio (tenant), pero puede repetirse entre laboratorios distintos.
- **RN-EQ-03**: un equipo no puede pasar a estado "Operativo" si tiene una calibración en estado "Vencido" marcada como crítica para su operación (configurable por categoría de equipo).
- **RN-EQ-04**: al duplicar un equipo como plantilla, el nuevo registro nunca copia el historial de calibraciones/mantenimientos del original, solo los campos de ficha técnica.

## Calibraciones

- **RN-CAL-01**: el estado semafórico se calcula así — **Verde (Vigente)**: fecha actual anterior a la próxima fecha de calibración menos el umbral preventivo; **Amarillo (Próximo a vencer)**: dentro del umbral preventivo configurado (por defecto 30 días) antes de la próxima fecha; **Rojo (Vencido)**: fecha actual posterior a la próxima fecha de calibración; **Gris (Sin información)**: el equipo no tiene ninguna calibración registrada.
- **RN-CAL-02**: una calibración registrada nunca se elimina físicamente; una corrección se registra como una nueva entrada con referencia a la entrada corregida y motivo obligatorio, preservando ambas en el historial.
- **RN-CAL-03**: la próxima fecha de calibración se recalcula automáticamente como `fecha_calibración + frecuencia`; si se registra una nueva calibración, la fecha anterior calculada queda archivada en el historial, no se sobrescribe silenciosamente.
- **RN-CAL-04**: un resultado de calibración "No conforme" genera automáticamente una alerta crítica y sugiere la apertura de un mantenimiento correctivo (no lo abre automáticamente — requiere confirmación humana).

## Documentos

- **RN-DOC-01**: un documento en estado "Vencido" nunca puede mostrarse ni exportarse como "Vigente" bajo ninguna circunstancia, incluso si un usuario administrador intenta forzar el estado manualmente — el estado de vigencia por fecha tiene precedencia sobre cualquier marca manual.
- **RN-DOC-02**: al aprobarse una nueva versión de un documento, la versión anterior pasa automáticamente a "Obsoleta"; nunca pueden coexistir dos versiones "Vigentes" del mismo documento lógico.
- **RN-DOC-03**: un documento eliminado (papelera) puede restaurarse dentro de una ventana configurable (por defecto 30 días); pasado ese plazo, pasa a purga automática programada, no eliminación inmediata silenciosa.
- **RN-DOC-04**: la fecha de vencimiento de un documento debe ser posterior a su fecha de emisión; el sistema rechaza el registro en caso contrario.

## Mantenimientos

- **RN-MANT-01**: al abrir un mantenimiento correctivo, el equipo asociado cambia automáticamente su estado operativo a "Fuera de servicio" o "En mantenimiento" (configurable por tipo); al cerrarlo, vuelve a "Operativo" solo si no existen otros mantenimientos abiertos para el mismo equipo.
- **RN-MANT-02**: no puede cerrarse un mantenimiento sin fecha de ejecución registrada.
- **RN-MANT-03**: el tiempo de inactividad de un equipo se calcula como la suma de los intervalos en que estuvo en estado "Fuera de servicio" o "En mantenimiento" dentro del periodo consultado.

## Alertas

- **RN-ALT-01**: no se genera una alerta duplicada para el mismo evento y el mismo umbral ya notificado (ej. no se repite la alerta preventiva de 30 días una vez ya enviada para esa calibración específica).
- **RN-ALT-02**: una alerta crítica no puede marcarse como "resuelta" automáticamente por el sistema — requiere una acción humana explícita (ej. registrar la calibración pendiente) que la resuelve como efecto secundario, o marcarla manualmente con justificación.

## Usuarios y Permisos

- **RN-USR-01**: un usuario desactivado conserva su historial de auditoría intacto, pero pierde inmediatamente la capacidad de iniciar sesión (invalidación de refresh tokens activos).
- **RN-USR-02**: el rol Administrador no puede autoeliminarse ni autodesactivarse si es el único Administrador activo del laboratorio (evita que un laboratorio quede sin administrador).
- **RN-USR-03**: el correo electrónico de un usuario es único dentro de su laboratorio (tenant), pero la misma persona puede tener cuentas independientes en laboratorios distintos.

## Auditoría

- **RN-AUD-01**: ningún registro de auditoría puede editarse ni eliminarse por ningún rol, incluido Administrador — se aplica a nivel de permisos de base de datos, no solo de aplicación.
- **RN-AUD-02**: toda acción que modifique datos de negocio debe generar exactamente un registro de auditoría; una transacción que falla no debe dejar un registro de auditoría "huérfano" de una acción que no ocurrió realmente.

## Multi-tenancy

- **RN-TEN-01**: ningún dato de un laboratorio es visible ni modificable por usuarios de otro laboratorio, sin excepción, garantizado a nivel de base de datos (Row Level Security) y no solo por lógica de aplicación.
- **RN-TEN-02**: el rol de plataforma "Superadmin" (soporte del operador SaaS) solo puede acceder a datos de un tenant específico con una justificación registrada (número de ticket), y ese acceso queda auditado igual que cualquier otra acción.

## QR

- **RN-QR-01**: el token embebido en un código QR nunca es el identificador incremental interno del equipo (evita enumeración); es un identificador opaco no adivinable.
- **RN-QR-02**: si un equipo se da de baja, su QR sigue siendo escaneable pero la vista pública debe mostrar explícitamente "Equipo dado de baja" en lugar de datos operativos activos.
