# Recomendación de mejora — CI/CD

**Fecha:** 2026-08-06
**Alcance:** revisión de `.github/workflows/ci.yml`, solo reporte — sin modificar el archivo.

## Hallazgo

El disparador `push` del workflow solo incluye la rama `main`:

```yaml
on:
  pull_request:
  push:
    branches: [main]
```

Con la rama `develop` ya creada y sincronizada con `origin/develop`, un push directo a `develop` (fuera de un Pull Request) **no dispara CI**. Hoy `develop` solo obtiene validación de CI cuando el cambio llega vía Pull Request (el trigger `pull_request:` no tiene filtro de rama destino, así que sí cubre PRs hacia `develop`).

Este mismo hallazgo ya había sido reportado, sin aplicar, en `docs/github-repository-strategy.md` (Fase 5).

## Recomendación

Añadir `develop` a la lista de ramas del trigger `push`:

```yaml
on:
  pull_request:
  push:
    branches: [main, develop]
```

## Impacto de no aplicarlo

Bajo, siempre que la regla operativa del equipo sea "nunca push directo a `develop`, todo vía PR" (que es la regla definida en `docs/git-workflow.md`). Si esa disciplina se mantiene, el `pull_request:` trigger ya cubre el caso real. El riesgo aparece solo si alguien hace push directo a `develop` sin PR — en ese escenario, el cambio quedaría sin validar por CI hasta el siguiente PR.

## Estado

No aplicado en esta fase, por instrucción explícita de no modificar `.github/workflows/ci.yml` automáticamente. Pendiente de aprobación explícita para aplicarse en una fase futura.
