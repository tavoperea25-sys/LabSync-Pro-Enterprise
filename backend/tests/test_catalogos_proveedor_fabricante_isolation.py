"""Gate crítico de CI para `proveedores`/`fabricantes` — Fase 2 de hojas de
vida (docs/25-diseno-tecnico-hojas-de-vida.md). Mismo patrón de RLS que
tests/test_equipos_isolation.py, más la FK compuesta
`equipos(proveedor_id/fabricante_id, laboratorio_id)` que Postgres evalúa
SIN pasar por RLS (hallazgo de Gustavo durante la revisión del diseño)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.equipos.infrastructure.models import Equipo, Fabricante, Proveedor


def _crear_proveedor_directo(db: Session, laboratorio_id: uuid.UUID, nombre: str) -> uuid.UUID:
    proveedor_id = uuid.uuid4()
    db.add(Proveedor(id=proveedor_id, laboratorio_id=laboratorio_id, nombre=nombre))
    db.commit()
    return proveedor_id


def _crear_fabricante_directo(db: Session, laboratorio_id: uuid.UUID, nombre: str) -> uuid.UUID:
    fabricante_id = uuid.uuid4()
    db.add(Fabricante(id=fabricante_id, laboratorio_id=laboratorio_id, nombre=nombre))
    db.commit()
    return fabricante_id


def test_rls_bloquea_lectura_de_proveedores_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Prov A", "lab-prov-iso-a", "admin@lab-prov-iso-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Prov B", "lab-prov-iso-b", "admin@lab-prov-iso-b.dev")

    set_tenant_context(db, lab_a)
    _crear_proveedor_directo(db, lab_a, "Proveedor A")

    set_tenant_context(db, lab_b)
    _crear_proveedor_directo(db, lab_b, "Proveedor B")

    set_tenant_context(db, lab_a)
    assert {p.nombre for p in db.query(Proveedor).all()} == {"Proveedor A"}

    set_tenant_context(db, lab_b)
    assert {p.nombre for p in db.query(Proveedor).all()} == {"Proveedor B"}


def test_rls_bloquea_escritura_cruzada_de_proveedores(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Prov C", "lab-prov-iso-c", "admin@lab-prov-iso-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Prov D", "lab-prov-iso-d", "admin@lab-prov-iso-d.dev")

    set_tenant_context(db, lab_a)
    db.add(Proveedor(id=uuid.uuid4(), laboratorio_id=lab_b, nombre="Intento cruzado"))

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_fk_compuesta_rechaza_proveedor_de_otro_laboratorio(db: Session, crear_laboratorio_con_admin):
    """La FK compuesta — no la RLS — es lo único que impide esto: un
    `laboratorio_id` legítimo del actor (pasa `WITH CHECK`) combinado con un
    `proveedor_id` real de OTRO laboratorio (viola la FK, porque no existe
    ninguna fila de `proveedores` con esa combinación exacta)."""
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Prov E", "lab-prov-iso-e", "admin@lab-prov-iso-e.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Prov F", "lab-prov-iso-f", "admin@lab-prov-iso-f.dev")

    set_tenant_context(db, lab_b)
    proveedor_b = _crear_proveedor_directo(db, lab_b, "Proveedor de B")

    set_tenant_context(db, lab_a)
    db.add(
        Equipo(
            id=uuid.uuid4(),
            laboratorio_id=lab_a,
            codigo_interno="EQ-FK-PROV",
            nombre="Intento FK cruzada",
            estado_operativo="operativo",
            proveedor_id=proveedor_b,
        )
    )

    with pytest.raises(IntegrityError, match="fk_equipos_proveedor_lab"):
        db.flush()


def test_rls_bloquea_lectura_de_fabricantes_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Fab A", "lab-fab-iso-a", "admin@lab-fab-iso-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Fab B", "lab-fab-iso-b", "admin@lab-fab-iso-b.dev")

    set_tenant_context(db, lab_a)
    _crear_fabricante_directo(db, lab_a, "Fabricante A")

    set_tenant_context(db, lab_b)
    _crear_fabricante_directo(db, lab_b, "Fabricante B")

    set_tenant_context(db, lab_a)
    assert {f.nombre for f in db.query(Fabricante).all()} == {"Fabricante A"}

    set_tenant_context(db, lab_b)
    assert {f.nombre for f in db.query(Fabricante).all()} == {"Fabricante B"}


def test_rls_bloquea_escritura_cruzada_de_fabricantes(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Fab C", "lab-fab-iso-c", "admin@lab-fab-iso-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Fab D", "lab-fab-iso-d", "admin@lab-fab-iso-d.dev")

    set_tenant_context(db, lab_a)
    db.add(Fabricante(id=uuid.uuid4(), laboratorio_id=lab_b, nombre="Intento cruzado"))

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_fk_compuesta_rechaza_fabricante_de_otro_laboratorio(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Fab E", "lab-fab-iso-e", "admin@lab-fab-iso-e.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Fab F", "lab-fab-iso-f", "admin@lab-fab-iso-f.dev")

    set_tenant_context(db, lab_b)
    fabricante_b = _crear_fabricante_directo(db, lab_b, "Fabricante de B")

    set_tenant_context(db, lab_a)
    db.add(
        Equipo(
            id=uuid.uuid4(),
            laboratorio_id=lab_a,
            codigo_interno="EQ-FK-FAB",
            nombre="Intento FK cruzada",
            estado_operativo="operativo",
            fabricante_id=fabricante_b,
        )
    )

    with pytest.raises(IntegrityError, match="fk_equipos_fabricante_lab"):
        db.flush()
