# Informe final — Remediación de dependencias, Fase 1 (Grupo B)

**Fecha:** 2026-08-07
**Rama:** `fix/dependencies-phase-1`
**Pull Request:** https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/5 (`fix/dependencies-phase-1` → `develop`, sin mergear)

## Resumen ejecutivo

Se corrigieron las 14 vulnerabilidades del Grupo B identificadas en `docs/security/dependabot-audit-report.md`, actualizando únicamente `PyJWT` (2.10.1 → 2.13.0) y `python-dotenv` (1.0.1 → 1.2.2) en `backend/requirements.txt`. Ambas actualizaciones se analizaron contra su changelog oficial y el uso real del código antes de aplicarse; ninguna introdujo un breaking change relevante para este proyecto. La suite completa de backend (352 tests, 95% cobertura) y frontend (121 tests, lint, typecheck, build) pasa sin regresiones. El Grupo C (21 alertas restantes) permanece completamente intacto, tal como exigía el alcance de esta fase.

## Dependencias modificadas

| Paquete | Versión anterior | Versión nueva | Tipo de cambio (semver) |
|---|---|---|---|
| `pyjwt[crypto]` | 2.10.1 | 2.13.0 | Menor (2.10 → 2.13) |
| `python-dotenv` | 1.0.1 | 1.2.2 | Menor (1.0 → 1.2) |

Archivo modificado: `backend/requirements.txt` (1 archivo, 2 líneas). `backend/requirements-dev.txt` no requirió cambios propios — hereda ambos paquetes vía `-r requirements.txt`.

## Tests ejecutados

| Suite | Comando | Resultado |
|---|---|---|
| Backend | `pytest --cov=app --cov-report=term-missing` | ✅ 352 passed, 6 warnings |
| Frontend | `npm test` | ✅ 121 passed (24 archivos) |

## Cobertura

**95%** (backend) — sin cambio respecto a la baseline documentada en `docs/architecture-audit.md`. Ninguna línea perdió cobertura a causa de esta actualización.

## Lint

| Herramienta | Resultado |
|---|---|
| `ruff check .` (backend) | ✅ All checks passed! |
| `npm run lint` (frontend) | ✅ Sin errores ni warnings |

## Build

| Comando | Resultado |
|---|---|
| `mypy app` (backend, type-check) | ✅ Success: no issues found in 183 source files |
| `npm run typecheck` (frontend) | ✅ Sin errores |
| `npm run build` (frontend) | ✅ built in 14.79s |

## Dependabot antes

35 alertas abiertas: 1 crítica, 14 altas, 14 moderadas, 6 bajas (verificado vía `gh api .../dependabot/alerts` sobre la rama por defecto `main`).

## Dependabot después

**Sin cambio todavía en el contador real de GitHub** — las alertas de Dependabot se calculan sobre la rama por defecto (`main`), y este fix vive únicamente en `fix/dependencies-phase-1`, sin mergear a `develop` ni a `main`. Se confirmó explícitamente después del push que GitHub sigue reportando 35 alertas abiertas.

Proyección verificada manualmente contra los rangos de versión vulnerable de cada GHSA (no es una lectura en vivo de GitHub, sino el resultado esperado una vez que este cambio llegue a `main`):

| Severidad | Antes | Después (proyectado) | Diferencia |
|---|---|---|---|
| Crítica | 1 | 1 | 0 |
| Alta | 14 | 10 | -4 |
| Moderada | 14 | 6 | -8 |
| Baja | 6 | 4 | -2 |
| **Total** | **35** | **21** | **-14 (-40.0%)** |

Verificación pendiente tras el merge: volver a consultar `gh api .../dependabot/alerts` y confirmar que el conteo real coincide con esta proyección.

## Riesgos pendientes

- **Grupo C intacto (21 alertas)** — `cryptography` (44.0.0, 7 alertas únicas), `vitest` (2.1.9, incluye la única crítica), `react-router` (transitiva, 1 alta), `pytest` (8.3.4, 1 moderada). Cada uno requiere su propia fase de remediación con pruebas de regresión dedicadas, según lo documentado en `docs/security/dependabot-audit-report.md`.
- **Este PR no está mergeado.** Hasta que se apruebe y fusione a `develop` (y eventualmente a `main`), las 14 correcciones no tienen efecto en el estado de seguridad real del branch por defecto.

## Recomendaciones

1. Revisar y aprobar el PR #5 (`fix/dependencies-phase-1` → `develop`).
2. Tras el merge, verificar en vivo que las 14 alertas correspondientes pasan a `dismissed`/resuelto en GitHub.
3. Planificar la Fase 2 de remediación (Grupo C) como trabajo separado, empezando por `cryptography` (mayor superficie en producción: JWT RS256) y evaluando `vitest` en una rama aislada antes de tocar la única alerta crítica restante.
