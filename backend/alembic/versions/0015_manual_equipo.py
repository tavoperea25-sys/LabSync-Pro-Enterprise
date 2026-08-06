"""Manual de usuario de un equipo — RF-EQ-01.

`docs/03-requerimientos-funcionales.md` (Módulo 3, Sprint 3) pide
explícitamente "manual de usuario (archivo)" como campo de la ficha técnica,
con validación de tipo (PDF) descrita en el propio requisito — igual que
"fotografía" (Sprint 24), no tenía columna en base de datos. Ver Sprint 26,
docs/18-sprints.md.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("equipos", sa.Column("manual_object_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("equipos", "manual_object_key")
