"""Calibraciones + adjuntos — RF-CAL-01 a RF-CAL-07 (Sprint 7, docs/18-sprints.md).

`adjuntos` es la tabla polimórfica declarada en docs/14-base-de-datos.md
("reutilizada por Equipos/Mantenimientos"): un registro por archivo subido
al bucket "evidencias" (distinto del bucket "documentos" del Gestor
Documental), identificado por (`entidad_tipo`, `entidad_id`). Solo
Calibraciones la usa por ahora (certificado_adjunto_id) — Mantenimientos la
reutilizará en Sprint 8 sin migración adicional.

`calibraciones` NO lleva `eliminado_en` a propósito (RN-CAL-02): una
calibración registrada nunca se elimina, ni física ni lógicamente — la
única operación de edición es "corregir", que inserta una fila nueva
referenciando la original vía `corrige_a_id` (auto-referencia). Enriquecido
sobre el esquema literal de docs/14 con `motivo_correccion` (obligatorio
solo en filas de corrección, ver RN-CAL-02) y, en `adjuntos`,
`nombre_archivo`/`tamano_bytes` (necesarios para el header
Content-Disposition de la descarga segura y no estaban en el esquema
original — mismo criterio ya aplicado a `documentos_versiones` en 0005).

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
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
        "adjuntos",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("entidad_tipo", sa.String(50), nullable=False),
        sa.Column("entidad_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("nombre_archivo", sa.String(255), nullable=False),
        sa.Column("tamano_bytes", sa.BigInteger(), nullable=False),
        sa.Column("tipo_mime", sa.String(100), nullable=False),
        sa.Column(
            "subido_por_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_adjuntos_laboratorio", "adjuntos", ["laboratorio_id"])
    op.create_index("ix_adjuntos_entidad", "adjuntos", ["entidad_tipo", "entidad_id"])

    op.create_table(
        "calibraciones",
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
        sa.Column("fecha_calibracion", sa.Date(), nullable=False),
        sa.Column("frecuencia_meses", sa.Integer(), nullable=False),
        sa.Column("proxima_fecha", sa.Date(), nullable=False),
        sa.Column("laboratorio_proveedor", sa.String(200), nullable=True),
        sa.Column("numero_certificado", sa.String(100), nullable=True),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column("incertidumbre", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "responsable_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column(
            "certificado_adjunto_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("adjuntos.id"),
            nullable=True,
        ),
        sa.Column(
            "corrige_a_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calibraciones.id"),
            nullable=True,
        ),
        sa.Column("motivo_correccion", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("frecuencia_meses > 0", name="ck_calibraciones_frecuencia_positiva"),
    )
    op.create_index("ix_calibraciones_equipo_proxima", "calibraciones", ["equipo_id", "proxima_fecha"])
    op.create_index(
        "ix_calibraciones_laboratorio_proxima", "calibraciones", ["laboratorio_id", "proxima_fecha"]
    )

    _habilitar_rls("adjuntos")
    _habilitar_rls("calibraciones")

    op.execute(f"GRANT SELECT, INSERT, UPDATE ON adjuntos, calibraciones TO {_ROL_APP}")
    # Deliberadamente sin DELETE — RN-CAL-02 prohíbe eliminar una
    # calibración registrada incluso a nivel de aplicación; se refuerza
    # aquí a nivel de permisos de base de datos, mismo criterio que
    # logs_auditoria (0003) para reglas append-only/no-borrado.


def downgrade() -> None:
    op.drop_table("calibraciones")
    op.drop_table("adjuntos")
