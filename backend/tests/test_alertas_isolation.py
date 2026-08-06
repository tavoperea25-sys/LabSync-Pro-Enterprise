"""Gate crítico de CI para las tablas `alertas`/`notificaciones_pendientes`
— mismo patrón que tests/test_calibraciones_isolation.py (docs/19-checklist.md)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.alertas.infrastructure.models import Alerta


def _crear_alerta_directa(db: Session, laboratorio_id: uuid.UUID) -> uuid.UUID:
    alerta_id = uuid.uuid4()
    db.add(
        Alerta(
            id=alerta_id,
            laboratorio_id=laboratorio_id,
            tipo="critica",
            origen_tipo="equipo",
            origen_id=uuid.uuid4(),
            mensaje="Prueba de aislamiento",
            estado="activa",
        )
    )
    db.commit()
    return alerta_id


def test_rls_bloquea_lectura_de_alertas_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Alt A", "lab-alt-a", "admin@lab-alt-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Alt B", "lab-alt-b", "admin@lab-alt-b.dev")

    set_tenant_context(db, lab_a)
    alerta_a = _crear_alerta_directa(db, lab_a)

    set_tenant_context(db, lab_b)
    _crear_alerta_directa(db, lab_b)

    set_tenant_context(db, lab_a)
    ids_desde_a = {a.id for a in db.query(Alerta).all()}
    assert ids_desde_a == {alerta_a}


def test_rls_bloquea_escritura_cruzada_de_alertas(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Alt C", "lab-alt-c", "admin@lab-alt-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Alt D", "lab-alt-d", "admin@lab-alt-d.dev")

    set_tenant_context(db, lab_a)
    alerta_cruzada = Alerta(
        id=uuid.uuid4(),
        laboratorio_id=lab_b,
        tipo="critica",
        origen_tipo="equipo",
        origen_id=uuid.uuid4(),
        mensaje="No debería poder escribirse",
        estado="activa",
    )
    db.add(alerta_cruzada)

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_no_se_puede_eliminar_una_alerta(db: Session, crear_laboratorio_con_admin):
    """El outbox y las alertas son de solo lectura/actualización a nivel de
    aplicación — sin DELETE otorgado, se preserva el historial completo
    para auditoría (mismo criterio que RN-CAL-02 en Calibraciones)."""
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Alt E", "lab-alt-e", "admin@lab-alt-e.dev")
    set_tenant_context(db, lab_a)
    _crear_alerta_directa(db, lab_a)

    with pytest.raises(ProgrammingError, match="permission denied"):
        db.execute(Alerta.__table__.delete())
        db.flush()
