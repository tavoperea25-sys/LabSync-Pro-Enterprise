"""Bloqueo de activación por categoría — RN-EQ-03.

`docs/07-reglas-de-negocio.md` documenta desde el Sprint 3 que "un equipo no
puede pasar a estado 'Operativo' si tiene una calibración en estado 'Vencido'
marcada como crítica para su operación (configurable por categoría de
equipo)" — la regla nunca se conectó en el código porque `categorias_equipo`
no tenía dónde guardar esa configuración. Esta migración añade la columna
que le faltaba (ver Sprint 17, docs/18-sprints.md).

`DEFAULT false` a propósito: activar el bloqueo por defecto para categorías
ya existentes cambiaría de golpe el comportamiento de equipos que hoy se
reactivan sin problema — el Administrador debe optar explícitamente por
categoría, no heredar una restricción nueva sin haberla configurado.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-02
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "categorias_equipo",
        sa.Column(
            "bloquea_activacion_si_calibracion_vencida",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("categorias_equipo", "bloquea_activacion_si_calibracion_vencida")
