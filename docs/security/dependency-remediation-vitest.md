# Remediación de dependencias — `vitest` (Grupo C)

**Fecha:** 2026-08-07
**Rama:** `fix/dependencies-vitest-group-c` (creada desde `develop`)

## Objetivo

Corregir la única alerta **crítica** de Dependabot (`vitest`, GHSA-5xrq-8626-4rwp) y las 4 alertas que arrastra por venir empaquetadas dentro de `vitest` 2.x (`vite`/`esbuild` anidados vía `vite-node`), sin tocar ningún otro paquete del Grupo C (`cryptography` ya remediado en fase aparte; `react-router`, `pytest` siguen pendientes) ni del backend.

## Versión anterior

`vitest@^2.1.8` (resuelto en el lockfile a `2.1.9`)

## Versión nueva

`vitest@^3.2.6` (resuelto en el lockfile a `3.2.7` — el caret sigue el mismo estilo que el resto de `devDependencies` del proyecto; `3.2.7` cumple y supera el mínimo corregido `3.2.6` de la alerta)

## Vulnerabilidades corregidas

| GHSA / CVE | Severidad | Paquete | Resumen |
|---|---|---|---|
| [GHSA-5xrq-8626-4rwp](https://github.com/advisories/GHSA-5xrq-8626-4rwp) / CVE-2026-47429 | **Crítica** | vitest | Con el servidor UI de Vitest activo, se puede leer y ejecutar un archivo arbitrario |
| [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff) / CVE-2026-53571 | Alta | vite (anidado en `vite-node`, copia interna de vitest 2.x) | Bypass de `server.fs.deny` en rutas alternas de Windows |
| GHSA-v6wh-96g9-6wx3 / CVE-2026-53632 | Moderada | vite (anidado) | Divulgación de hash NTLMv2 vía manejo de rutas UNC en Windows |
| GHSA-4w7w-66w2-5vf9 | Moderada | vite (anidado) | Path traversal en manejo de `.map` de deps optimizadas |
| GHSA-67mh-4wv8-2f99 | Moderada | esbuild (anidado en `vite-node`) | El servidor de desarrollo acepta requests y expone respuestas a cualquier sitio |

Las 4 últimas no son alertas de `vite`/`esbuild` como dependencias directas — el proyecto ya usaba `vite@6.4.3` y `esbuild@0.25.12` en el nivel superior (`frontend/package.json`), ambos ya parcheados. Eran copias vulnerables **anidadas dentro de `vitest@2.1.9`**, vía su dependencia interna `vite-node@2.1.9` (que traía su propio `vite@5.4.21` y `esbuild@0.21.5`, sin relación con las versiones de nivel superior).

## Análisis de impacto (previo a la actualización)

**Riesgo real de la alerta crítica confirmado como bajo incluso antes del fix:** el servidor UI de Vitest (`vitest --ui`) es la única vía de explotación de GHSA-5xrq-8626-4rwp, y no se usa en este proyecto — `frontend/package.json` define `"test": "vitest run"` (modo CLI, sin UI), y `.github/workflows/ci.yml` ejecuta ese mismo script. La corrección igual se aplicó de inmediato por ser la única alerta crítica del repo.

**Superficie de uso real de vitest revisada antes del bump:**

- Sin `vitest.workspace.ts` ni configuración de `browser` en `vite.config.ts` — no aplica la eliminación de `browser.name`/`browser.providerOptions` (Vitest 3.0).
- Sin archivos `.snap` en el repo (`find src -iname "*.snap"` sin resultados) — no aplica el cambio de formato/API de snapshots.
- Sin uso de `coverage.excludes` ni `@vitest/coverage-*` como dependencia — el proyecto no corre `--coverage` en frontend, no aplica el cambio de exclusión forzada de archivos de test.
- Sin imports de `vitest/reporters` en el código del proyecto — no aplica el cambio de qué tipos exporta ese entrypoint.
- `grep` sin resultados para `mockReset(` — no aplica el cambio de comportamiento de `spy.mockReset()` (ahora restaura la implementación original en vez de crear un noop).
- Un solo archivo usa fake timers ([src/shared/hooks/useDebouncedValue.test.ts](../../frontend/src/shared/hooks/useDebouncedValue.test.ts)), y solo con `vi.advanceTimersByTime` sobre un `setTimeout` — no depende de `performance.now()`, así que el cambio de Vitest 3 (fake timers ahora mockea también `performance.now()` por defecto) no lo afecta.
- 17 archivos usan `vi.mock`/`vi.hoisted`/`vi.spyOn` — la API de mocking no cambió de forma incompatible entre 2.x y 3.x según el [changelog oficial](https://vitest.dev/guide/migration.html); confirmado en la práctica corriendo la suite completa (ver más abajo).
- Sin uso del tercer argumento de `test()`/`describe()` como objeto de opciones (el único cambio con warning en consola de Vitest 3.0) — todos los `it(...)`/`describe(...)` del proyecto usan la forma de 2 argumentos.

No se encontró ningún breaking change de la [guía de migración oficial](https://v3.vitest.dev/guide/migration) aplicable a este proyecto. Se procedió con la actualización.

## Cambios realizados

- `frontend/package.json`: `"vitest": "^2.1.8"` → `"vitest": "^3.2.6"`. Ningún otro paquete tocado a mano — `npm install` resolvió `vite-node` a una versión que ya no trae su propio `vite`/`esbuild` anidados, sino que reutiliza los de nivel superior (ya parcheados).
- `frontend/package-lock.json`: regenerado por `npm install`.
- Ningún cambio de código de la aplicación ni de `vite.config.ts` — no fue necesario.

## Resultado de pruebas

| Comando | Resultado |
|---|---|
| `npm run lint` | ✅ Sin errores ni warnings |
| `npm run typecheck` | ✅ Sin errores |
| `npm test` (`vitest run`) | ✅ 121 passed (24 archivos) — mismo resultado que antes del bump |
| `npm run build` | ✅ built in 18.29s |
| Backend | Sin cambios — no aplica |

## Resultado de `npm audit`

Antes del bump, `npm audit` reportaba las vulnerabilidades de vitest/vite/esbuild anidados entre sus hallazgos. Después del bump:

```
react-router  7.12.0 - 8.2.0
Severity: high
React Router: RSC Mode CSRF Bypass Allows Action Execution Before 400 Response
2 high severity vulnerabilities
```

Solo queda la alerta de `react-router`/`react-router-dom` — exactamente la que este cambio **no** debía tocar (Grupo C, remediación separada pendiente). Confirmado también inspeccionando `package-lock.json`: ya no existe ningún `vite`/`esbuild` anidado en `node_modules/vite-node/node_modules/*`.

## Resultado de Dependabot

Confirmado vía `gh api .../dependabot/alerts` en vivo, justo antes de este commit: **siguen las 35 alertas originales, sin cambio** (1 crítica, 14 altas, 14 moderadas, 6 bajas — idéntico al primer reporte). Esto es esperado y consistente con lo ya documentado en las fases anteriores: Dependabot calcula el conteo sobre la rama por defecto del repositorio (`main`), y ni esta fase ni las dos anteriores (Grupo B — PR #5, `cryptography` — PR #6) se han fusionado a `main` todavía, solo a `develop`. El conteo real de GitHub no bajará hasta que `develop` (o esta rama, directamente) llegue a `main`.

**Proyección de esta fase por sí sola** (contra la base real de 35, verificada manualmente contra los rangos de versión vulnerable de cada GHSA — no es una lectura en vivo):

| Severidad | Antes de este fix | Después (proyectado) | Diferencia |
|---|---|---|---|
| Crítica | 1 | 0 | -1 |
| Alta | 14 | 13 | -1 (`vite` anidado, GHSA-fx2h-pf6j-xcff) |
| Moderada | 14 | 11 | -3 (`vite` x2 + `esbuild` anidados) |
| Baja | 6 | 6 | 0 |
| **Total** | **35** | **30** | **-5 (-14.3%)** |

**Proyectado una vez que también lleguen a `main` el Grupo B y `cryptography`** (ya fusionados a `develop`, PRs #5 y #6): 35 − 14 (Grupo B) − 14 (`cryptography`, 7 únicas × 2 manifiestos) − 5 (esta fase) = **2 alertas restantes** (`react-router` alta + `pytest` moderada), una vez que `develop` llegue a `main`.

## Riesgos pendientes

Quedan 16 alertas del Grupo C sin tocar, tal como exige esta fase: `react-router` (transitiva vía `react-router-dom`, 1 alta — requiere subir a la línea 8.x, cambio mayor de la librería de rutas de toda la SPA) y `pytest` (backend, 1 moderada — major bump 8→9, riesgo sobre fixtures/plugins de los 352 tests). Cada uno requiere su propia fase de remediación dedicada.

## Recomendaciones

1. Revisar y aprobar este PR de forma independiente.
2. Tras fusionar, volver a consultar `gh api .../dependabot/alerts` para confirmar que el conteo real baja a 16 alertas restantes.
3. Planificar `react-router` como la siguiente fase (alta severidad, pero cambio mayor — requiere pruebas manuales de navegación completas de la SPA), y `pytest` después (menor impacto de severidad, pero también major bump).
