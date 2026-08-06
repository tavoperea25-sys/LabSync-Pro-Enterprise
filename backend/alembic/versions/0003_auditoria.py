"""Auditoría: logs_auditoria (append-only) — RN-AUD-01, RN-AUD-02.

Se adelanta desde Sprint 10 porque RF-EQ-09 (historial de cambios de un
equipo) no puede construirse honestamente sin datos de auditoría reales —
ver docs/18-sprints.md, nota del Sprint 4. La pantalla dedicada
multi-módulo con filtros (RF-AUD-02/03) sigue siendo Sprint 10; aquí solo
se sienta la captura de datos, que para entonces ya llevará varios sprints
acumulando historial real en vez de arrancar vacía.

`laboratorio_id` se modela NOT NULL en esta migración porque todavía no
existe ningún flujo de plataforma (Superadmin, Sprint 10+) que escriba
auditoría fuera de un tenant — docs/14-base-de-datos.md contempla NULL
para ese caso futuro, pero implementarlo antes de que exista quien lo
use sería especular sobre un requisito que aún no es real.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

_ROL_APP = "labsync_app"


def upgrade() -> None:
    op.create_table(
        "logs_auditoria",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("ip_origen", sa.dialects.postgresql.INET(), nullable=True),
        sa.Column("modulo", sa.String(50), nullable=False),
        sa.Column("accion", sa.String(50), nullable=False),
        sa.Column("entidad_tipo", sa.String(50), nullable=False),
        sa.Column("entidad_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valor_anterior", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("valor_nuevo", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("ix_logs_auditoria_laboratorio", "logs_auditoria", ["laboratorio_id"])
    op.create_index(
        "ix_logs_auditoria_entidad", "logs_auditoria", ["laboratorio_id", "entidad_tipo", "entidad_id"]
    )

    op.execute("ALTER TABLE logs_auditoria ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE logs_auditoria FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_logs_auditoria ON logs_auditoria
          USING (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
          WITH CHECK (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )

    # RN-AUD-01: append-only incluso para el rol de aplicación — sin
    # UPDATE ni DELETE, a diferencia del resto de las tablas de negocio.
    op.execute(f"GRANT SELECT, INSERT ON logs_auditoria TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_table("logs_auditoria")
