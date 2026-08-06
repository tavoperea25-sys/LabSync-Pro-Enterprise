"""Gate crítico de CI para configuraciones_laboratorio — mismo patrón que
tests/test_reportes_isolation.py."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.configuracion.infrastructure.models import ConfiguracionLaboratorio


def _crear_config_directo(db: Session, laboratorio_id: uuid.UUID, umbral: int) -> None:
    db.add(ConfiguracionLaboratorio(laboratorio_id=laboratorio_id, umbral_alerta_calibracion_dias=umbral))
    db.commit()


def test_rls_bloquea_lectura_de_configuracion_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Cfg A", "lab-cfg-a", "admin@lab-cfg-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Cfg B", "lab-cfg-b", "admin@lab-cfg-b.dev")

    set_tenant_context(db, lab_a)
    _crear_config_directo(db, lab_a, 11)

    set_tenant_context(db, lab_b)
    _crear_config_directo(db, lab_b, 22)

    set_tenant_context(db, lab_a)
    umbrales_desde_a = {c.umbral_alerta_calibracion_dias for c in db.query(ConfiguracionLaboratorio).all()}
    assert umbrales_desde_a == {11}

    set_tenant_context(db, lab_b)
    umbrales_desde_b = {c.umbral_alerta_calibracion_dias for c in db.query(ConfiguracionLaboratorio).all()}
    assert umbrales_desde_b == {22}


def test_rls_bloquea_escritura_cruzada_de_configuracion(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Cfg C", "lab-cfg-c", "admin@lab-cfg-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Cfg D", "lab-cfg-d", "admin@lab-cfg-d.dev")

    set_tenant_context(db, lab_a)
    fila_cruzada = ConfiguracionLaboratorio(laboratorio_id=lab_b, umbral_alerta_calibracion_dias=99)
    db.add(fila_cruzada)

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()
