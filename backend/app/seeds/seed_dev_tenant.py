"""Crea un laboratorio (tenant) y un usuario Administrador de ejemplo para
desarrollo local. NUNCA ejecutar en producción — ver guardas de entorno.

Uso: `python -m app.seeds.seed_dev_tenant` (ver README del backend).
"""

from __future__ import annotations

import sys
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, set_tenant_context
from app.core.security import hash_password
from app.modules.auth.infrastructure.models import Laboratorio, Rol, Usuario, UsuarioRol
from app.modules.equipos.infrastructure.models import Area, CategoriaEquipo

SLUG_DEV = "demo"
CORREO_ADMIN_DEV = "admin@demo.labsync.dev"
PASSWORD_ADMIN_DEV = "CambiarEn123!"

CATEGORIAS_DEMO = ["Microbiología", "Bioquímica", "Hematología", "Virología"]
AREAS_DEMO = ["Laboratorio Central", "Toma de Muestras", "Bioseguridad"]


def ejecutar() -> None:
    settings = get_settings()
    if settings.entorno == "produccion":
        print("Este seed es solo para desarrollo — abortando (entorno=produccion).", file=sys.stderr)
        sys.exit(1)

    db: Session = SessionLocal()
    try:
        laboratorio = db.execute(
            select(Laboratorio).where(Laboratorio.slug == SLUG_DEV)
        ).scalar_one_or_none()
        if laboratorio is None:
            laboratorio = Laboratorio(id=uuid.uuid4(), nombre="Laboratorio Demo", slug=SLUG_DEV)
            db.add(laboratorio)
            db.flush()

        set_tenant_context(db, laboratorio.id)

        usuario_existente = db.execute(
            select(Usuario).where(
                Usuario.laboratorio_id == laboratorio.id, Usuario.correo == CORREO_ADMIN_DEV
            )
        ).scalar_one_or_none()

        if usuario_existente is None:
            rol_admin = db.execute(
                select(Rol).where(Rol.nombre == "administrador", Rol.laboratorio_id.is_(None))
            ).scalar_one_or_none()
            if rol_admin is None:
                raise RuntimeError(
                    "El rol 'administrador' no existe — ejecuta primero "
                    "`python -m app.seeds.seed_roles_permisos`."
                )

            usuario = Usuario(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio.id,
                correo=CORREO_ADMIN_DEV,
                password_hash=hash_password(PASSWORD_ADMIN_DEV),
                nombre_completo="Administrador Demo",
                estado="activo",
                debe_cambiar_password=False,
            )
            db.add(usuario)
            db.flush()
            db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol_admin.id, laboratorio_id=laboratorio.id))

        categorias_existentes = set(db.execute(select(CategoriaEquipo.nombre)).scalars())
        for nombre in CATEGORIAS_DEMO:
            if nombre not in categorias_existentes:
                db.add(CategoriaEquipo(id=uuid.uuid4(), laboratorio_id=laboratorio.id, nombre=nombre))

        areas_existentes = set(db.execute(select(Area.nombre)).scalars())
        for nombre in AREAS_DEMO:
            if nombre not in areas_existentes:
                db.add(Area(id=uuid.uuid4(), laboratorio_id=laboratorio.id, nombre=nombre))

        db.commit()
        print(f"Laboratorio demo listo: slug='{SLUG_DEV}'")
        print(f"Usuario administrador: {CORREO_ADMIN_DEV} / {PASSWORD_ADMIN_DEV}")
    finally:
        db.close()


if __name__ == "__main__":
    ejecutar()
