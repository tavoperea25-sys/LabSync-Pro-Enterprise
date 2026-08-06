# 16 — Estrategia de Seguridad

---

## 1. Autenticación

- **JWT de acceso**: 15 minutos de vida, firmado (RS256), contiene `sub` (usuario), `laboratorio_id`, `roles`, `exp`.
- **Refresh token**: 7 días, rotativo (cada uso emite uno nuevo e invalida el anterior), almacenado como cookie `httpOnly` + `secure` + `SameSite=strict` — nunca accesible desde JavaScript del cliente (mitiga robo vía XSS).
- **Detección de reuso de refresh token**: si un refresh token ya rotado se presenta de nuevo (indicio de robo), se revocan todas las sesiones activas de ese usuario y se le notifica.
- **Bloqueo progresivo**: 5 intentos fallidos → bloqueo de 1 minuto; se duplica en cada ciclo adicional hasta un máximo, reseteable solo por flujo de recuperación de contraseña o por un Administrador.
- **MFA**: modelo de datos preparado (`usuarios.mfa_habilitado`), flujo de UI diferido a fase posterior (ver `17-roadmap.md`).

## 2. Autorización (RBAC)

- Roles y permisos modelados como relación granular (`roles_permisos`, ver `14-base-de-datos.md`), no como `if rol == "admin"` disperso en el código.
- Verificación de permiso en cada endpoint del backend (dependency de FastAPI) — el frontend oculta controles por UX, pero la autorización real siempre se re-verifica en el servidor.
- Separación explícita de permisos sensibles: `usuarios.leer_pii` es distinto de `equipos.leer`, de forma que un Técnico con acceso operativo amplio no pueda, por defecto, exportar la base completa de usuarios.
- El rol `Superadmin` (plataforma, soporte del operador SaaS) es un rol **separado** de los roles de laboratorio, sin pertenecer a ningún tenant, y su uso requiere justificación registrada (número de ticket) — RN-TEN-02.

## 3. Aislamiento multi-tenant

- Row Level Security de PostgreSQL como barrera de último recurso (ver `14-base-de-datos.md` sección 3) — no se confía únicamente en que cada query de aplicación incluya el filtro de tenant correctamente.
- `laboratorio_id` se deriva siempre del JWT validado en el servidor, nunca de un parámetro de la URL/body controlable por el cliente.
- **Criterio de aceptación no negociable**: suite de pruebas automatizadas que, para cada endpoint, verifica que un usuario del tenant A recibe 403/404 al intentar acceder a un recurso del tenant B — gate obligatorio de CI (ver `19-checklist.md`).

## 4. Protección de contraseñas

- Hash con **Argon2id** (parámetros de costo ajustados a hardware de producción, revisados anualmente).
- Política de complejidad configurable por laboratorio (longitud mínima 10, combinación de tipos de carácter) vía `configuraciones_laboratorio.politica_password_json`.
- Cambio de contraseña obligatorio en primer inicio de sesión (RF-USR-04).
- Nunca se registra la contraseña en texto plano en ningún log, ni siquiera en logs de depuración (middleware de sanitización de logs).

## 5. Transporte y almacenamiento

- HTTPS/TLS 1.2+ obligatorio en todo el tráfico (RNF-SEC-01); HTTP redirige a HTTPS a nivel de Nginx, nunca se sirve contenido sensible sobre HTTP.
- Documentos en MinIO cifrados en reposo (SSE), acceso exclusivamente vía URLs prefirmadas de corta duración — nunca URLs públicas permanentes ni acceso directo al bucket.
- Backups de base de datos cifrados y almacenados fuera del mismo host que la base de datos primaria.

## 6. Protección de la capa web

- **CORS**: lista blanca explícita de orígenes permitidos (dominio de la aplicación), nunca `*` en producción.
- **CSRF**: mitigado por `SameSite=strict` en la cookie de refresh token + verificación de origen en operaciones de estado; los endpoints autenticados por `Authorization: Bearer` (no cookie) no son susceptibles a CSRF clásico.
- **Rate limiting**: por IP y por usuario en `/auth/login`, `/auth/recuperar-password` y en el endpoint público de incidencias QR (superficie de abuso sin autenticación).
- **Validación de entrada**: Pydantic v2 en el límite de cada endpoint; ninguna validación de negocio se confía únicamente al frontend (RNF-SEC-05).
- **Cabeceras de seguridad**: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, `X-Frame-Options: DENY` (salvo la vista pública QR, que se evalúa aparte por su naturaleza embebible).

## 7. Auditoría como control de seguridad

- Todo intento de acceso denegado por autorización (403) se registra en auditoría — permite detectar patrones de intento de acceso indebido, no solo acciones exitosas.
- El log de auditoría es append-only a nivel de permisos de base de datos (ver `14-base-de-datos.md`), inaccesible a `UPDATE`/`DELETE` incluso para el rol de aplicación con privilegios de Administrador.

## 8. Gestión de sesiones

- Un usuario puede ver y cerrar remotamente sus sesiones activas (RF-USR-06).
- Desactivar un usuario invalida inmediatamente todos sus refresh tokens activos (RN-USR-01).

## 9. Seguridad en integraciones futuras (preparación, no implementación v1)

- API pública versionada: autenticación por API key con scopes granulares (no el mismo JWT de usuario), diseño reservado para cuando se habilite (`17-roadmap.md`).
- Webhooks salientes firmados (HMAC) para que el receptor pueda verificar autenticidad del payload.

## 10. Respuesta a incidentes (mínimo viable para v1)

- Procedimiento documentado de revocación masiva de sesiones (ante sospecha de compromiso de un tenant o de la plataforma completa).
- Backups verificados con restauración de prueba trimestral (RNF-BKP-03) como parte del plan de continuidad.
