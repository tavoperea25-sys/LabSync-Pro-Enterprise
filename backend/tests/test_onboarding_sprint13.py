"""Pruebas de Sprint 13: script de alta de laboratorio (onboarding manual v1)
— app/scripts/crear_laboratorio.py."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.core.security import verificar_password
from app.modules.auth.infrastructure.models import Usuario
from app.scripts.crear_laboratorio import ErrorOnboarding, crear_laboratorio


def test_crear_laboratorio_exitoso_con_password_generada(db: Session) -> None:
    sufijo = uuid.uuid4().hex[:8]
    laboratorio, admin, password = crear_laboratorio(
        db,
        nombre="Laboratorio Onboarding Test",
        slug=f"onb-{sufijo}",
        admin_nombre="Admin Onboarding",
        admin_correo=f"admin-{sufijo}@onboarding.dev",
        admin_password=None,
    )
    db.commit()

    assert laboratorio.slug == f"onb-{sufijo}"
    assert admin.debe_cambiar_password is True
    assert len(password) >= 10

    set_tenant_context(db, laboratorio.id)
    fila = db.get(Usuario, admin.id)
    assert fila is not None
    assert verificar_password(password, fila.password_hash)
    assert fila.correo == f"admin-{sufijo}@onboarding.dev"


def test_crear_laboratorio_con_password_explicita_no_fuerza_cambio(db: Session) -> None:
    sufijo = uuid.uuid4().hex[:8]
    _laboratorio, admin, password = crear_laboratorio(
        db,
        nombre="Laboratorio Onboarding Explicito",
        slug=f"onb-exp-{sufijo}",
        admin_nombre="Admin",
        admin_correo=f"admin-exp-{sufijo}@onboarding.dev",
        admin_password="Cl4veExplicita!Segura",
    )
    db.commit()

    assert password == "Cl4veExplicita!Segura"
    assert admin.debe_cambiar_password is False


def test_crear_laboratorio_slug_duplicado_falla(db: Session, crear_laboratorio_con_admin) -> None:
    _lab_id, _admin_id, _correo, _password = crear_laboratorio_con_admin(
        "Lab Existente", "onb-duplicado", "admin@onb-duplicado.dev"
    )
    db.commit()

    with pytest.raises(ErrorOnboarding, match="Ya existe un laboratorio"):
        crear_laboratorio(
            db,
            nombre="Otro nombre",
            slug="onb-duplicado",
            admin_nombre="Admin",
            admin_correo="otro@onboarding.dev",
            admin_password="Cl4veSegura!2026",
        )


def test_crear_laboratorio_slug_invalido_falla(db: Session) -> None:
    with pytest.raises(ErrorOnboarding, match="Slug inválido"):
        crear_laboratorio(
            db,
            nombre="Nombre",
            slug="Slug Con Espacios",
            admin_nombre="Admin",
            admin_correo=f"admin-{uuid.uuid4().hex[:8]}@onboarding.dev",
            admin_password="Cl4veSegura!2026",
        )


def test_crear_laboratorio_password_no_cumple_politica_falla(db: Session) -> None:
    with pytest.raises(ErrorOnboarding, match="no cumple la política"):
        crear_laboratorio(
            db,
            nombre="Nombre",
            slug=f"onb-badpw-{uuid.uuid4().hex[:8]}",
            admin_nombre="Admin",
            admin_correo=f"admin-{uuid.uuid4().hex[:8]}@onboarding.dev",
            admin_password="corta",
        )
