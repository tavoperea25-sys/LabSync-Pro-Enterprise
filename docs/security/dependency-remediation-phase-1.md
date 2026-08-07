# Remediación de dependencias — Fase 1 (Grupo B)

**Fecha:** 2026-08-07
**Rama:** `fix/dependencies-phase-1` (creada desde `develop`)

## Objetivo

Corregir exclusivamente las 14 vulnerabilidades clasificadas como **Grupo B** en `docs/security/dependabot-audit-report.md` (`PyJWT`, `python-dotenv`), sin tocar Grupo C, sin alterar React, Vite, pytest, React Router ni esbuild, y sin sacrificar estabilidad.

## Dependencias actualizadas

| Paquete | Archivo | Versión anterior | Versión nueva |
|---|---|---|---|
| `PyJWT` (`pyjwt[crypto]`) | `backend/requirements.txt` (heredado por `requirements-dev.txt` vía `-r`) | `2.10.1` | `2.13.0` |
| `python-dotenv` | `backend/requirements.txt` (heredado por `requirements-dev.txt` vía `-r`) | `1.0.1` | `1.2.2` |

## Versiones anteriores

- `pyjwt[crypto]==2.10.1`
- `python-dotenv==1.0.1`

## Versiones nuevas

- `pyjwt[crypto]==2.13.0`
- `python-dotenv==1.2.2`

## Análisis de impacto (previo a la actualización)

- **PyJWT:** uso en el proyecto limitado a `jwt.encode`/`jwt.decode` con claves RSA estáticas (`backend/app/core/security.py` y 4 archivos más que importan `jwt`/`pyjwt`). No se usa `PyJWKClient` ni `PyJWK` en ningún punto del código — las clases afectadas por varias de las CVEs de SSRF/bypass de algoritmo ni siquiera están en la superficie de uso real del proyecto. Changelog oficial revisado (v2.10.1→v2.13.0): el único cambio "Changed" documentado en ese rango es de empaquetado (migración de extras a dependency groups en 2.13.0), sin impacto en runtime.
- **python-dotenv:** usado únicamente de forma indirecta, vía `pydantic_settings.BaseSettings(env_file=".env")` (`backend/app/core/config.py`) — solo lectura. El único breaking change documentado en 1.2.2 (symlinks ya no seguidos en `set_key`/`unset_key`) es precisamente la corrección de seguridad del CVE, y no afecta al proyecto porque no se llama a `set_key`/`unset_key`/CLI en ningún punto del código (`grep` sin resultados). Compatibilidad confirmada: `pydantic-settings==2.7.0` declara `python-dotenv>=0.21.0`, así que `1.2.2` está dentro del rango soportado.

No se encontró ningún breaking change inesperado. Se procedió con la actualización.

## Vulnerabilidades corregidas

14 alertas (todas las del Grupo B):

| GHSA | Severidad | Paquete | Resumen |
|---|---|---|---|
| GHSA-xgmm-8j9v-c9wx | Alta | PyJWT | JWK de clave pública aceptado como secreto HMAC |
| GHSA-752w-5fwx-jx9f | Alta | PyJWT | Acepta extensiones de header `crit` desconocidas |
| GHSA-993g-76c3-p5m4 | Media | PyJWT | `PyJWKClient` sin allowlist de esquema (SSRF) |
| GHSA-w7vc-732c-9m39 | Media | PyJWT | DoS por decodificación Base64URL sin límite |
| GHSA-jq35-7prp-9v3f | Media | PyJWT | Bypass de allow-list de algoritmo |
| GHSA-fhv5-28vv-h8m8 | Baja | PyJWT | DoS por requests JWKS sin límite |
| GHSA-mf9w-mj56-hr94 | Media | python-dotenv | Symlink following en `set_key` |

*(Cada GHSA cuenta doble en el total de 14 porque Dependabot escanea tanto `backend/requirements.txt` como `backend/requirements-dev.txt`, que apunta al primero vía `-r`.)*

## Validaciones ejecutadas

### Backend

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed! |
| `mypy app` | ✅ Success: no issues found in 183 source files |
| `pytest --cov=app --cov-report=term-missing` | ✅ 352 passed, 6 warnings — cobertura total 95% (sin cambio respecto a la baseline previa) |

### Frontend (sin cambios de dependencias, ejecutado como verificación de que nada se rompió)

| Comando | Resultado |
|---|---|
| `npm install` | ✅ up to date, 403 paquetes |
| `npm run lint` | ✅ sin errores |
| `npm run typecheck` | ✅ sin errores |
| `npm test` | ✅ 121 passed (24 archivos) |
| `npm run build` | ✅ built in 14.79s |

## Resultado de tests

- Backend: **352/352** tests pasando, cobertura **95%** (idéntica a la baseline documentada en `docs/architecture-audit.md`, sin disminución).
- Frontend: **121/121** tests pasando (sin cambios de dependencias en esta fase).

## Estado actual de Dependabot

**Importante:** GitHub calcula las alertas de Dependabot sobre la rama por defecto del repositorio (`main`), no sobre ramas de feature. Confirmado vía `gh api .../dependabot/alerts` inmediatamente antes de este commit: **siguen apareciendo las 35 alertas como `open`**, porque este fix todavía vive únicamente en `fix/dependencies-phase-1` y no se ha fusionado a `main`. El conteo de alertas en GitHub no se actualizará hasta después del merge.

**Comparación proyectada (a nivel de manifiesto, verificada manualmente contra los rangos de versión vulnerable de cada GHSA):**

| Severidad | Antes | Después del merge (proyectado) | Diferencia |
|---|---|---|---|
| Crítica | 1 | 1 | 0 |
| Alta | 14 | 10 | -4 |
| Moderada | 14 | 6 | -8 |
| Baja | 6 | 4 | -2 |
| **Total** | **35** | **21** | **-14 (-40.0%)** |

## Riesgos pendientes

Las 21 alertas del Grupo C permanecen sin tocar, tal como exige esta fase: `cryptography` (7 únicas), `vitest` (1 crítica, arrastra 4 más), `react-router` (1 alta, transitiva), `pytest` (1 moderada). Ver `docs/security/dependabot-audit-report.md` para el detalle completo y el plan de remediación propuesto para cada una.

## Próximos pasos

1. Abrir PR de `fix/dependencies-phase-1` hacia `develop` (Fase 9 de este mismo proceso).
2. Tras el merge a `develop` y eventualmente a `main`, volver a consultar `gh api .../dependabot/alerts` para confirmar que las 14 alertas pasan a estado `dismissed`/`fixed` y que el conteo real coincide con la proyección de esta tabla.
3. Planificar una Fase 2 de remediación dedicada al Grupo C, con ramas y pruebas de regresión propias por paquete (ver recomendaciones en `docs/security/dependabot-audit-report.md`).
