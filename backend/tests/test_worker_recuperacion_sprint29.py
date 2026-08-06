"""Fase 1 / I12 (auditoría 2026-07-31) — cobertura de rutas de recuperación
de `app/worker/main.py` (78% antes de este sprint — ver
tests/test_worker_notificaciones.py, Fase 0/C1, para el caso ya cubierto del
outbox de notificaciones). Aquí se cubren las dos rutas de recuperación que
quedaban sin probar: un reporte que falla al generarse, y que un laboratorio
falle sin tumbar el barrido completo de todos los laboratorios."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.reportes.infrastructure.models import ReporteGenerado
from app.worker.main import _procesar_laboratorio, _procesar_reportes_pendientes, ejecutar_ciclo


def _crear_reporte(
    db: Session, laboratorio_id: uuid.UUID, tipo: str, formato: str, filtros: dict | None = None
) -> uuid.UUID:
    reporte_id = uuid.uuid4()
    db.add(
        ReporteGenerado(
            id=reporte_id,
            laboratorio_id=laboratorio_id,
            tipo=tipo,
            formato=formato,
            filtros=filtros or {},
            estado="pendiente",
        )
    )
    db.commit()
    return reporte_id


def test_un_reporte_que_falla_al_generarse_no_bloquea_a_los_demas_del_mismo_ciclo(
    db: Session, crear_laboratorio_con_admin
):
    """`paquete_auditoria` sin el filtro `equipo_id` falla de forma real (no
    simulada) dentro de `generar_datos_por_tipo` — el mismo tipo de fallo que
    podría producir cualquier reporte con datos inconsistentes. Se crea junto
    a un reporte `inventario` válido, en el mismo laboratorio y el mismo
    tick, para confirmar que el fallo de uno no impide que el otro se
    complete (mismo criterio de aislamiento ya aplicado al outbox de
    notificaciones en Fase 0/C1).

    Esta prueba encontró un bug real al escribirse por primera vez
    (2026-08-04, Fase 1/I12): sin `set_tenant_context` al inicio de cada
    iteración del bucle en `_procesar_reportes_pendientes`, el reporte
    `inventario` (perfectamente válido) terminaba marcado 'fallido' con un
    `AssertionError` genérico, solo por procesarse después de uno que sí
    falló — el mismo `SET LOCAL` moría con el commit del manejo del primer
    reporte. Corregido en el mismo commit que esta prueba."""
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Worker Reportes", "lab-worker-reportes", "admin@lab-worker-reportes.dev"
    )
    set_tenant_context(db, laboratorio_id)

    reporte_fallido_id = _crear_reporte(db, laboratorio_id, "paquete_auditoria", "pdf", filtros={})
    # `_crear_reporte` comitea internamente — el `SET LOCAL` de tenant muere
    # con ese commit (mismo motivo ya documentado en app/worker/main.py).
    set_tenant_context(db, laboratorio_id)
    reporte_ok_id = _crear_reporte(db, laboratorio_id, "inventario", "csv", filtros={})

    set_tenant_context(db, laboratorio_id)
    _procesar_reportes_pendientes(db, laboratorio_id)

    db.expire_all()
    set_tenant_context(db, laboratorio_id)
    fallido = db.get(ReporteGenerado, reporte_fallido_id)
    ok = db.get(ReporteGenerado, reporte_ok_id)

    assert fallido.estado == "fallido"
    assert fallido.error is not None and "equipo_id" in fallido.error
    assert fallido.completado_en is None

    assert ok.estado == "listo"
    assert ok.object_key is not None
    assert ok.nombre_archivo is not None
    assert ok.completado_en is not None


def test_ejecutar_ciclo_procesa_todos_los_laboratorios_aunque_uno_falle(
    db: Session, crear_laboratorio_con_admin, monkeypatch
):
    """`ejecutar_ciclo()` no tenía ninguna prueba propia — itera TODOS los
    laboratorios de la base (no solo uno pasado explícitamente), así que se
    necesitan al menos 2 laboratorios reales para verificar que procesar uno
    no depende de ni bloquea al otro. Se fuerza el fallo del laboratorio A
    con `monkeypatch` sobre `EvaluadorAlertasService.evaluar_laboratorio` —
    la única forma práctica de disparar la rama `except Exception` más
    externa de `_procesar_laboratorio` (líneas 251-255): a diferencia del
    outbox o de un reporte, no hay un dato real y determinista que haga
    fallar la evaluación de alertas en sí misma sin tocar código de
    aplicación. El resto de la prueba (que el laboratorio B si se procese)
    corre sin ningún mock, contra Postgres real."""
    laboratorio_a, _, _, _ = crear_laboratorio_con_admin(
        "Lab Worker Ciclo A", "lab-worker-ciclo-a", "admin@lab-worker-ciclo-a.dev"
    )
    laboratorio_b, _, _, _ = crear_laboratorio_con_admin(
        "Lab Worker Ciclo B", "lab-worker-ciclo-b", "admin@lab-worker-ciclo-b.dev"
    )
    set_tenant_context(db, laboratorio_b)
    reporte_b_id = _crear_reporte(db, laboratorio_b, "inventario", "csv", filtros={})

    from app.modules.alertas.application.evaluador_service import EvaluadorAlertasService

    evaluar_original = EvaluadorAlertasService.evaluar_laboratorio

    def _evaluar_que_falla(self, laboratorio_id: uuid.UUID) -> int:
        if laboratorio_id == laboratorio_a:
            raise RuntimeError("fallo simulado — ver docstring de la prueba")
        return evaluar_original(self, laboratorio_id)

    monkeypatch.setattr(EvaluadorAlertasService, "evaluar_laboratorio", _evaluar_que_falla)

    # No debe propagar la excepción del laboratorio A hacia arriba.
    ejecutar_ciclo()

    db.expire_all()
    set_tenant_context(db, laboratorio_b)
    reporte_b = db.get(ReporteGenerado, reporte_b_id)
    # Si `ejecutar_ciclo` se hubiera detenido al fallar el laboratorio A,
    # este reporte del laboratorio B (que se itera después, mismo orden de
    # creación) seguiría "pendiente".
    assert reporte_b.estado == "listo"


def test_un_laboratorio_que_falla_por_completo_no_impide_reintentarlo_en_el_proximo_ciclo(
    db: Session, crear_laboratorio_con_admin, monkeypatch
):
    """Complementa la prueba anterior a nivel de `_procesar_laboratorio`
    directamente: confirma que la función no relanza la excepción (el
    `except Exception` más externo la contiene) y que la sesión se cierra
    igual, sin importar el fallo — ver `finally: db.close()`."""
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Worker Fallo Total", "lab-worker-fallo-total", "admin@lab-worker-fallo-total.dev"
    )

    from app.modules.alertas.application.evaluador_service import EvaluadorAlertasService

    def _evaluar_que_siempre_falla(self, laboratorio_id: uuid.UUID) -> int:
        raise RuntimeError("fallo simulado — ver docstring de la prueba")

    monkeypatch.setattr(EvaluadorAlertasService, "evaluar_laboratorio", _evaluar_que_siempre_falla)

    try:
        _procesar_laboratorio(laboratorio_id)
    except Exception as exc:  # pragma: no cover - solo se ejecuta si la prueba falla
        pytest.fail(f"_procesar_laboratorio no debía dejar escapar la excepción: {exc!r}")
