"""Reportes — RF-REP-01 a 08, RNF-PERF-04 (Sprint 11, docs/18-sprints.md).

`reportes_generados` es tanto el historial (RF-REP, "descarga desde
/reportes/historial") como la cola de trabajo asíncrona: un reporte pequeño
(<=1000 registros) se genera y se transmite en la misma petición HTTP y NUNCA
pasa por esta tabla; un reporte grande inserta una fila 'pendiente' aquí en
la MISMA petición y el worker (ya corriendo desde Sprint 8 para Alertas) la
recoge, genera el archivo, lo sube a MinIO y la marca 'listo' — mismo
patrón outbox que `notificaciones_pendientes`, reutilizado en vez de
inventar una cola nueva.

`filtros` se persiste en JSONB para que el historial muestre con qué
parámetros se generó cada reporte sin necesitar columnas específicas por
tipo de reporte."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_ROL_APP = "labsync_app"

_TIPOS_REPORTE = (
    "inventario",
    "calibraciones",
    "vencidos",
    "cumplimiento",
    "mantenimiento",
    "trazabilidad_documental",
    "paquete_auditoria",
)
_FORMATOS = ("pdf", "xlsx", "csv", "zip")
_ESTADOS = ("pendiente", "procesando", "listo", "fallido")


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
        "reportes_generados",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("formato", sa.String(10), nullable=False),
        sa.Column("filtros", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("nombre_archivo", sa.String(255), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "solicitado_por_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "tipo IN (" + ", ".join(f"'{t}'" for t in _TIPOS_REPORTE) + ")", name="ck_reportes_tipo"
        ),
        sa.CheckConstraint(
            "formato IN (" + ", ".join(f"'{f}'" for f in _FORMATOS) + ")", name="ck_reportes_formato"
        ),
        sa.CheckConstraint(
            "estado IN (" + ", ".join(f"'{e}'" for e in _ESTADOS) + ")", name="ck_reportes_estado"
        ),
    )
    op.create_index("ix_reportes_generados_laboratorio", "reportes_generados", ["laboratorio_id"])
    op.create_index(
        "ix_reportes_generados_laboratorio_estado", "reportes_generados", ["laboratorio_id", "estado"]
    )

    _habilitar_rls("reportes_generados")
    # Sin DELETE — el historial de reportes generados se conserva completo,
    # mismo criterio que el resto de tablas de historial/outbox del proyecto.
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON reportes_generados TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_table("reportes_generados")
