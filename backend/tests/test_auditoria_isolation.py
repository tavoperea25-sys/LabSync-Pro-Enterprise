"""Gate crítico de CI para logs_auditoria — mismo patrón que
tests/test_tenant_isolation.py y tests/test_equipos_isolation.py."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.auditoria.infrastructure.models import LogAuditoria


def _registrar_log(db: Session, laboratorio_id: uuid.UUID, modulo: str) -> None:
    db.add(
        LogAuditoria(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            usuario_id=None,
            modulo=modulo,
            accion="crear",
            entidad_tipo="prueba",
            entidad_id=uuid.uuid4(),
        )
    )
    db.commit()


def test_rls_bloquea_lectura_de_auditoria_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Aud A", "lab-aud-a", "admin@lab-aud-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Aud B", "lab-aud-b", "admin@lab-aud-b.dev")

    set_tenant_context(db, lab_a)
    _registrar_log(db, lab_a, "modulo-a")

    set_tenant_context(db, lab_b)
    _registrar_log(db, lab_b, "modulo-b")

    set_tenant_context(db, lab_a)
    modulos_desde_a = {log.modulo for log in db.query(LogAuditoria).all()}
    assert modulos_desde_a == {"modulo-a"}


def test_no_se_puede_editar_ni_borrar_auditoria(db: Session, crear_laboratorio_con_admin):
    """RN-AUD-01: append-only incluso a nivel de permisos de base de datos —
    el rol de aplicación no tiene UPDATE ni DELETE sobre esta tabla."""
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Aud C", "lab-aud-c", "admin@lab-aud-c.dev")
    set_tenant_context(db, lab_a)
    _registrar_log(db, lab_a, "modulo-c")

    with pytest.raises(ProgrammingError, match="permission denied"):
        db.execute(LogAuditoria.__table__.update().values(modulo="editado"))
        db.flush()
