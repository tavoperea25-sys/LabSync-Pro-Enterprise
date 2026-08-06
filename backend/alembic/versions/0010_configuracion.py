"""Configuración — RF-CFG-01 a 05 (Sprint 12, docs/18-sprints.md).

`configuraciones_laboratorio` ya estaba contemplada en docs/14-base-de-datos.md
desde el diseño original, pero ningún sprint la había creado — los umbrales
de alerta (Calibraciones, Alertas) y la política de contraseña (Usuarios)
vivían como constantes hardcodeadas con un comentario explícito de que este
sprint las haría configurables por laboratorio. Fila 1:1 por laboratorio,
creada perezosamente (no hay INSERT en esta migración): mientras no exista,
la aplicación opera con los valores por defecto (RF-CFG-03, ver
docs/05-casos-de-uso.md 3a)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
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
    # `laboratorios.logo_url` nunca se escribió en ningún sprint anterior
    # (verificado: cero referencias en el código) — se renombra ahora que
    # por fin tiene un flujo real (RF-CFG-04) para reflejar lo que en
    # realidad contiene: el object_key de MinIO, no una URL literal (las
    # URLs de descarga son prefirmadas y expiran, nunca se persisten).
    op.alter_column("laboratorios", "logo_url", new_column_name="logo_object_key")

    op.create_table(
        "configuraciones_laboratorio",
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            primary_key=True,
        ),
        sa.Column("umbral_alerta_calibracion_dias", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("umbral_alerta_mantenimiento_dias", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("umbral_alerta_documento_dias", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("politica_password_json", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "umbral_alerta_calibracion_dias > 0", name="ck_config_umbral_calibracion_positivo"
        ),
        sa.CheckConstraint(
            "umbral_alerta_mantenimiento_dias > 0", name="ck_config_umbral_mantenimiento_positivo"
        ),
        sa.CheckConstraint("umbral_alerta_documento_dias > 0", name="ck_config_umbral_documento_positivo"),
    )

    _habilitar_rls("configuraciones_laboratorio")
    # Sin DELETE — la fila de configuración de un laboratorio activo nunca
    # se borra, solo se actualiza (mismo criterio que el resto de tablas
    # 1:1 de este proyecto).
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON configuraciones_laboratorio TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_table("configuraciones_laboratorio")
    op.alter_column("laboratorios", "logo_object_key", new_column_name="logo_url")
