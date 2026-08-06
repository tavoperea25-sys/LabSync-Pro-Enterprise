"""Mapeo configurable tipo→estado_operativo de mantenimiento — RN-MANT-01.

`mantenimientos/domain/entities.py::estado_operativo_para_tipo` documentaba
desde el Sprint 8 que la asignación era fija "en ausencia de un módulo de
Configuración (Sprint 12)" — ese módulo ya existe, esta migración cierra
el loop añadiendo la columna que le faltaba a `configuraciones_laboratorio`."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "configuraciones_laboratorio",
        sa.Column("mapeo_estados_mantenimiento_json", sa.dialects.postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("configuraciones_laboratorio", "mapeo_estados_mantenimiento_json")
