# Política de seguridad

## Reportar una vulnerabilidad

Si encuentras una vulnerabilidad de seguridad en este proyecto, **no la reportes como un issue público**. Repórtala de forma privada:

<!-- TODO: reemplazar por el canal real de contacto (correo de seguridad,
     GitHub Security Advisories, u otro) antes de la primera publicación. -->
- Canal de contacto: _pendiente de definir_.

Incluye, en la medida de lo posible:

- Descripción del problema y su impacto potencial.
- Pasos para reproducirlo.
- Versión/commit afectado.

## Qué esperar

- Confirmación de recepción en un plazo razonable.
- Evaluación de severidad y, si aplica, coordinación de una corrección antes de cualquier divulgación pública.
- No se tomarán acciones legales contra quien reporte una vulnerabilidad de buena fe, siguiendo este proceso.

## Alcance

Este proyecto es un sistema multi-tenant que maneja datos operativos de laboratorios clínicos. Se consideran de especial interés (pero no exclusivo):

- Fallos de aislamiento entre tenants (laboratorios).
- Bypass de autenticación o autorización.
- Exposición de credenciales, tokens o archivos no autorizados.
- Inyección (SQL, XSS, o de cualquier otro tipo).

## Versiones soportadas

Al ser un proyecto en fase de Release Candidate, actualmente solo la rama `main` recibe atención de seguridad activa.
