# LabSync Pro — Frontend

React 19 + TypeScript + Vite + Tailwind + componentes estilo shadcn/ui. Ver `docs/11-design-system.md`, `docs/12-component-library.md`, `docs/13-arquitectura.md`.

## Desarrollo (recomendado: Docker Compose desde la raíz del repo)

```bash
docker compose up --build
```

Abre `http://localhost:5173`. El proxy de Vite reenvía `/api/*` al backend (ver `vite.config.ts`).

## Desarrollo sin Docker

```bash
npm install
cp .env.example .env
npm run dev
```

## Comandos

```bash
npm run dev         # servidor de desarrollo
npm run build        # build de producción (tsc -b + vite build)
npm run lint          # ESLint
npm run typecheck     # TypeScript en modo estricto, sin emitir
npm test              # Vitest
```

## Estado de Sprint 1

Este scaffold prueba la autenticación completa de punta a punta contra el backend real (login, sesión persistida vía refresh token en cookie httpOnly, logout). El `LoginPage` actual es funcional pero **no** es todavía la migración visual completa del login original — esa migración (glassmorphism, panel institucional con Motion, todas las microinteracciones ya auditadas en accesibilidad) es Sprint 2 (`docs/18-sprints.md`) y reutilizará esta misma base de formulario/validación.

## Estructura

Ver `docs/13-arquitectura.md` sección 10 — organización por features (`src/features/<modulo>/`), componentes compartidos en `src/shared/`.
