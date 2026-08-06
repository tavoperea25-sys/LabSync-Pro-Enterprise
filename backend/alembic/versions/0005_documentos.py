"""Gestor Documental (I): carpetas, documentos, documentos_versiones,
etiquetas, documentos_etiquetas, documentos_favoritos — RF-DOC-01 a RF-DOC-11
(Sprint 5, docs/18-sprints.md).

Todas las tablas nuevas llevan `laboratorio_id` propio y RLS estándar, aun
las tablas hijas/junction (`documentos_versiones`, `documentos_etiquetas`,
`documentos_favoritos`) — se denormaliza el tenant en vez de depender de un
JOIN implícito para el filtrado, mismo criterio que `logs_auditoria` y
`qr_tokens`/`incidencias_qr` de sprints anteriores: RLS debe poder evaluarse
con una columna propia de la fila, no confiar en que el código de aplicación
siempre haga el JOIN correcto.

`version_vigente_id` en `documentos` se agrega con ALTER posterior a crear
`documentos_versiones` (dependencia circular entre ambas tablas).

Alcance deliberado de Sprint 5: `estado` existe en el esquema completo desde
ahora (coincide con docs/14-base-de-datos.md), pero la máquina de estados de
aprobación (RN-DOC-01, RN-DOC-02 — ligadas al endpoint `/aprobar`) es Sprint 6.
Por ahora toda versión nueva pasa a ser la vigente directamente.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
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
        "carpetas",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column(
            "carpeta_padre_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("carpetas.id"),
            nullable=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_carpetas_laboratorio", "carpetas", ["laboratorio_id"])

    op.create_table(
        "etiquetas",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.UniqueConstraint("laboratorio_id", "nombre", name="uq_etiquetas_lab_nombre"),
    )

    op.create_table(
        "documentos",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "carpeta_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("carpetas.id"),
            nullable=True,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("categoria", sa.String(100), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="vigente"),
        sa.Column("fecha_emision", sa.Date(), nullable=True),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column(
            "responsable_aprobacion_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        # FK a documentos_versiones se agrega después (dependencia circular).
        sa.Column("version_vigente_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "fecha_vencimiento IS NULL OR fecha_emision IS NULL OR fecha_vencimiento > fecha_emision",
            name="ck_documentos_vencimiento_posterior",
        ),
    )
    op.create_index("ix_documentos_laboratorio", "documentos", ["laboratorio_id"])
    op.create_index("ix_documentos_carpeta", "documentos", ["laboratorio_id", "carpeta_id"])
    op.execute(
        """
        CREATE INDEX ix_documentos_busqueda ON documentos
        USING GIN (to_tsvector('spanish', coalesce(nombre,'') || ' ' || coalesce(categoria,'')))
        """
    )

    op.create_table(
        "documentos_versiones",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "documento_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documentos.id"),
            nullable=False,
        ),
        sa.Column("numero_version", sa.Integer(), nullable=False),
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
        sa.Column(
            "aprobado_por_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("aprobado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("documento_id", "numero_version", name="uq_documentos_versiones_doc_num"),
    )
    op.create_index("ix_documentos_versiones_laboratorio", "documentos_versiones", ["laboratorio_id"])
    op.create_index("ix_documentos_versiones_documento", "documentos_versiones", ["documento_id"])

    op.create_foreign_key(
        "fk_documentos_version_vigente",
        "documentos",
        "documentos_versiones",
        ["version_vigente_id"],
        ["id"],
    )

    op.create_table(
        "documentos_etiquetas",
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "documento_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documentos.id"),
            primary_key=True,
        ),
        sa.Column(
            "etiqueta_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("etiquetas.id"),
            primary_key=True,
        ),
    )
    op.create_index("ix_documentos_etiquetas_laboratorio", "documentos_etiquetas", ["laboratorio_id"])

    op.create_table(
        "documentos_favoritos",
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "documento_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documentos.id"),
            primary_key=True,
        ),
        sa.Column(
            "usuario_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            primary_key=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_documentos_favoritos_laboratorio", "documentos_favoritos", ["laboratorio_id"])

    for tabla in (
        "carpetas",
        "etiquetas",
        "documentos",
        "documentos_versiones",
        "documentos_etiquetas",
        "documentos_favoritos",
    ):
        _habilitar_rls(tabla)

    op.execute(
        f"""GRANT SELECT, INSERT, UPDATE, DELETE ON carpetas, etiquetas, documentos,
        documentos_versiones, documentos_etiquetas, documentos_favoritos TO {_ROL_APP}"""
    )


def downgrade() -> None:
    op.drop_table("documentos_favoritos")
    op.drop_table("documentos_etiquetas")
    op.drop_constraint("fk_documentos_version_vigente", "documentos", type_="foreignkey")
    op.drop_table("documentos_versiones")
    op.drop_table("documentos")
    op.drop_table("etiquetas")
    op.drop_table("carpetas")
