"""Código QR: qr_tokens, incidencias_qr — docs/03-requerimientos-funcionales.md
Módulo 13 (RF-QR-01 a 04).

Decisión deliberada de RLS para `qr_tokens`: esta tabla NO lleva política
RLS, a diferencia de casi todo el resto del esquema. Se consulta desde un
endpoint público sin autenticación (RF-QR-02), por token exacto — nunca se
lista ni se filtra por tenant. El límite de seguridad real es "conocer el
token aleatorio de 64 caracteres" (RN-QR-01), no el aislamiento por
laboratorio_id. Se denormaliza `laboratorio_id` en la tabla igualmente
(mismo patrón que `sesiones`/`usuarios_roles`) para que, una vez resuelto
el token, el código pueda fijar `app.current_tenant_id` correctamente
antes de consultar `equipos` (esa sí, protegida por RLS) — resuelve el
mismo problema de "huevo y gallina" que el refresh token de Auth
(ver app/core/security.py).

`incidencias_qr` sí lleva RLS estándar: se escribe desde el flujo público
(tras resolver el tenant vía qr_tokens) y se lee desde la app autenticada
(Mantenimientos, Sprint 8, como solicitudes pendientes de triage).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

_ROL_APP = "labsync_app"


def upgrade() -> None:
    op.create_table(
        "qr_tokens",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "equipo_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("equipos.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("revocado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_qr_tokens_token", "qr_tokens", ["token"])

    op.create_table(
        "incidencias_qr",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "equipo_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("equipos.id"),
            nullable=False,
        ),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("contacto_nombre", sa.String(150), nullable=True),
        sa.Column("contacto_medio", sa.String(150), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_incidencias_qr_laboratorio", "incidencias_qr", ["laboratorio_id"])

    op.execute("ALTER TABLE incidencias_qr ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE incidencias_qr FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_incidencias_qr ON incidencias_qr
          USING (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
          WITH CHECK (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )

    # qr_tokens sin RLS (ver docstring) — el rol de app igual necesita
    # permisos de tabla para poder ejecutar el SELECT/INSERT.
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON qr_tokens TO {_ROL_APP}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON incidencias_qr TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_table("incidencias_qr")
    op.drop_table("qr_tokens")
