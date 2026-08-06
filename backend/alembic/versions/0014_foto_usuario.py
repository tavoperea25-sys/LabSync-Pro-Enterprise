"""Fotografía de perfil de usuario — RF-CFG-01.

`docs/03-requerimientos-funcionales.md` (Módulo 14) pide explícitamente
"Editar datos de perfil propio (nombre, correo, contraseña, foto)" desde el
Sprint 12 — nombre/correo/contraseña ya estaban conectados, pero "foto" no
tenía ni columna en base de datos, a diferencia del logo institucional
(`laboratorios.logo_object_key`, mismo patrón que se replica aquí) o la
fotografía de equipos (`equipos.foto_url`, Sprint 24). Ver Sprint 25,
docs/18-sprints.md.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("foto_object_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "foto_object_key")
