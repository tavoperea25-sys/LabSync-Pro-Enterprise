# GitHub Repository Strategy — LabSync Pro Enterprise

**Estado de este documento:** especifica la configuración que debe aplicarse al repositorio remoto. La creación del repositorio y la configuración que solo existe en GitHub (protección de rama, topics, visibilidad) **no se ha ejecutado todavía** — este entorno de trabajo no tiene `gh` CLI instalado ni credenciales de Git configuradas para GitHub. Ver `docs/fase-5-github-setup-report.md` para el detalle de qué está pendiente y por qué.

---

## Repository information

**Nombre:** `LabSync-Pro-Enterprise`

**Descripción:** *"Enterprise clinical laboratory document management platform with secure workflows, authentication, automation and modern architecture."*

**Topics:**
```
healthcare, clinical-lab, document-management, fastapi, react, typescript,
python, docker, postgresql, enterprise, security, automation
```

## Visibility decision

**PRIVATE.** Razón: producto empresarial en desarrollo, para una entidad de salud pública real (Laboratorio de Salud Pública del Cesar), sin una decisión de licencia open-source (el proyecto es software propietario — ver `README.md` sección Licencia).

## Branch strategy

Ver detalle completo en [`docs/git-workflow.md`](git-workflow.md). Resumen: `main` (producción) + `develop` (integración) + ramas temporales (`feature/*`, `fix/*`, `hotfix/*`, `release/*`, `docs/*`, `refactor/*`), todo vía Pull Request.

## Commit convention

Conventional Commits (`feat`, `fix`, `docs`, `test`, `refactor`, `security`, `chore`) — detalle y ejemplos en [`docs/git-workflow.md`](git-workflow.md).

## Pull Request rules

- Ningún push directo a `main` ni `develop`.
- Al menos 1 aprobación requerida antes de fusionar.
- Todos los checks de CI en verde antes de fusionar (ver CI/CD abajo).
- Conversaciones resueltas antes de fusionar.
- Sin force push ni borrado de `main`/`develop`.
- Plantilla obligatoria: [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md) (ya existe en el repositorio).

## CI/CD

Pipeline actual (`.github/workflows/ci.yml`, ya existente y verificado en verde):

| Job | Pasos |
|---|---|
| `backend` | instalar dependencias → `ruff check .` → `mypy app` → arrancar MinIO real → `pytest --cov=app` |
| `frontend` | `npm install` → `npm run lint` → `npm run typecheck` → `npm test` → `npm run build` |

Disparadores actuales: `pull_request` (sin filtro de rama — corre en PRs hacia cualquier rama, incluida `develop`) y `push` a `main` únicamente.

**Recomendación (no aplicada, requiere tu aprobación):** añadir `develop` a los disparadores de `push` (`branches: [main, develop]`), para que un push directo a `develop` —si llegara a ocurrir— también dispare CI. Hoy solo lo dispara si llega vía Pull Request.

## Release strategy

Versionado Semántico (`vMAJOR.MINOR.PATCH`), con pre-releases tipo `v1.0.0-rc1`. `CHANGELOG.md` (ya existente) sigue el formato Keep a Changelog y se actualiza en cada release. GitHub Releases se crean a partir de tags anotados sobre `main`, con las notas derivadas de la sección correspondiente de `CHANGELOG.md`.

## Security rules

- Branch protection en `main` y `develop` (detalle en `docs/fase-5-github-setup-report.md` — pendiente de aplicación manual).
- `SECURITY.md` ya existente (`.github/SECURITY.md`) define el canal de reporte de vulnerabilidades.
- Dependabot ya configurado (`.github/dependabot.yml`) para `pip`, `npm` y `github-actions`.
- Ningún secreto real versionado — auditado en `docs/security-audit-pre-git.md`.
