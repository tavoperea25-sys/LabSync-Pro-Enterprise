"""Columnas `revocada_en` y `duracion_dias` en `sesiones` — revisión de
seguridad del módulo Auth, hallazgos 1 y 2.

`revocada_en` (hallazgo 1): `AuthService.refresh` marcaba una sesión como
`revocada=True` al rotarla, pero no guardaba CUÁNDO. Sin esa marca de
tiempo no hay forma de distinguir "refresh token reusado por un atacante
minutos/horas después de rotado" (robo real) de "dos peticiones del mismo
usuario llegaron casi a la vez y la segunda vio la sesión ya rotada por la
primera" (carrera benigna — varias pestañas, reintento de red, etc.). Antes
de este cambio, ambos casos revocaban TODAS las sesiones del usuario.

`duracion_dias` (hallazgo 2): "Recordarme" en /login solo cambiaba el
`max_age` de la cookie (30 días vs 7) en el router, pero la fila de
`sesiones` siempre se creaba con `expira_en = ahora + refresh_token_expira_dias`
(7 días fijo, ignorando `recordarme`), y cada `/refresh` volvía a fijar la
cookie en 7 días sin importar la preferencia original. Guardar la duración
elegida en la propia sesión permite que sobreviva a rotaciones sucesivas.

`NOT NULL DEFAULT 7` en `duracion_dias`: las filas existentes no tienen
forma de saber qué duración se usó originalmente — 7 días es el valor no
"recordado" (el más restrictivo), así que es el default seguro para datos
preexistentes. Las filas nuevas siempre lo fijan explícitamente
(`SesionRepositorySQLAlchemy.crear`), nunca dependen de este default.

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-05
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sesiones", sa.Column("revocada_en", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "sesiones",
        sa.Column("duracion_dias", sa.Integer(), nullable=False, server_default="7"),
    )


def downgrade() -> None:
    op.drop_column("sesiones", "duracion_dias")
    op.drop_column("sesiones", "revocada_en")
