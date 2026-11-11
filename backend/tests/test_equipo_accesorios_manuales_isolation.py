"""Gate crítico de CI para `equipo_accesorios`/`equipo_manuales` — Fase 2 de
hojas de vida (docs/25-diseno-tecnico-hojas-de-vida.md). Mismo patrón que
tests/test_equipos_isolation.py, más la FK compuesta
`(equipo_id, laboratorio_id) -> equipos(id, laboratorio_id)`."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.equipos.infrastructure.models import Equipo, EquipoAccesorio, EquipoManual


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


def test_rls_bloquea_lectura_de_accesorios_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Acc A", "lab-acc-iso-a", "admin@lab-acc-iso-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Acc B", "lab-acc-iso-b", "admin@lab-acc-iso-b.dev")

    set_tenant_context(db, lab_a)
    equipo_a = _crear_equipo_directo(db, lab_a, "EQ-ACC-A")
    # `_crear_equipo_directo` ya hizo `commit()` — `SET LOCAL` es por
    # transacción, así que hay que fijarlo de nuevo antes de la siguiente
    # escritura.
    set_tenant_context(db, lab_a)
    db.add(
        EquipoAccesorio(id=uuid.uuid4(), laboratorio_id=lab_a, equipo_id=equipo_a, descripcion="Accesorio A")
    )
    db.commit()

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-ACC-B")
    set_tenant_context(db, lab_b)
    db.add(
        EquipoAccesorio(id=uuid.uuid4(), laboratorio_id=lab_b, equipo_id=equipo_b, descripcion="Accesorio B")
    )
    db.commit()

    set_tenant_context(db, lab_a)
    assert {a.descripcion for a in db.query(EquipoAccesorio).all()} == {"Accesorio A"}

    set_tenant_context(db, lab_b)
    assert {a.descripcion for a in db.query(EquipoAccesorio).all()} == {"Accesorio B"}


def test_rls_bloquea_escritura_cruzada_de_accesorios(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Acc C", "lab-acc-iso-c", "admin@lab-acc-iso-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Acc D", "lab-acc-iso-d", "admin@lab-acc-iso-d.dev")

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-ACC-D")

    set_tenant_context(db, lab_a)
    db.add(
        EquipoAccesorio(
            id=uuid.uuid4(), laboratorio_id=lab_b, equipo_id=equipo_b, descripcion="Intento cruzado"
        )
    )

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_fk_compuesta_rechaza_accesorio_de_equipo_de_otro_laboratorio(
    db: Session, crear_laboratorio_con_admin
):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Acc E", "lab-acc-iso-e", "admin@lab-acc-iso-e.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Acc F", "lab-acc-iso-f", "admin@lab-acc-iso-f.dev")

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-ACC-F")

    set_tenant_context(db, lab_a)
    db.add(
        EquipoAccesorio(
            id=uuid.uuid4(), laboratorio_id=lab_a, equipo_id=equipo_b, descripcion="Intento FK cruzada"
        )
    )

    with pytest.raises(IntegrityError, match="fk_equipo_accesorios_equipo_lab"):
        db.flush()


def test_rls_bloquea_lectura_de_manuales_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Man A", "lab-man-iso-a", "admin@lab-man-iso-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Man B", "lab-man-iso-b", "admin@lab-man-iso-b.dev")

    set_tenant_context(db, lab_a)
    equipo_a = _crear_equipo_directo(db, lab_a, "EQ-MAN-A")
    # `_crear_equipo_directo` ya hizo `commit()` — `SET LOCAL` es por
    # transacción, así que hay que fijarlo de nuevo antes de la siguiente
    # escritura.
    set_tenant_context(db, lab_a)
    db.add(
        EquipoManual(
            id=uuid.uuid4(),
            laboratorio_id=lab_a,
            equipo_id=equipo_a,
            tipo="manual_operacion",
            disponible=True,
        )
    )
    db.commit()

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-MAN-B")
    set_tenant_context(db, lab_b)
    db.add(
        EquipoManual(
            id=uuid.uuid4(), laboratorio_id=lab_b, equipo_id=equipo_b, tipo="manual_servicio", disponible=True
        )
    )
    db.commit()

    set_tenant_context(db, lab_a)
    assert {m.tipo for m in db.query(EquipoManual).all()} == {"manual_operacion"}

    set_tenant_context(db, lab_b)
    assert {m.tipo for m in db.query(EquipoManual).all()} == {"manual_servicio"}


def test_rls_bloquea_escritura_cruzada_de_manuales(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Man C", "lab-man-iso-c", "admin@lab-man-iso-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Man D", "lab-man-iso-d", "admin@lab-man-iso-d.dev")

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-MAN-D")

    set_tenant_context(db, lab_a)
    db.add(
        EquipoManual(
            id=uuid.uuid4(),
            laboratorio_id=lab_b,
            equipo_id=equipo_b,
            tipo="manual_operacion",
            disponible=True,
        )
    )

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_fk_compuesta_rechaza_manual_de_equipo_de_otro_laboratorio(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Man E", "lab-man-iso-e", "admin@lab-man-iso-e.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Man F", "lab-man-iso-f", "admin@lab-man-iso-f.dev")

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-MAN-F")

    set_tenant_context(db, lab_a)
    db.add(
        EquipoManual(
            id=uuid.uuid4(),
            laboratorio_id=lab_a,
            equipo_id=equipo_b,
            tipo="manual_operacion",
            disponible=True,
        )
    )

    with pytest.raises(IntegrityError, match="fk_equipo_manuales_equipo_lab"):
        db.flush()
