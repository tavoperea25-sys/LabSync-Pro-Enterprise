# Release Strategy — LabSync Pro Enterprise

## Versionado

Versionado Semántico (`MAJOR.MINOR.PATCH`):

- **MAJOR** — cambios incompatibles con versiones anteriores (breaking changes de API, migraciones de base de datos irreversibles, cambios de contrato).
- **MINOR** — nuevas funcionalidades compatibles con versiones anteriores.
- **PATCH** — correcciones de bugs y parches de seguridad compatibles con versiones anteriores.

**Ejemplos:**

```
1.0.0   → primera versión estable
1.1.0   → nueva funcionalidad (ej. exportación de reportes)
1.1.1   → corrección de un bug en esa funcionalidad
2.0.0   → cambio incompatible (ej. rediseño del esquema de autenticación)
```

Pre-releases usan el sufijo `-rc<N>` (ej. `v1.0.0-rc1`), consistente con el tag ya existente en el repositorio.

## Flujo de un release

```
feature/*
    |
    ↓
develop
    |
    ↓
release/*
    |
    ↓
main
    |
    ↓
tag (vMAJOR.MINOR.PATCH)
    |
    ↓
release GitHub
```

1. Las funcionalidades se desarrollan en ramas `feature/*`, nacen de `develop` y se fusionan de vuelta a `develop` vía PR.
2. Cuando `develop` acumula suficiente trabajo estabilizado para un release, se crea una rama `release/vX.Y.Z` desde `develop` para ajustes finales (actualización de `CHANGELOG.md`, fixes menores, sin nuevas funcionalidades).
3. La rama `release/*` se fusiona a `main` vía PR.
4. Se crea un tag anotado (`git tag -a vX.Y.Z`) sobre el commit de `main` correspondiente al merge.
5. La rama `release/*` se fusiona también de vuelta a `develop`, para que los ajustes finales del release no se pierdan en el trabajo futuro.
6. Se publica un GitHub Release a partir del tag, con notas derivadas de la sección correspondiente de `CHANGELOG.md`.

## Hotfixes

Para correcciones urgentes sobre producción, el flujo se simplifica: `main` → `hotfix/*` → PR a `main` (tag de patch) → PR también a `develop`. Detalle completo en [`docs/git-workflow.md`](git-workflow.md).

## Relación con otros documentos

- [`docs/git-workflow.md`](git-workflow.md) — estrategia de ramas y Conventional Commits.
- [`docs/github-repository-strategy.md`](github-repository-strategy.md) — configuración general del repositorio en GitHub.
- `CHANGELOG.md` (raíz del proyecto) — historial de cambios por versión, formato Keep a Changelog.
