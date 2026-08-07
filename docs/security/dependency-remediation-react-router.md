# Remediación de dependencias — `react-router` (Grupo C)

**Fecha:** 2026-08-07
**Rama:** `fix/dependencies-react-router-group-c` (creada desde `develop`)

## Objetivo

Corregir la última alerta de severidad **alta** del repo (`react-router`, GHSA-qwww-vcr4-c8h2), sin tocar `pytest` (la única alerta que queda después de esta fase, moderada, backend).

## Versión anterior

`react-router-dom@^7.1.1` (resuelto en el lockfile a `7.18.2`, con `react-router` como dependencia transitiva en la misma versión)

## Versión nueva

`react-router@^8.3.0` (resuelto a `8.3.0`) — **`react-router-dom` se elimina como paquete**, no se reemplaza por otra versión.

## Vulnerabilidad corregida

| GHSA / CVE | Severidad | Paquete | Resumen |
|---|---|---|---|
| [GHSA-qwww-vcr4-c8h2](https://github.com/advisories/GHSA-qwww-vcr4-c8h2) | Alta | react-router | Bypass de CSRF en modo RSC permite ejecutar una acción antes de la respuesta 400 |

## Análisis de impacto (previo a la actualización)

**La vulnerabilidad en sí no aplica al patrón de uso de este proyecto:** confirmado en `frontend/src/app/App.tsx` que el enrutamiento usa `BrowserRouter`/`Routes`/`Route` (modo SPA clásico, declarativo), no `RouterProvider`/`createBrowserRouter` ni ningún modo de React Server Components — la única vía de explotación de esta alerta. La actualización igual se aplicó por disciplina (es la única alerta alta restante) y porque el proyecto ya llevaba dos versiones mayores de atraso.

**Esto NO fue un bump menor** — a diferencia de `cryptography`/`pyjwt`/`vitest`, react-router 7→8 elimina por completo el paquete `react-router-dom` (el shim de compatibilidad con imports estilo v6 que existía durante toda la v7 desaparece). Cada símbolo (`BrowserRouter`, `Routes`, `Route`, `Navigate`, `Link`, `NavLink`, `MemoryRouter`, `useNavigate`, `useLocation`, `useParams`, `useSearchParams`, `LinkProps`) pasa a exportarse directamente desde el paquete `react-router`. Según el [anuncio oficial de v8](https://remix.run/blog/react-router-v8), a nivel de API es "un upgrade no disruptivo" — el único cambio real para este proyecto es la ruta de import.

**Alcance real, verificado con `grep` antes de tocar nada:** 38 archivos en `frontend/src` importaban de `"react-router-dom"` (no solo los 5 de `src/app/` — se extiende a prácticamente cada feature de la SPA). Se hizo un reemplazo mecánico de `from "react-router-dom"` → `from "react-router"` en los 38, más dos referencias adicionales en `Omnibox.test.tsx` que mockeaban el módulo por nombre (`vi.mock("react-router-dom", ...)`) y no las tocaba un reemplazo basado en `from "..."`.

**Efecto colateral obligatorio: bump de Vite 6→7.** React Router v8 requiere Vite 7 (usa la Vite Environment API). Se revisó la [guía de migración oficial de Vite 7](https://v7.vite.dev/guide/migration): elimina el soporte legado de Sass y `splitVendorChunkPlugin` (ninguno usado en este proyecto — `grep` sin resultados) y actualiza los targets de navegador por defecto. Sin breaking changes aplicables.

**Requisitos mínimos de v8 verificados contra el proyecto:**

| Requisito | Mínimo v8 | Proyecto | ¿Cumple? |
|---|---|---|---|
| React | 19.2.7 | 19.2.8 (instalado) | ✅ |
| Node | 22.22.0 | CI: `node-version: "22"` (setup-node resuelve al último 22.x); Docker: `node:22-slim` | Verificar en CI/build que el 22.x resuelto sea ≥22.22.0 |
| Vite | 7.x | Actualizado en este mismo cambio | ✅ |
| Módulos | ESM-only | `"type": "module"` ya fijado en `package.json` | ✅ |

## Cambios realizados

- `frontend/package.json`: `"react-router-dom": "^7.1.1"` → `"react-router": "^8.3.0"` (en `dependencies`); `"vite": "^6.0.6"` → `"vite": "^7.0.0"` (en `devDependencies`, requerido por react-router 8).
- 38 archivos de `frontend/src`: `from "react-router-dom"` → `from "react-router"`.
- `frontend/src/features/busqueda/components/Omnibox.test.tsx`: el `vi.mock("react-router-dom", ...)` y su `typeof import("react-router-dom")` pasan a `"react-router"`, para que el mock siga aplicando al módulo real que ahora importa el componente.
- `frontend/package-lock.json`: regenerado por `npm install`.
- Ningún cambio de lógica de la aplicación — el enrutamiento, guardas de ruta y navegación funcionan igual, solo cambió de dónde se importan.

## Resultado de pruebas

| Comando | Resultado |
|---|---|
| `npm run lint` | ✅ Sin errores ni warnings |
| `npm run typecheck` | ✅ Sin errores (TypeScript habría fallado si algún símbolo no existiera en el nuevo paquete) |
| `npm test` (`vitest run`) | ✅ 121 passed (24 archivos) — incluye `ProtectedRoute.test.tsx`, `LoginPage.test.tsx` y `navigation.test.ts`, que ejercitan directamente guardas de ruta y lógica de navegación |
| `npm run build` | ✅ built in 14.79s |
| `npm audit` | ✅ **0 vulnerabilidades** — ninguna alerta de frontend restante |

## Resultado de Dependabot

Pendiente confirmar en vivo tras fusionar y promover a `main` (mismo patrón que las fases anteriores: el conteo de GitHub no cambia hasta que el fix llegue a la rama por defecto).

**Proyección** (contra la única alerta que corrige esta fase):

| Severidad | Antes | Después (proyectado) | Diferencia |
|---|---|---|---|
| Alta | 1 (`react-router`) | 0 | -1 |
| Moderada | 1 (`pytest`) | 1 | 0 |
| **Total** | **2** | **1** | **-1** |

Con esto, de las 35 alertas originales del primer reporte, solo quedaría **1** (`pytest`, moderada, backend).

## Riesgos pendientes

- `pytest` (backend, moderada) — última alerta del repo, requiere su propia fase (major bump 8→9, riesgo sobre fixtures/plugins de los 352 tests).
- Ninguno — ver "Verificación manual en navegador real" más abajo.

## Verificación manual en navegador real

Con el stack completo levantado (`docker compose up postgres minio backend worker` + `npm run dev` en frontend, código de esta rama, contra el usuario admin de `seed_dev_tenant.py`):

- **Login** (`/` → formulario → dashboard con datos reales) — ✅
- **Navegación directa por URL** a rutas protegidas (`/equipos`, `/documentos`) — ✅ ambas renderizan con datos reales del backend
- **Detalle de equipo vía Omnibox** (Ctrl+K, buscar "microscopio", clic en el resultado) — ✅ navega correctamente a `/equipos/{id}` y cierra el diálogo; ejercita `useNavigate()` importado desde `react-router` (el mismo mecanismo cubierto por el mock corregido en `Omnibox.test.tsx`)
- **Logout** (menú de perfil → "Cerrar sesión") — ✅ redirige a `/login`
- **Guardia de ruta protegida estando deslogueado**: navegación directa a `/equipos` sin sesión — ✅ redirige a `/login` (confirma que `Navigate` en `ProtectedRoute.tsx` sigue funcionando)
- Consola del navegador revisada de punta a punta: solo errores esperados (401 tras logout, 404 de un token QR inválido de un flujo no relacionado) — cero errores de módulos, imports rotos, o crashes de routing.

## Recomendaciones

1. Revisar y aprobar este PR de forma independiente.
2. Si es posible, una pasada manual rápida de navegación en `npm run dev` (login → dashboard → un par de rutas protegidas → logout) antes de fusionar, dado que es el cambio de mayor superficie de esta serie de remediaciones.
3. Tras fusionar y promover a `main`, confirmar vía `gh api .../dependabot/alerts` que solo queda la alerta de `pytest`.
4. Planificar `pytest` 8→9 como la última fase pendiente.
