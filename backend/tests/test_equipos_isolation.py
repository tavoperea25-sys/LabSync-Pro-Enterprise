"""Gate crítico de CI para la tabla `equipos` — mismo patrón que
tests/test_tenant_isolation.py (docs/19-checklist.md)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.equipos.infrastructure.models import Equipo


def _crear_equipo_directo(db: Session, laboratorio_id: uuid.UUID, codigo: str) -> None:
    db.add(
        Equipo(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            codigo_interno=codigo,
            nombre=f"Equipo {codigo}",
            estado_operativo="operativo",
        )
    )
    db.commit()


def test_rls_bloquea_lectura_de_equipos_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Eq A", "lab-eq-a", "admin@lab-eq-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Eq B", "lab-eq-b", "admin@lab-eq-b.dev")

    set_tenant_context(db, lab_a)
    _crear_equipo_directo(db, lab_a, "EQ-A-001")

    set_tenant_context(db, lab_b)
    _crear_equipo_directo(db, lab_b, "EQ-B-001")

    set_tenant_context(db, lab_a)
    codigos_desde_a = {e.codigo_interno for e in db.query(Equipo).all()}
    assert codigos_desde_a == {"EQ-A-001"}

    set_tenant_context(db, lab_b)
    codigos_desde_b = {e.codigo_interno for e in db.query(Equipo).all()}
    assert codigos_desde_b == {"EQ-B-001"}


def test_rls_bloquea_escritura_cruzada_de_equipos(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Eq C", "lab-eq-c", "admin@lab-eq-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Eq D", "lab-eq-d", "admin@lab-eq-d.dev")

    set_tenant_context(db, lab_a)
    equipo_cruzado = Equipo(
        id=uuid.uuid4(),
        laboratorio_id=lab_b,
        codigo_interno="EQ-INTRUSO",
        nombre="Intento cruzado",
        estado_operativo="operativo",
    )
    db.add(equipo_cruzado)

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()
