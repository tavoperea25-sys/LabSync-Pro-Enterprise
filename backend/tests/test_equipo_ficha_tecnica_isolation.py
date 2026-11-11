"""Gate crítico de CI para `equipo_ficha_tecnica` — Fase 2 de hojas de vida
(docs/25-diseno-tecnico-hojas-de-vida.md). Mismo patrón que
tests/test_equipos_isolation.py, más la FK compuesta
`equipo_ficha_tecnica(equipo_id, laboratorio_id) -> equipos(id, laboratorio_id)`."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.equipos.infrastructure.models import Equipo, EquipoFichaTecnica


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


def test_rls_bloquea_lectura_de_ficha_tecnica_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin(
        "Lab Ficha A", "lab-ficha-iso-a", "admin@lab-ficha-iso-a.dev"
    )
    lab_b, _, _, _ = crear_laboratorio_con_admin(
        "Lab Ficha B", "lab-ficha-iso-b", "admin@lab-ficha-iso-b.dev"
    )

    set_tenant_context(db, lab_a)
    equipo_a = _crear_equipo_directo(db, lab_a, "EQ-FICHA-A")
    # `_crear_equipo_directo` ya hizo `commit()` — `SET LOCAL` es por
    # transacción (docs/`set_tenant_context`), así que hay que fijarlo de
    # nuevo antes de la siguiente escritura.
    set_tenant_context(db, lab_a)
    db.add(EquipoFichaTecnica(equipo_id=equipo_a, laboratorio_id=lab_a, voltaje="120V", datos_adicionales={}))
    db.commit()

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-FICHA-B")
    set_tenant_context(db, lab_b)
    db.add(EquipoFichaTecnica(equipo_id=equipo_b, laboratorio_id=lab_b, voltaje="220V", datos_adicionales={}))
    db.commit()

    set_tenant_context(db, lab_a)
    assert {f.voltaje for f in db.query(EquipoFichaTecnica).all()} == {"120V"}

    set_tenant_context(db, lab_b)
    assert {f.voltaje for f in db.query(EquipoFichaTecnica).all()} == {"220V"}


def test_rls_bloquea_escritura_cruzada_de_ficha_tecnica(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin(
        "Lab Ficha C", "lab-ficha-iso-c", "admin@lab-ficha-iso-c.dev"
    )
    lab_b, _, _, _ = crear_laboratorio_con_admin(
        "Lab Ficha D", "lab-ficha-iso-d", "admin@lab-ficha-iso-d.dev"
    )

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-FICHA-D")

    set_tenant_context(db, lab_a)
    # Fila VÁLIDA para `equipo_b` (satisface la FK: equipo_b pertenece a
    # lab_b), escrita mientras el actor es lab_a — solo la RLS lo bloquea.
    db.add(EquipoFichaTecnica(equipo_id=equipo_b, laboratorio_id=lab_b, datos_adicionales={}))

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_fk_compuesta_rechaza_ficha_tecnica_de_equipo_de_otro_laboratorio(
    db: Session, crear_laboratorio_con_admin
):
    """La FK compuesta — no la RLS — es lo único que impide esto: un
    `laboratorio_id` legítimo del actor (pasa `WITH CHECK`) combinado con un
    `equipo_id` real de OTRO laboratorio (viola la FK)."""
    lab_a, _, _, _ = crear_laboratorio_con_admin(
        "Lab Ficha E", "lab-ficha-iso-e", "admin@lab-ficha-iso-e.dev"
    )
    lab_b, _, _, _ = crear_laboratorio_con_admin(
        "Lab Ficha F", "lab-ficha-iso-f", "admin@lab-ficha-iso-f.dev"
    )

    set_tenant_context(db, lab_b)
    equipo_b = _crear_equipo_directo(db, lab_b, "EQ-FICHA-F")

    set_tenant_context(db, lab_a)
    db.add(EquipoFichaTecnica(equipo_id=equipo_b, laboratorio_id=lab_a, datos_adicionales={}))

    with pytest.raises(IntegrityError, match="fk_equipo_ficha_tecnica_equipo_lab"):
        db.flush()
