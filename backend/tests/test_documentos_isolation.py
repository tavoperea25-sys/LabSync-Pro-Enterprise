"""Gate crítico de CI para las tablas del módulo Documentos — mismo patrón
que tests/test_equipos_isolation.py (docs/19-checklist.md)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.documentos.infrastructure.models import Carpeta, Documento


def _crear_carpeta_directa(db: Session, laboratorio_id: uuid.UUID, nombre: str) -> uuid.UUID:
    carpeta = Carpeta(id=uuid.uuid4(), laboratorio_id=laboratorio_id, nombre=nombre)
    db.add(carpeta)
    db.commit()
    return carpeta.id


def _crear_documento_directo(db: Session, laboratorio_id: uuid.UUID, nombre: str) -> None:
    db.add(Documento(id=uuid.uuid4(), laboratorio_id=laboratorio_id, nombre=nombre, estado="vigente"))
    db.commit()


def test_rls_bloquea_lectura_de_documentos_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Doc A", "lab-doc-a", "admin@lab-doc-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Doc B", "lab-doc-b", "admin@lab-doc-b.dev")

    set_tenant_context(db, lab_a)
    _crear_documento_directo(db, lab_a, "Doc A")

    set_tenant_context(db, lab_b)
    _crear_documento_directo(db, lab_b, "Doc B")

    set_tenant_context(db, lab_a)
    nombres_desde_a = {d.nombre for d in db.query(Documento).all()}
    assert nombres_desde_a == {"Doc A"}

    set_tenant_context(db, lab_b)
    nombres_desde_b = {d.nombre for d in db.query(Documento).all()}
    assert nombres_desde_b == {"Doc B"}


def test_rls_bloquea_lectura_de_carpetas_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Carp A", "lab-carp-a", "admin@lab-carp-a.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Carp B", "lab-carp-b", "admin@lab-carp-b.dev")

    set_tenant_context(db, lab_a)
    _crear_carpeta_directa(db, lab_a, "Carpeta A")

    set_tenant_context(db, lab_b)
    _crear_carpeta_directa(db, lab_b, "Carpeta B")

    set_tenant_context(db, lab_a)
    nombres_desde_a = {c.nombre for c in db.query(Carpeta).all()}
    assert nombres_desde_a == {"Carpeta A"}


def test_rls_bloquea_escritura_cruzada_de_documentos(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab Doc C", "lab-doc-c", "admin@lab-doc-c.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab Doc D", "lab-doc-d", "admin@lab-doc-d.dev")

    set_tenant_context(db, lab_a)
    documento_cruzado = Documento(
        id=uuid.uuid4(), laboratorio_id=lab_b, nombre="Intento cruzado", estado="vigente"
    )
    db.add(documento_cruzado)

    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()
