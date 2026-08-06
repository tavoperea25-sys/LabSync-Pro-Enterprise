"""Mantenimientos + Alertas + outbox — RF-MANT-01 a 05, RF-ALT-01 a 06
(Sprint 8, docs/18-sprints.md).

`alertas` lleva la restricción única lógica de RN-ALT-01 aplicada como
constraint real de base de datos (parcial, solo sobre filas 'activa') en
vez de solo "en capa de aplicación" como sugiere docs/14 — un índice único
parcial es más fuerte que una verificación en Python (inmune a condiciones
de carrera entre el worker y peticiones concurrentes) y no cuesta nada
adicional expresarlo así.

`notificaciones_pendientes` es el outbox (RF-ALT-05): ninguna alerta
dispara un WebSocket directamente desde la transacción que la genera — se
escribe aquí en la MISMA transacción, y un worker separado la procesa
(docs/13-arquitectura.md sección 2, patrón outbox).

`mantenimientos.frecuencia_meses`/`generado_de_id` se agregan sobre el
esquema literal de docs/14 para resolver RF-MANT-02 ("programar
preventivos recurrentes"): al cerrar un preventivo con `frecuencia_meses`,
se autogenera el siguiente mantenimiento "programado" referenciando este
vía `generado_de_id` — recurrencia paso a paso en vez de un scheduler de
cron separado, mismo criterio que `proxima_fecha` en Calibraciones (0006).

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_ROL_APP = "labsync_app"


def _habilitar_rls(tabla: str) -> None:
    op.execute(f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_{tabla} ON {tabla}
          USING (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
          WITH CHECK (laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        """
    )


def upgrade() -> None:
    op.create_table(
        "mantenimientos",
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
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="programado"),
        sa.Column("fecha_programada", sa.Date(), nullable=True),
        sa.Column("fecha_ejecutada", sa.Date(), nullable=True),
        sa.Column(
            "tecnico_responsable_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("repuestos_utilizados", sa.Text(), nullable=True),
        sa.Column("tiempo_inactividad_horas", sa.Numeric(8, 2), nullable=True),
        sa.Column("costo", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "informe_adjunto_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("adjuntos.id"),
            nullable=True,
        ),
        sa.Column("frecuencia_meses", sa.Integer(), nullable=True),
        sa.Column(
            "generado_de_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("mantenimientos.id"),
            nullable=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_mantenimientos_equipo_programada", "mantenimientos", ["equipo_id", "fecha_programada"]
    )
    op.create_index("ix_mantenimientos_laboratorio_estado", "mantenimientos", ["laboratorio_id", "estado"])
    op.create_index(
        "ix_mantenimientos_tecnico", "mantenimientos", ["tecnico_responsable_id", "fecha_programada"]
    )

    op.create_table(
        "alertas",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("origen_tipo", sa.String(30), nullable=False),
        sa.Column("origen_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="activa"),
        sa.Column("leida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "resuelta_por_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_alertas_laboratorio_estado", "alertas", ["laboratorio_id", "estado"])
    op.create_index("ix_alertas_origen", "alertas", ["origen_tipo", "origen_id"])
    # RN-ALT-01 reforzado como constraint real, no solo verificación en
    # Python — único (origen_tipo, origen_id, tipo) mientras estado='activa'.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_alertas_activa_por_origen
        ON alertas (origen_tipo, origen_id, tipo)
        WHERE estado = 'activa'
        """
    )

    op.create_table(
        "notificaciones_pendientes",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "alerta_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alertas.id"),
            nullable=False,
        ),
        sa.Column("canal", sa.String(20), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("procesado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_notificaciones_pendientes_estado", "notificaciones_pendientes", ["estado", "creado_en"]
    )

    for tabla in ("mantenimientos", "alertas", "notificaciones_pendientes"):
        _habilitar_rls(tabla)

    op.execute(
        f"GRANT SELECT, INSERT, UPDATE ON mantenimientos, alertas, notificaciones_pendientes TO {_ROL_APP}"
    )


def downgrade() -> None:
    op.drop_table("notificaciones_pendientes")
    op.drop_table("alertas")
    op.drop_table("mantenimientos")
