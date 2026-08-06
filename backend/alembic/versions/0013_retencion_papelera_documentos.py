"""Retención configurable de la papelera de documentos — RN-DOC-03.

`docs/07-reglas-de-negocio.md` documenta desde el Sprint 5 que un documento
en papelera "puede restaurarse dentro de una ventana configurable (por
defecto 30 días); pasado ese plazo, pasa a purga automática programada, no
eliminación inmediata silenciosa." Ni la ventana ni la purga estaban
conectadas en el código — `restaurar()` no tenía límite de tiempo y no
existía ningún job de purga (ver Sprint 19, docs/18-sprints.md).

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-03
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuraciones_laboratorio",
        sa.Column(
            "dias_retencion_papelera_documentos",
            sa.Integer(),
            nullable=False,
            server_default="30",
        ),
    )


def downgrade() -> None:
    op.drop_column("configuraciones_laboratorio", "dias_retencion_papelera_documentos")
