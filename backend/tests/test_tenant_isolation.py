"""Gate crítico de CI — ver docs/19-checklist.md sección Seguridad y
docs/16-seguridad.md sección 3: ningún dato de un laboratorio debe ser
visible ni modificable desde el contexto de otro, sin excepción."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.auth.infrastructure.models import Usuario


def test_rls_bloquea_lectura_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, correo_a, _ = crear_laboratorio_con_admin("Lab A", "lab-a", "admin@lab-a.dev")
    lab_b, _, correo_b, _ = crear_laboratorio_con_admin("Lab B", "lab-b", "admin@lab-b.dev")

    set_tenant_context(db, lab_a)
    correos_visibles_desde_a = {u.correo for u in db.query(Usuario).all()}

    assert correo_a in correos_visibles_desde_a
    assert correo_b not in correos_visibles_desde_a

    set_tenant_context(db, lab_b)
    correos_visibles_desde_b = {u.correo for u in db.query(Usuario).all()}

    assert correo_b in correos_visibles_desde_b
    assert correo_a not in correos_visibles_desde_b


def test_rls_bloquea_lectura_sin_contexto_de_tenant(db: Session, crear_laboratorio_con_admin):
    crear_laboratorio_con_admin("Lab C", "lab-c", "admin@lab-c.dev")

    set_tenant_context(db, None)  # sin contexto — debe fallar cerrado (fail-closed)
    resultados = db.query(Usuario).all()

    assert resultados == []


def test_rls_bloquea_escritura_cruzada_entre_tenants(db: Session, crear_laboratorio_con_admin):
    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab D", "lab-d", "admin@lab-d.dev")
    lab_b, _, _, _ = crear_laboratorio_con_admin("Lab E", "lab-e", "admin@lab-e.dev")

    set_tenant_context(db, lab_a)

    # Intento de crear un usuario "para" el laboratorio B mientras el
    # contexto activo de la sesión es A — la política WITH CHECK debe
    # rechazarlo, no solo ocultarlo en lecturas posteriores.
    usuario_cruzado = Usuario(
        id=uuid.uuid4(),
        laboratorio_id=lab_b,
        correo="intruso@lab-e.dev",
        password_hash="hash-irrelevante",
        nombre_completo="Intento cruzado",
        estado="activo",
        debe_cambiar_password=False,
    )
    db.add(usuario_cruzado)

    # Postgres rechaza la violación de una política RLS con
    # InsufficientPrivilege (mapeado por SQLAlchemy a ProgrammingError),
    # no con una violación de constraint (IntegrityError) — son mecanismos
    # de rechazo distintos a nivel de motor.
    with pytest.raises(ProgrammingError, match="row-level security policy"):
        db.flush()


def test_rls_roles_de_sistema_visibles_en_todos_los_tenants(db: Session, crear_laboratorio_con_admin):
    from app.modules.auth.infrastructure.models import Rol

    lab_a, _, _, _ = crear_laboratorio_con_admin("Lab F", "lab-f", "admin@lab-f.dev")

    set_tenant_context(db, lab_a)
    nombres_roles = {r.nombre for r in db.query(Rol).all()}

    assert "administrador" in nombres_roles
    assert "tecnico" in nombres_roles
