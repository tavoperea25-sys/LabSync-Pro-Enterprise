# Remediación de dependencias — `cryptography` (Grupo C)

**Fecha:** 2026-08-07
**Rama:** `fix/dependencies-cryptography` (creada desde `develop`)

## Objetivo

Corregir las 14 vulnerabilidades asociadas a `cryptography` (7 GHSA únicos, clasificadas en Grupo C en `docs/security/dependabot-audit-report.md`), sin tocar ninguna otra dependencia del Grupo C (`pytest`, `vitest`, `vite`, `esbuild`, `react-router`) ni del ecosistema JavaScript.

## Versión anterior

`cryptography==44.0.0`

## Versión nueva

`cryptography==50.0.0`

Confirmada como la versión recomendada por Dependabot (mayor `first_patched_version` entre las 7 alertas: `GHSA-g6cj-pr64-35w5` exige `50.0.0`) y como la última release publicada en PyPI en el momento de esta fase.

## Análisis de impacto (previo a la actualización)

**Único punto de uso de `cryptography` en el proyecto:** `backend/app/core/security.py`, líneas 22-23 — `from cryptography.hazmat.primitives import serialization` y `from cryptography.hazmat.primitives.asymmetric import rsa`, usados exclusivamente para generar el par de llaves RSA de desarrollo (`rsa.generate_private_key`) y serializarlas en PEM/PKCS8 estándar (`private_bytes`/`public_bytes`).

**Breaking changes revisados en el CHANGELOG oficial (44.0.0 → 50.0.0), ninguno aplicable a este uso:**

| Versión | Cambio | ¿Aplica? |
|---|---|---|
| 45.0.0 | Carga de llaves SSH lanza `TypeError` en vez de `ValueError` en ciertos casos | No — no se cargan llaves SSH |
| 46.0.0 | Python 3.7 sin soporte; `CAST5`/`SEED`/`IDEA`/`Blowfish` movidos a `decrepit` | No — proyecto en Python 3.11/3.12; esos cifrados no se usan |
| 47.0.0 | Curvas SECT eliminadas; OpenSSL 1.1.x sin soporte (requiere ≥3.0); `CFB`/`OFB`/`CFB8`/`Camellia` movidos a `decrepit`; `public_bytes`/`private_bytes` lanzan `TypeError` (no `ValueError`) en encodings inválidos | No — no se usan curvas SECT ni esos modos/cifrados; los parámetros de encoding usados (PEM + PKCS8/SubjectPublicKeyInfo) son válidos |
| 48.0.0 | Python 3.8 sin soporte; validación más estricta de CRL X.509 | No — Python ≥3.9 cumplido; no se parsean/validan certificados X.509 |
| 49.0.0 | Alias de tipos deprecados eliminados (`PUBLIC_KEY_TYPES`, etc.); cambios en manejo de nonce de ChaCha20; validación más estricta de firmas X.509 (ECDSA/DSA con NULL) | No — no se usan esos alias, ChaCha20, ni parsing de certificados X.509 |
| 50.0.0 | Sin cambios incompatibles documentados | — |

**Conclusión del análisis:** pese a ser un salto "mayor" en el número de versión (44→50), el riesgo real para este proyecto es bajo — la superficie de uso real (generación RSA + serialización PEM/PKCS8 estándar) no se ve afectada por ninguno de los breaking changes documentados. Se procedió con la actualización, validando con la suite completa de tests como confirmación final.

## Cambios realizados

- `backend/requirements.txt`: `cryptography==44.0.0` → `cryptography==50.0.0`. Ningún otro paquete modificado (`pyjwt`, `python-dotenv` permanecen en las versiones de `develop`, ya que esta rama parte de `develop` y no incluye el fix del Grupo B, todavía en PR #5 separado).
- Ningún cambio de código funcional — no fue necesario, tal como anticipaba el análisis de impacto.

## Resultado de pruebas

### Backend

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed! |
| `mypy app` | ✅ Success: no issues found in 183 source files |
| `pytest --cov=app --cov-report=term-missing` | ✅ 352 passed, 6 warnings — cobertura 95% (idéntica a la baseline, sin regresión) |

### Frontend (sin cambios, verificación de que nada se rompió)

| Comando | Resultado |
|---|---|
| `npm install` | ✅ |
| `npm run lint` | ✅ Sin errores |
| `npm run typecheck` | ✅ Sin errores |
| `npm test` | ✅ 121 passed (24 archivos) |
| `npm run build` | ✅ built in 17.47s |

## Resultado de Dependabot

GitHub sigue reportando **35 alertas abiertas** (14 de `cryptography` incluidas) porque las alertas se calculan sobre la rama por defecto (`main`), y este cambio vive únicamente en `fix/dependencies-cryptography`, sin fusionar. Confirmado vía `gh api .../dependabot/alerts` inmediatamente después del push.

**Proyección tras el merge** (verificada manualmente contra los rangos de versión vulnerable, no es una lectura en vivo):

| Severidad | Antes de este fix | Después (proyectado) | Diferencia |
|---|---|---|---|
| Crítica | 1 | 1 | 0 |
| Alta | 14 | 6 | -8 |
| Moderada | 14 | 12 | -2 |
| Baja | 6 | 2 | -4 |
| **Total** | **35** | **21** | **-14 (-40.0%)** |

(Este PR es independiente del PR #5 del Grupo B; si ambos se fusionan, el efecto combinado dejaría el total en 35-14-14=7 alertas, todas del resto del Grupo C: `vitest`, `vite`/`esbuild` anidados, `react-router`, `pytest`.)

## Riesgos pendientes

El resto del Grupo C permanece sin tocar, según lo exigido por esta fase: `vitest` (2.1.9, incluye la única alerta crítica), `vite`/`esbuild` anidados (dependen del bump de `vitest`), `react-router` (transitiva, requiere subir `react-router-dom` a la línea 8.x), `pytest` (8.3.4 → 9.0.3). Cada uno requiere su propia fase de remediación dedicada.

## Recomendaciones

1. Revisar y aprobar este PR de forma independiente al PR #5 (Grupo B) — ambos son cambios pequeños y aislados, pensados para revisarse por separado.
2. Tras fusionar ambos a `main`, volver a consultar `gh api .../dependabot/alerts` para confirmar que el conteo real baja a 7 alertas restantes.
3. Planificar la remediación del resto del Grupo C como fases independientes adicionales, priorizando `vitest` (por la alerta crítica) en una rama aislada con validación completa de los 121 tests de frontend.
