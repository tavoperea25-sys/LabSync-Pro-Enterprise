# Remediación de dependencias — `pytest` (Grupo C, última fase)

**Fecha:** 2026-08-07
**Rama:** `fix/dependencies-pytest-group-c` (creada desde `develop`)

## Objetivo

Corregir la **última alerta de Dependabot que queda en el repo** (`pytest`, moderada, GHSA-6w46-j5rx-g56g). Con esto se cierran las 35 alertas originales del primer reporte de auditoría.

## Versión anterior

`pytest==8.3.4` (en `backend/requirements-dev.txt`)

## Versión nueva

`pytest==9.0.3`

## Vulnerabilidad corregida

| GHSA / CVE | Severidad | Paquete | Resumen |
|---|---|---|---|
| [GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g) / CVE-2025-71176 | Moderada | pytest | Manejo vulnerable de `tmpdir` |

`pytest` es una dependencia de desarrollo (`requirements-dev.txt`), nunca se instala ni corre en producción — el riesgo real de esta alerta siempre fue nulo fuera de las máquinas de CI/desarrolladores. Se corrige de todas formas por ser la última pendiente.

## Análisis de impacto (previo a la actualización)

Revisado contra el [changelog oficial de pytest 9.0.0](https://docs.pytest.org/en/stable/announce/release-9.0.0.html) y la [página de deprecaciones](https://docs.pytest.org/en/stable/deprecations.html). El patrón general de esta versión: los `PytestRemovedIn9Warning` que pytest 8.x venía emitiendo como advertencia se convierten en errores duros en 9.0 — así que el riesgo real depende de si el proyecto ya tenía alguno de esos warnings pendientes.

**Verificado explícitamente, antes del bump:**

- `pytest -W error::pytest.PytestDeprecationWarning` sobre la suite completa (352 tests) con **pytest 8.3.4** — cero warnings de deprecación de pytest disparados (los únicos 6 warnings de la suite son `DeprecationWarning` de FastAPI por `@app.on_event`, no relacionados con pytest).
- Sin fixtures `async def` en `conftest.py` ni en `tests/` (`grep` sin resultados) — no aplica la eliminación del manejo legado de fixtures async en 9.0. Las dos únicas menciones de `asyncio`/`anyio` en tests ([tests/test_integrity_error_handler.py](../../backend/tests/test_integrity_error_handler.py), [tests/test_websocket_notificaciones.py](../../backend/tests/test_websocket_notificaciones.py)) usan `asyncio.run(...)` dentro de funciones de test síncronas normales, no fixtures async de pytest — sin dependencia de `pytest-asyncio` en el proyecto.
- Sin funciones de setup/teardown estilo nose (`setup()`/`teardown()` a nivel de módulo, `setUp`/`tearDown` estilo unittest) en ningún archivo de `tests/` — el otro foco principal de incompatibilidad de 8→9 según el changelog.
- `pytest-cov==6.0.0` (ya en el proyecto) es compatible con pytest 9 sin cambios — confirmado instalando ambos juntos, sin conflictos (`pip check`).
- El resto de cambios documentados (progreso de terminal desactivado por defecto salvo Windows, cambio en el atributo privado `config.inicfg`) no aplican: el proyecto no usa reporters custom ni accede a `config.inicfg` en ningún conftest/plugin propio.

No se encontró ningún breaking change aplicable a este proyecto. Se procedió con la actualización.

## Cambios realizados

- `backend/requirements-dev.txt`: `pytest==8.3.4` → `pytest==9.0.3`. Ningún otro paquete tocado — `pytest-cov` se mantiene en `6.0.0`, ya compatible.
- Ningún cambio de código de tests ni de `conftest.py` — no fue necesario.

## Resultado de pruebas

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed! |
| `mypy app` | ✅ Success: no issues found in 183 source files |
| `pytest --cov=app --cov-report=term-missing` | ✅ 352 passed, 6 warnings — cobertura **95%**, idéntica a la baseline |
| `pytest -W error::pytest.PytestDeprecationWarning -W error::pytest.PytestRemovedIn9Warning` sobre toda la suite, ya con **pytest 9.0.3** | ✅ 352 passed — confirma que no quedó ningún warning de deprecación/remoción de pytest sin resolver |
| `pip check` | ✅ No broken requirements found |

Frontend: sin cambios — no aplica (esta fase es exclusivamente backend).

## Resultado de Dependabot

Pendiente confirmar en vivo tras fusionar y promover a `main` (mismo patrón que todas las fases anteriores).

**Proyección** (última alerta del repo):

| Severidad | Antes | Después (proyectado) | Diferencia |
|---|---|---|---|
| Moderada | 1 (`pytest`) | 0 | -1 |
| **Total** | **1** | **0** | **-1** |

Con esto, de las **35 alertas originales** del primer reporte de auditoría (`docs/security/dependabot-audit-report.md`), quedarían **0** una vez que este cambio llegue a `main`.

## Riesgos pendientes

Ninguno — esta es la última fase de remediación planeada. Recomendación de mantenimiento continuo: correr `gh api .../dependabot/alerts` periódicamente (o activar las actualizaciones de seguridad automáticas de Dependabot) para detectar nuevas alertas a medida que se publiquen, en vez de esperar a otra auditoría manual completa.

## Recomendaciones

1. Revisar y aprobar este PR de forma independiente.
2. Tras fusionar y promover a `main`, confirmar vía `gh api .../dependabot/alerts` que el conteo real llega a **0**.
3. Cerrar/actualizar `docs/security/dependabot-audit-report.md` con el resultado final de toda la serie de remediaciones (Grupo B + las 4 fases de Grupo C).
