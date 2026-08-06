"""Módulo Equipos: categorias_equipo, areas, equipos — con RLS.

Corresponde a docs/14-base-de-datos.md y docs/03-requerimientos-funcionales.md
Módulo 3. Sigue el mismo patrón de aislamiento multi-tenant que 0001
(ENABLE + FORCE ROW LEVEL SECURITY, políticas USING + WITH CHECK, y GRANT
explícito al rol de aplicación `labsync_app` — sin este último paso las
tablas nuevas quedarían inaccesibles para la app, ver la lección documentada
en 0001).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
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
        "categorias_equipo",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("frecuencia_calibracion_default_meses", sa.Integer(), nullable=True),
        sa.UniqueConstraint("laboratorio_id", "nombre", name="uq_categorias_lab_nombre"),
    )

    op.create_table(
        "areas",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.UniqueConstraint("laboratorio_id", "nombre", name="uq_areas_lab_nombre"),
    )

    op.create_table(
        "equipos",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("codigo_interno", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column(
            "categoria_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categorias_equipo.id"),
            nullable=True,
        ),
        sa.Column("marca", sa.String(100), nullable=True),
        sa.Column("modelo", sa.String(100), nullable=True),
        sa.Column("numero_serie", sa.String(100), nullable=True),
        sa.Column("fabricante", sa.String(150), nullable=True),
        sa.Column("proveedor", sa.String(150), nullable=True),
        sa.Column("fecha_adquisicion", sa.Date(), nullable=True),
        sa.Column("estado_operativo", sa.String(30), nullable=False, server_default="operativo"),
        sa.Column(
            "area_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("areas.id"), nullable=True
        ),
        sa.Column(
            "responsable_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("foto_url", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("eliminado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("laboratorio_id", "codigo_interno", name="uq_equipos_lab_codigo"),
    )

    op.create_index("ix_equipos_laboratorio", "equipos", ["laboratorio_id"])
    op.create_index("ix_equipos_estado_operativo", "equipos", ["laboratorio_id", "estado_operativo"])
    # Búsqueda global (RF-EQ-06 / Módulo 9) sobre código, nombre y n° de serie.
    op.execute(
        """
        CREATE INDEX ix_equipos_busqueda ON equipos
        USING GIN (to_tsvector('spanish',
          coalesce(codigo_interno,'') || ' ' || coalesce(nombre,'') || ' ' || coalesce(numero_serie,'')
        ))
        """
    )

    _habilitar_rls("categorias_equipo")
    _habilitar_rls("areas")
    _habilitar_rls("equipos")

    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON categorias_equipo, areas, equipos TO {_ROL_APP}"
    )


def downgrade() -> None:
    op.drop_table("equipos")
    op.drop_table("areas")
    op.drop_table("categorias_equipo")
