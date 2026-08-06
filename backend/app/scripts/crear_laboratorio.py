"""Alta de un nuevo laboratorio (tenant) — onboarding manual v1.

`docs/17-roadmap.md` (Fase 5) pide "proceso de alta de nuevos laboratorios,
aunque sea gestionado manualmente en v1" — este script es esa versión
manual: lo ejecuta un operador con acceso al servidor, no un usuario final
ni un Superadmin con rol propio (ese rol no existe en el sistema y no se
construye aquí sin evidencia de que se necesite, ver
`00-analisis-critico-y-recomendaciones.md`).

A diferencia de `app/seeds/seed_dev_tenant.py` (solo desarrollo, datos de
ejemplo, bloqueado en producción), este script SÍ está pensado para
producción: no siembra categorías/áreas de ejemplo — el nuevo laboratorio
las configura por su cuenta vía RF-CFG-05 (módulo Configuración, Sprint 12)
una vez que su Administrador inicia sesión.

Uso:
    python -m app.scripts.crear_laboratorio \
        --nombre "Laboratorio de Salud Pública del Cesar" \
        --slug lsp-cesar \
        --admin-nombre "Nombre Apellido" \
        --admin-correo admin@ejemplo.gov.co \
        [--admin-password 'Opcional123!Segura']

Si no se pasa `--admin-password`, se genera una aleatoria que cumple la
política de contraseña por defecto y se imprime UNA sola vez — no se
guarda en ningún lado. El nuevo Administrador debe cambiarla en su primer
login (`debe_cambiar_password=True`, mismo criterio que RF-USR-04)."""

from __future__ import annotations

import argparse
import re
import secrets
import string
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, set_tenant_context
from app.core.password_policy import PasswordNoCumplePolitica, validar_password
from app.core.security import hash_password
from app.modules.auth.infrastructure.models import Laboratorio, Rol, Usuario, UsuarioRol

_PATRON_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_ALFABETO_PASSWORD = string.ascii_letters + string.digits + "!@#$%^&*"


class ErrorOnboarding(Exception):
    pass


def _generar_password_temporal() -> str:
    while True:
        candidata = "".join(secrets.choice(_ALFABETO_PASSWORD) for _ in range(16))
        try:
            validar_password(candidata)
        except PasswordNoCumplePolitica:
            continue  # improbable con 16 caracteres del alfabeto elegido, pero se reintenta si pasa
        return candidata


def crear_laboratorio(
    db: Session, *, nombre: str, slug: str, admin_nombre: str, admin_correo: str, admin_password: str | None
) -> tuple[Laboratorio, Usuario, str]:
    if not _PATRON_SLUG.match(slug):
        raise ErrorOnboarding(
            f"Slug inválido: '{slug}'. Solo minúsculas, dígitos y guiones (ej. 'lsp-cesar')."
        )
    if db.execute(select(Laboratorio.id).where(Laboratorio.slug == slug)).first() is not None:
        raise ErrorOnboarding(f"Ya existe un laboratorio con slug '{slug}'.")

    password = admin_password or _generar_password_temporal()
    try:
        validar_password(password)
    except PasswordNoCumplePolitica as exc:
        raise ErrorOnboarding(
            f"La contraseña no cumple la política: {', '.join(exc.detalles['motivos'])}"
        ) from exc

    laboratorio = Laboratorio(id=uuid.uuid4(), nombre=nombre, slug=slug)
    db.add(laboratorio)
    db.flush()

    # A partir de aquí las escrituras son sobre tablas con RLS — hay que
    # fijar el contexto de tenant como haría cualquier request autenticado
    # (ver app/core/database.py::set_tenant_context).
    set_tenant_context(db, laboratorio.id)

    rol_admin = db.execute(
        select(Rol).where(Rol.nombre == "administrador", Rol.laboratorio_id.is_(None))
    ).scalar_one_or_none()
    if rol_admin is None:
        raise ErrorOnboarding(
            "El rol 'administrador' no existe — ejecuta primero " "`python -m app.seeds.seed_roles_permisos`."
        )

    if (
        db.execute(
            select(Usuario.id).where(Usuario.laboratorio_id == laboratorio.id, Usuario.correo == admin_correo)
        ).first()
        is not None
    ):
        raise ErrorOnboarding(f"Ya existe un usuario con correo '{admin_correo}' en este laboratorio.")

    admin = Usuario(
        id=uuid.uuid4(),
        laboratorio_id=laboratorio.id,
        correo=admin_correo,
        password_hash=hash_password(password),
        nombre_completo=admin_nombre,
        estado="activo",
        debe_cambiar_password=admin_password is None,
    )
    db.add(admin)
    db.flush()
    db.add(UsuarioRol(usuario_id=admin.id, rol_id=rol_admin.id, laboratorio_id=laboratorio.id))

    return laboratorio, admin, password


def main() -> None:
    parser = argparse.ArgumentParser(description="Alta de un nuevo laboratorio (tenant) en LabSync Pro.")
    parser.add_argument("--nombre", required=True, help="Nombre del laboratorio.")
    parser.add_argument(
        "--slug", required=True, help="Identificador corto único, usado en el login (URL-safe)."
    )
    parser.add_argument("--admin-nombre", required=True, help="Nombre completo del Administrador inicial.")
    parser.add_argument("--admin-correo", required=True, help="Correo del Administrador inicial.")
    parser.add_argument(
        "--admin-password",
        default=None,
        help="Opcional — si se omite, se genera una contraseña temporal aleatoria.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        laboratorio, admin, password = crear_laboratorio(
            db,
            nombre=args.nombre,
            slug=args.slug,
            admin_nombre=args.admin_nombre,
            admin_correo=args.admin_correo,
            admin_password=args.admin_password,
        )
        db.commit()
    except ErrorOnboarding as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

    print(f"Laboratorio creado: '{laboratorio.nombre}' (slug='{laboratorio.slug}')")
    print(f"Administrador: {admin.correo}")
    print(f"Contraseña temporal (guárdala ahora, no se vuelve a mostrar): {password}")
    if args.admin_password is None:
        print("Se generó automáticamente — el Administrador deberá cambiarla en su primer login.")


if __name__ == "__main__":
    main()
