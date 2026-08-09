# Auditoría Dependabot — LabSync Pro Enterprise

**Fecha:** 2026-08-06 (nota: la corrida de Dependabot que originó estas 35 alertas fue posterior a las fechas de fases anteriores registradas en este repositorio)
**Fuente:** `gh api repos/tavoperea25-sys/LabSync-Pro-Enterprise/dependabot/alerts` (35 alertas reales, obtenidas directamente de GitHub, no simuladas).

---

## ✅ Estado final (actualizado 2026-08-07): 0 alertas abiertas

Las 35 alertas descritas en esta auditoría (punto de partida, ver "Resumen ejecutivo" y tabla completa más abajo) quedaron **todas resueltas**, confirmado en vivo con `gh api .../dependabot/alerts` contra `main` tras la última fusión. El resto del documento se conserva sin modificar como registro histórico del análisis original — esta sección solo añade el desenlace.

Requisito previo, no anticipado en el análisis original: el gate de aislamiento multi-tenant de CI (RLS) estaba deshabilitado en silencio desde el primer commit del repo (rol de Postgres equivocado en `ci.yml`), y CI nunca había pasado en verde. Sin arreglar eso primero, ninguna de las fases siguientes hubiera tenido una señal de CI confiable — ver [fix(ci) #7](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/7).

| Grupo | Paquete(s) | Alertas cerradas | PR → `develop` | PR → `main` | Detalle |
|---|---|---|---|---|---|
| B | `PyJWT`, `python-dotenv` | 14 | [#5](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/5) | [#9](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/9) | [dependency-remediation-phase-1.md](dependency-remediation-phase-1.md) |
| C | `cryptography` | 14 | [#6](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/6) | [#9](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/9) | [dependency-remediation-cryptography.md](dependency-remediation-cryptography.md) |
| C | `vitest` (+ vite/esbuild anidados) | 5 (incl. la crítica) | [#8](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/8) | [#36](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/36) | [dependency-remediation-vitest.md](dependency-remediation-vitest.md) |
| C | `react-router` (react-router-dom → react-router v8) | 1 | [#35](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/35) | [#36](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/36) | [dependency-remediation-react-router.md](dependency-remediation-react-router.md) |
| C | `pytest` | 1 | [#37](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/37) | [#38](https://github.com/tavoperea25-sys/LabSync-Pro-Enterprise/pull/38) | [dependency-remediation-pytest.md](dependency-remediation-pytest.md) |
| — | **Total** | **35** | | | |

Cada fase se verificó de forma independiente (lint, typecheck, suite completa de tests, y en el caso de `react-router`, además una pasada manual de navegación en navegador real contra el backend real) antes de fusionarse — no se aplicó ningún bump "a ciegas" pese a que casi todo el Grupo C eran saltos de versión mayor. El detalle de análisis de impacto de cada paquete está en su propio documento (tabla de arriba).

**Nota de proceso, para la próxima vez:** Dependabot calcula su conteo de alertas sobre la rama por defecto (`main`), no sobre `develop` — cada fase de esta serie requirió un PR adicional de promoción `develop` → `main` para que el cierre se reflejara realmente en GitHub. Fusionar solo a `develop` no mueve el contador aunque el código ya esté corregido.

## Estado de GitHub Projects — actualización

Sigue sin resolverse (ver sección original más abajo, sin cambios): el token de `gh` no tiene el scope `project`. No bloqueó nada de esta serie de remediación, que se gestionó enteramente vía PRs normales.

---

## Resumen ejecutivo

GitHub detectó 35 alertas de Dependabot: **1 crítica, 14 altas, 14 moderadas, 6 bajas**, repartidas en 8 paquetes distintos (4 backend, 4 frontend). Los números de esta auditoría reconcilian exactamente con el resumen de GitHub.

**Hallazgo principal de esta auditoría: el Grupo A (actualización segura, sin cambio de versión menor o mayor) está vacío.** Ninguna de las 35 alertas tiene una corrección disponible que sea un simple parche dentro del mismo `major.minor` ya instalado — todas requieren al menos un salto de versión **menor**, y las más severas (incluida la única crítica) requieren un salto de versión **mayor**. Por esta razón, siguiendo la regla explícita de esta fase ("Aplicar solamente Grupo A"), **no se aplicó ninguna actualización de dependencias de forma automática** — hacerlo hubiera violado la regla de "no actualizar dependencias a ciegas" y el objetivo de no sacrificar estabilidad.

Todas las alertas tienen una versión corregida disponible (Grupo D — "sin solución disponible" — está vacío).

## Tabla completa de vulnerabilidades

### Crítica (1)

| # | Paquete | Ecosistema | Archivo | Tipo | GHSA / CVE | Instalada | Corregida | Resumen |
|---|---|---|---|---|---|---|---|---|
| 32 | vitest | npm | frontend/package-lock.json | Directa (dev) | [GHSA-5xrq-8626-4rwp](https://github.com/advisories/GHSA-5xrq-8626-4rwp) / CVE-2026-47429 | 2.1.9 | 3.2.6 | Con el servidor UI de Vitest activo, se puede leer y ejecutar un archivo arbitrario |

### Alta (14)

| # | Paquete | Ecosistema | Archivo | Tipo | GHSA / CVE | Instalada | Corregida | Resumen |
|---|---|---|---|---|---|---|---|---|
| 35 | react-router | npm | frontend/package-lock.json | Transitiva (vía react-router-dom) | [GHSA-qwww-vcr4-c8h2](https://github.com/advisories/GHSA-qwww-vcr4-c8h2) | 7.18.2 | 8.3.0 | Bypass de CSRF en modo RSC permite ejecutar una acción antes de la respuesta 400 |
| 33 | vite | npm | frontend/package-lock.json | Transitiva (copia interna de vitest 2.x) | [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff) / CVE-2026-53571 | 5.4.21 (anidada) | 6.4.3 | Bypass de `server.fs.deny` en rutas alternas de Windows |
| 28, 22, 14, 8 | pyjwt/PyJWT | pip | backend/requirements.txt, backend/requirements-dev.txt | Directa | [GHSA-xgmm-8j9v-c9wx](https://github.com/advisories/GHSA-xgmm-8j9v-c9wx) / CVE-2026-48526 | 2.10.1 | 2.13.0 | JWK de clave pública aceptada como secreto HMAC — permite forjar tokens HS256 |
| 27, 21, 13, 7 | PyJWT | pip | backend/requirements.txt, backend/requirements-dev.txt | Directa | [GHSA-752w-5fwx-jx9f](https://github.com/advisories/GHSA-752w-5fwx-jx9f) / CVE-2026-32597 | 2.10.1 | 2.12.0 | PyJWT acepta extensiones de header `crit` desconocidas |
| 26, 20, 12, 4 | cryptography | pip | backend/requirements.txt, backend/requirements-dev.txt | Directa | [GHSA-537c-gmf6-5ccf](https://github.com/advisories/GHSA-537c-gmf6-5ccf) | 44.0.0 | 48.0.1 | OpenSSL vulnerable incluido en los wheels de cryptography |
| 19, 17, 9, ... | cryptography | pip | backend/requirements.txt, backend/requirements-dev.txt | Directa | [GHSA-r6ph-v2qm-q3c2](https://github.com/advisories/GHSA-r6ph-v2qm-q3c2) / CVE-2026-26007 | 44.0.0 | 46.0.5 | Falta validación de subgrupo en curvas SECT — vulnerable a ataque de subgrupo |
| 28... | cryptography | pip | backend/requirements.txt, backend/requirements-dev.txt | Directa | [GHSA-jwv3-5hgf-82ww](https://github.com/advisories/GHSA-jwv3-5hgf-82ww) / CVE-2026-69249 | 44.0.0 | 49.0.0 | Intermedios autofirmados duplicados causan construcción de ruta exponencial |
| 27... | cryptography | pip | backend/requirements.txt, backend/requirements-dev.txt | Directa | [GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5) / CVE-2026-69247 | 44.0.0 | 50.0.0 | Oráculo de Bleichenbacher en desencriptación PKCS#7 EnvelopedData |

*(Nota de formato: `cryptography` y `PyJWT` generan alertas duplicadas entre `backend/requirements.txt` y `backend/requirements-dev.txt` porque este último incluye al primero vía `-r requirements.txt` — son el mismo paquete/versión instalada, contados dos veces por Dependabot al escanear ambos manifiestos. Se consolidan por claridad; el conteo total de 35 sí corresponde a las alertas individuales reales de GitHub.)*

### Moderada (14)

| Paquete | Ecosistema | Tipo | GHSA / CVE | Instalada | Corregida | Resumen |
|---|---|---|---|---|---|---|
| vite | npm | Transitiva (vitest 2.x) | GHSA-v6wh-96g9-6wx3 / CVE-2026-53632 | 5.4.21 (anidada) | 6.4.3 | Divulgación de hash NTLMv2 vía manejo de rutas UNC en Windows (launch-editor) |
| vite | npm | Transitiva (vitest 2.x) | GHSA-4w7w-66w2-5vf9 | 5.4.21 (anidada) | 6.4.2 | Path traversal en manejo de `.map` de deps optimizadas |
| esbuild | npm | Transitiva (vitest 2.x) | GHSA-67mh-4wv8-2f99 | 0.21.5 (anidada) | 0.25.0 | El servidor de desarrollo acepta requests y expone respuestas a cualquier sitio |
| cryptography | pip | Directa | GHSA-m2h6-j472-rp4c / CVE-2026-69248 | 44.0.0 | 49.0.0 | Verificador acepta nombres DNS wildcard, permitiendo escapar de `permittedSubtrees` |
| PyJWT | pip | Directa | GHSA-993g-76c3-p5m4 / CVE-2026-48522 | 2.10.1 | 2.13.0 | `PyJWKClient` sin allowlist de esquema — SSRF + forja de token vía `file://`/`ftp://`/`data:` |
| PyJWT | pip | Directa | GHSA-w7vc-732c-9m39 / CVE-2026-48525 | 2.10.1 | 2.13.0 | DoS no autenticado por decodificación Base64URL sin límite en JWS detached |
| PyJWT | pip | Directa | GHSA-jq35-7prp-9v3f / CVE-2026-48523 | 2.10.1 | 2.13.0 | Bypass de allow-list de algoritmo al decodificar con claves `PyJWK`/`PyJWKClient` |
| python-dotenv | pip | Directa | GHSA-mf9w-mj56-hr94 / CVE-2026-28684 | 1.0.1 | 1.2.2 | Symlink following en `set_key` permite sobrescritura arbitraria de archivos |
| pytest | pip | Directa (dev) | GHSA-6w46-j5rx-g56g / CVE-2025-71176 | 8.3.4 | 9.0.3 | Manejo vulnerable de `tmpdir` |

*(Las filas de `cryptography`/`PyJWT`/`python-dotenv` se duplican entre `requirements.txt` y `requirements-dev.txt` por la misma razón indicada arriba.)*

### Baja (6)

| Paquete | Ecosistema | Tipo | GHSA / CVE | Instalada | Corregida | Resumen |
|---|---|---|---|---|---|---|
| PyJWT | pip | Directa | GHSA-fhv5-28vv-h8m8 / CVE-2026-48524 | 2.10.1 | 2.13.0 | `PyJWKClient` sin límite de requests al endpoint JWKS vía `kid` controlado por atacante (DoS) |
| cryptography | pip | Directa | GHSA-m959-cc7f-wv43 / CVE-2026-34073 | 44.0.0 | 46.0.6 | Enforcement incompleto de restricción de nombre DNS |
| cryptography | pip | Directa | GHSA-79v4-65xg-pq4g / CVE-2024-12797 | 44.0.0 | 44.0.1 | OpenSSL vulnerable incluido en los wheels de cryptography |

*(Duplicadas entre ambos manifiestos de backend, igual que arriba.)*

## Clasificación por grupo

| Grupo | Criterio | Paquetes | Alertas cubiertas |
|---|---|---|---|
| **A — Actualización segura** | Parche dentro del mismo `major.minor` instalado | *(ninguno)* | 0 |
| **B — Actualización menor, requiere pruebas** | Salto de versión menor, mismo major | PyJWT (2.10→2.13), python-dotenv (1.0→1.2) | 14 |
| **C — Actualización mayor, posibles incompatibilidades** | Salto de versión mayor, o depende de uno | cryptography (44→50), pytest (8→9), react-router (7→8, transitiva), vitest (2→3), vite/esbuild anidados (dependen del bump mayor de vitest) | 21 |
| **D — Sin solución disponible** | Sin versión corregida publicada | *(ninguno)* | 0 |

## Dependencias corregidas

**Ninguna.** Se verificó exhaustivamente que ningún paquete cae en Grupo A — la regla de esta fase autoriza aplicar únicamente ese grupo de forma automática. Aplicar Grupo B o C sin pruebas dedicadas y aprobación explícita habría contradicho la instrucción de "no actualizar dependencias a ciegas" y el objetivo de no sacrificar estabilidad. Consecuentemente, **no se modificó ningún archivo de dependencias** (`requirements.txt`, `requirements-dev.txt`, `package.json`, `package-lock.json`) en esta fase.

## Dependencias pendientes

### Grupo B — recomendadas para un ciclo de pruebas dedicado

| Paquete | Versión objetivo | Alertas que resuelve |
|---|---|---|
| `PyJWT` (backend) | `2.10.1` → `2.13.0` | 6 alertas únicas (2 altas, 3 moderadas, 1 baja) |
| `python-dotenv` (backend) | `1.0.1` → `1.2.2` | 1 alerta moderada |

Riesgo de romper el proyecto: bajo-medio. Son bumps menores dentro del mismo major, pero PyJWT es central en la autenticación JWT del backend (`app/core/seguridad*`) — requiere ejecutar la suite completa de tests de auth antes de aceptar el cambio.

### Grupo C — requieren evaluación dedicada antes de intentar

| Paquete | Versión objetivo | Alertas que resuelve | Por qué no se auto-aplica |
|---|---|---|---|
| `cryptography` (backend) | `44.0.0` → `50.0.0` | 7 alertas únicas (4 altas, 1 media, 2 bajas) | Salto de 6 líneas de versión; usada en JWT RS256 y hashing — requiere pruebas de regresión completas de auth/documentos |
| `vitest` (frontend, dev) | `2.1.9` → `3.2.6` | La crítica + arrastra 4 alertas más (vite/esbuild anidados) | Major bump (2→3) de la herramienta de testing; puede cambiar configuración/API de mocks usados en los 121 tests actuales |
| `react-router` (frontend, transitiva vía react-router-dom) | `7.18.2` → `8.3.0` | 1 alerta alta | Requiere subir `react-router-dom` a una versión que dependa de react-router 8.x — cambio mayor de la librería de rutas central de toda la SPA |
| `pytest` (backend, dev) | `8.3.4` → `9.0.3` | 1 alerta moderada | Major bump; riesgo de romper fixtures/plugins usados en los 352 tests actuales |

## Riesgos

- **La única vulnerabilidad crítica (vitest) es de una dependencia de desarrollo, no de producción.** Solo es explotable si el servidor UI de Vitest (`vitest --ui`) está expuesto y accesible — no se usa en este proyecto (`npm test` ejecuta `vitest run`, sin UI) ni en CI. Riesgo real actual: bajo, pero la corrección sigue siendo recomendable antes de que alguien active la UI localmente.
- **La vulnerabilidad de `react-router` (CSRF en "RSC Mode") no aplica al patrón de uso actual del proyecto.** Se verificó en `frontend/src/app/App.tsx` que el enrutamiento usa `BrowserRouter` (modo SPA clásico), no `RouterProvider`/`createBrowserRouter` ni ningún modo de React Server Components. La superficie de ataque real de esta alerta específica es, con alta probabilidad, no explotable en este código — pero el paquete sigue nominalmente vulnerable según el escaneo de versión de Dependabot.
- **Las vulnerabilidades de `PyJWT` y `cryptography` sí son relevantes en producción** — ambas librerías son centrales en la autenticación JWT RS256 del backend. Los hallazgos de mayor preocupación real: forja de tokens HS256 vía JWK de clave pública (PyJWT, alta) y el oráculo de Bleichenbacher en PKCS#7 (cryptography, alta) — aunque requieren confirmar si el backend usa esas rutas de código específicas (mixed-algorithm JWK decode, PKCS#7 EnvelopedData) antes de asumir explotabilidad directa.
- **Ninguna corrección disponible es aplicable sin riesgo de regresión.** Esto no es un fallo de esta auditoría — es el estado real de las dependencias del proyecto: llevan meses sin actualizarse y el "salto" acumulado ahora es grande.

## Recomendaciones

1. **Corto plazo (próxima fase dedicada):** aplicar Grupo B (`PyJWT`, `python-dotenv`) en una rama `fix/deps-pyjwt-dotenv`, ejecutar la suite completa de tests de autenticación, y mergear vía PR normal.
2. **Mediano plazo:** planificar la actualización de `cryptography` a `50.0.0` como una tarea propia, con pruebas de regresión enfocadas en JWT RS256 y cualquier uso de PKCS#7/certificados.
3. **Mediano plazo:** evaluar la actualización de `vitest` a `3.x` en una rama aislada — validar que los 121 tests de frontend siguen pasando y que no hay cambios de configuración necesarios (`vite.config.ts`/`vitest.config.ts`).
4. **Bajo prioridad, revisar cuando haya ventana de mantenimiento:** actualizar `react-router-dom`/`react-router` a la línea 8.x, con pruebas manuales de navegación completas (es la librería de enrutamiento de toda la aplicación).
5. **Proceso:** una vez aplicado cualquier grupo, volver a ejecutar esta auditoría (`gh api .../dependabot/alerts`) para confirmar que las alertas correspondientes pasan a estado `dismissed`/resuelto.

## Estado de GitHub Projects

❌ **Bloqueado — sin cambios desde el último reporte.** El token de `gh` sigue sin el scope `project` (`gh auth status` confirma únicamente `gist`, `read:org`, `repo`). No se creó el proyecto `LabSync Pro Enterprise Roadmap`.

Comando exacto pendiente de ejecución por el usuario:

```
gh auth refresh -s project,read:project
```

Una vez completado ese flujo de autenticación (requiere navegador, no puede ejecutarse de forma no interactiva), se puede reintentar `gh project create --owner tavoperea25-sys --title "LabSync Pro Enterprise Roadmap"` y añadir las columnas Backlog/Planning/Development/Code Review/Testing/Done.
