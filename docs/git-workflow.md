# Git Workflow — LabSync Pro Enterprise

## Branch strategy

| Rama | Propósito | Vida |
|---|---|---|
| `main` | Producción / releases. Siempre desplegable. | Permanente |
| `develop` | Integración de trabajo en curso antes de un release. | Permanente |
| `feature/*` | Nuevas funcionalidades. | Temporal — nace de `develop`, se fusiona a `develop` |
| `fix/*` | Correcciones que no son urgentes. | Temporal — nace de `develop`, se fusiona a `develop` |
| `hotfix/*` | Correcciones urgentes sobre producción. | Temporal — nace de `main`, se fusiona a `main` y a `develop` |
| `release/*` | Preparación y estabilización de una versión antes de publicarla. | Temporal — nace de `develop`, se fusiona a `main` y a `develop` |
| `docs/*` | Cambios exclusivos de documentación. | Temporal — nace de `develop`, se fusiona a `develop` |
| `refactor/*` | Cambios internos sin alterar comportamiento observable. | Temporal — nace de `develop`, se fusiona a `develop` |

Todo cambio entra a `main`/`develop` **exclusivamente mediante Pull Request** — nunca con push directo.

## Conventional Commits

Formato: `tipo(alcance opcional): descripción en imperativo`.

| Tipo | Uso |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de un defecto |
| `docs` | Solo documentación |
| `test` | Añadir o corregir tests, sin cambiar código de producción |
| `refactor` | Cambio interno sin alterar comportamiento |
| `security` | Corrección o endurecimiento de seguridad |
| `chore` | Mantenimiento (dependencias, configuración, tareas repetitivas) |

**Ejemplos:**

```
feat(auth): add JWT authentication
fix(upload): repair document validation
docs(api): update API documentation
security(storage): bind content-type to presigned upload URL
chore(deps): bump fastapi to 0.115.6
```

## Flujo típico de una funcionalidad

```bash
git checkout develop
git pull
git checkout -b feature/nombre-descriptivo

# ... trabajo ...

git push -u origin feature/nombre-descriptivo
# Abrir Pull Request hacia develop
```

## Flujo de un release

```bash
git checkout develop
git checkout -b release/v1.1.0
# Ajustes finales, actualizar CHANGELOG.md
# PR hacia main → merge → tag v1.1.0
# PR de vuelta hacia develop (para que develop tenga los ajustes del release)
```

## Flujo de un hotfix

```bash
git checkout main
git checkout -b hotfix/descripcion-corta
# corrección puntual
# PR hacia main → merge → tag de patch (ej. v1.0.1)
# PR también hacia develop
```

## Reglas

- `main` y `develop` están protegidas — sin push directo, sin force push, sin borrado.
- Todo PR requiere que pasen los checks de CI (`ruff`, `mypy`, `pytest` en backend; `lint`, `typecheck`, `test`, `build` en frontend) y al menos una aprobación.
- Los nombres de rama son descriptivos en minúsculas con guiones (`feature/subida-masiva-documentos`, no `feature/nueva-funcionalidad-2`).
