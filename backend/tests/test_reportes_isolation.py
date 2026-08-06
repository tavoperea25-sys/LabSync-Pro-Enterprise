"""Gate crítico de CI para reportes_generados — mismo patrón que
tests/test_equipos_isolation.py y tests/test_auditoria_isolation.py."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.reportes.infrastructure.models import ReporteGenerado


def _crear_reporte_directo(db: Session, laboratorio_id: uuid.UUID, tipo: str = "inventario") -> None:
    db.add(
        ReporteGenerado(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            tipo=tipo,
            formato="csv",
            estado="listo",
        )
    )
    db.commit()


def test_rls_bloquea_lectura_de_reportes_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Rep A", "lab-rep-a", "admin@lab-rep-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Rep B", "lab-rep-b", "admin@lab-rep-b.dev")

    set_tenant_context(db, lab_a)
    _crear_reporte_directo(db, lab_a, "inventario")

    set_tenant_context(db, lab_b)
    _crear_reporte_directo(db, lab_b, "calibraciones")

    set_tenant_context(db, lab_a)
    tipos_desde_a = {r.tipo for r in db.query(ReporteGenerado).all()}
    assert tipos_desde_a == {"inventario"}

    set_tenant_context(db, lab_b)
    tipos_desde_b = {r.tipo for r in db.query(ReporteGenerado).all()}
    assert tipos_desde_b == {"calibraciones"}


def test_rls_bloquea_escritura_cruzada_de_reportes(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Rep C", "lab-rep-c", "admin@lab-rep-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Rep D", "lab-rep-d", "admin@lab-rep-d.dev")

    set_tenant_context(db, lab_a)
    reporte_cruzado = ReporteGenerado(
        id=uuid.uuid4(), laboratorio_id=lab_b, tipo="inventario", formato="csv", estado="listo"
    )
    db.add(reporte_cruzado)

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_no_se_puede_borrar_reportes(db: Session, crear_laboratorio_con_admin):
    """El historial de reportes se conserva completo — sin GRANT DELETE
    para el rol de aplicación (ver alembic/versions/0009_reportes.py)."""
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Rep E", "lab-rep-e", "admin@lab-rep-e.dev")
    set_tenant_context(db, lab_a)
    _crear_reporte_directo(db, lab_a, "inventario")

    with pytest.raises(ProgrammingError, match="permission denied"):
        db.execute(ReporteGenerado.__table__.delete())
        db.flush()
