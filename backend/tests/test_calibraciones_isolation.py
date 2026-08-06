"""Gate crítico de CI para la tabla `calibraciones` — mismo patrón que
tests/test_equipos_isolation.py (docs/19-checklist.md)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.calibraciones.infrastructure.models import Calibracion
from app.modules.equipos.infrastructure.models import Equipo


def _crear_equipo_directo(db: Session, laboratorio_id: uuid.UUID, codigo: str) -> uuid.UUID:
    equipo_id = uuid.uuid4()
    db.add(
        Equipo(
            id=equipo_id,
            laboratorio_id=laboratorio_id,
            codigo_interno=codigo,
            nombre=f"Equipo {codigo}",
            estado_operativo="operativo",
        )
    )
    db.commit()
    return equipo_id


def _crear_calibracion_directa(db: Session, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID) -> None:
    db.add(
        Calibracion(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            equipo_id=equipo_id,
            fecha_calibracion=date(2026, 1, 1),
            frecuencia_meses=12,
            proxima_fecha=date(2027, 1, 1),
            resultado="conforme",
        )
    )
    db.commit()


def test_rls_bloquea_lectura_de_calibraciones_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Cal A", "lab-cal-a", "admin@lab-cal-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Cal B", "lab-cal-b", "admin@lab-cal-b.dev")

    set_tenant_context(db, lab_a)
    equipo_a = _crear_equipo_directo(db, lab_a, "EQ-CAL-A")
    set_tenant_context(db, lab_a)  # cada commit() cierra la transacción y limpia el SET LOCAL
    _crear_calibracion_directa(db, lab_a, equipo_a)

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-CAL-B")
    set_tenant_context(db, lab_b)
    _crear_calibracion_directa(db, lab_b, equipo_b)

    set_tenant_context(db, lab_a)
    equipos_desde_a = {c.equipo_id for c in db.query(Calibracion).all()}
    assert equipos_desde_a == {equipo_a}


def test_rls_bloquea_escritura_cruzada_de_calibraciones(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Cal C", "lab-cal-c", "admin@lab-cal-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Cal D", "lab-cal-d", "admin@lab-cal-d.dev")

    set_tenant_context(db, lab_a)
    equipo_a = _crear_equipo_directo(db, lab_a, "EQ-CAL-C")

    calibracion_cruzada = Calibracion(
        id=uuid.uuid4(),
        laboratorio_id=lab_b,
        equipo_id=equipo_a,
        fecha_calibracion=date(2026, 1, 1),
        frecuencia_meses=12,
        proxima_fecha=date(2027, 1, 1),
        resultado="conforme",
    )
    db.add(calibracion_cruzada)

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_no_se_puede_eliminar_una_calibracion(db: Session, crear_laboratorio_con_admin):
    """RN-CAL-02 reforzado a nivel de permisos de base de datos — sin
    DELETE otorgado al rol de aplicación, ni un bug de código puede borrar
    una calibración registrada."""
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Cal E", "lab-cal-e", "admin@lab-cal-e.dev")
    set_tenant_context(db, lab_a)
    equipo_a = _crear_equipo_directo(db, lab_a, "EQ-CAL-E")
    set_tenant_context(db, lab_a)
    _crear_calibracion_directa(db, lab_a, equipo_a)

    with pytest.raises(ProgrammingError, match="permission denied"):
        db.execute(Calibracion.__table__.delete())
        db.flush()
