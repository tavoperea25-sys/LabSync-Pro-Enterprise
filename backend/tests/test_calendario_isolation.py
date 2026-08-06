"""Gate crítico de CI para la tabla `eventos_calendario` — mismo patrón que
tests/test_alertas_isolation.py (docs/19-checklist.md)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.calendario.infrastructure.models import EventoCalendario


def _crear_evento_directo(db: Session, laboratorio_id: uuid.UUID) -> uuid.UUID:
    evento_id = uuid.uuid4()
    db.add(
        EventoCalendario(
            id=evento_id,
            laboratorio_id=laboratorio_id,
            tipo="institucional",
            titulo="Prueba de aislamiento",
            fecha=datetime(2026, 8, 1, tzinfo=UTC),
        )
    )
    db.commit()
    return evento_id


def test_rls_bloquea_lectura_de_eventos_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Cal9 A", "lab-cal9-iso-a", "admin@lab-cal9-iso-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Cal9 B", "lab-cal9-iso-b", "admin@lab-cal9-iso-b.dev")

    set_tenant_context(db, lab_a)
    evento_a = _crear_evento_directo(db, lab_a)

    set_tenant_context(db, lab_b)
    _crear_evento_directo(db, lab_b)

    set_tenant_context(db, lab_a)
    ids_desde_a = {e.id for e in db.query(EventoCalendario).all()}
    assert ids_desde_a == {evento_a}


def test_rls_bloquea_escritura_cruzada_de_eventos(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Cal9 C", "lab-cal9-iso-c", "admin@lab-cal9-iso-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Cal9 D", "lab-cal9-iso-d", "admin@lab-cal9-iso-d.dev")

    set_tenant_context(db, lab_a)
    evento_cruzado = EventoCalendario(
        id=uuid.uuid4(),
        laboratorio_id=lab_b,
        tipo="institucional",
        titulo="No debería poder escribirse",
        fecha=datetime(2026, 8, 1, tzinfo=UTC),
    )
    db.add(evento_cruzado)

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()
