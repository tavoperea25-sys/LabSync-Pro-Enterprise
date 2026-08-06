"""Calendario + índices de búsqueda global — RF-CAL2-01 a 05, RF-SEARCH-01 a 05
(Sprint 9, docs/18-sprints.md).

`eventos_calendario` solo almacena físicamente los tipos que un usuario crea
a mano ('auditoria', 'capacitacion', 'institucional' — RF-CAL2-03). Los tipos
'calibracion', 'mantenimiento' y 'vencimiento_documental' NO se materializan
aquí: se sintetizan en el momento de la lectura a partir de
`calibraciones.proxima_fecha`, `mantenimientos.fecha_programada` y
`documentos.fecha_vencimiento` respectivamente (ver
`app/modules/calendario/application/calendario_service.py`). Espejar esas
fechas en una tabla aparte crearía una segunda fuente de verdad que se
desincroniza en cuanto alguien edite la fecha original — el mismo problema
que ya se evitó en Alertas (Sprint 8) no persistiendo alertas "vivas" a
partir de datos que cambian, sino evaluándolos bajo demanda. El CHECK
constraint sí permite los 6 valores del ENUM lógico (docs/14) porque
`origen_tipo`/`origen_id` quedan disponibles para cualquier futuro caso de
uso que sí requiera materializar una excepción puntual.

`descripcion` se agrega sobre el esquema literal de docs/14 — un evento
institucional sin espacio para notas (agenda, ubicación) es de uso limitado
en la práctica; mismo criterio de enriquecimiento ya aplicado repetidamente
desde Sprint 6 (ver docs de esas migraciones).

Los índices GIN de búsqueda de `equipos` (0002) y `documentos` (0005) ya
existían — aquí se completa la cobertura de RF-SEARCH-02 agregando
`usuarios`, `calibraciones` (cubre "certificados"), `mantenimientos` y
`logs_auditoria`.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-02
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

_ROL_APP = "labsync_app"

_TIPOS_EVENTO = (
    "calibracion",
    "mantenimiento",
    "auditoria",
    "capacitacion",
    "vencimiento_documental",
    "institucional",
)


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
        "eventos_calendario",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origen_tipo", sa.String(50), nullable=True),
        sa.Column("origen_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "creado_por_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=True,
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "tipo IN (" + ", ".join(f"'{t}'" for t in _TIPOS_EVENTO) + ")", name="ck_eventos_calendario_tipo"
        ),
    )
    op.create_index("ix_eventos_calendario_laboratorio", "eventos_calendario", ["laboratorio_id"])
    op.create_index("ix_eventos_calendario_fecha", "eventos_calendario", ["laboratorio_id", "fecha"])

    _habilitar_rls("eventos_calendario")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON eventos_calendario TO {_ROL_APP}")

    op.execute(
        """
        CREATE INDEX ix_usuarios_busqueda ON usuarios
        USING GIN (to_tsvector('spanish', coalesce(nombre_completo,'') || ' ' || coalesce(correo,'')))
        """
    )
    op.execute(
        """
        CREATE INDEX ix_calibraciones_busqueda ON calibraciones
        USING GIN (to_tsvector('spanish',
          coalesce(numero_certificado,'') || ' ' || coalesce(laboratorio_proveedor,'')
        ))
        """
    )
    op.execute(
        """
        CREATE INDEX ix_mantenimientos_busqueda ON mantenimientos
        USING GIN (to_tsvector('spanish',
          coalesce(descripcion,'') || ' ' || coalesce(repuestos_utilizados,'')
        ))
        """
    )
    op.execute(
        """
        CREATE INDEX ix_logs_auditoria_busqueda ON logs_auditoria
        USING GIN (to_tsvector('spanish',
          coalesce(modulo,'') || ' ' || coalesce(accion,'') || ' ' || coalesce(entidad_tipo,'')
        ))
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_logs_auditoria_busqueda")
    op.execute("DROP INDEX IF EXISTS ix_mantenimientos_busqueda")
    op.execute("DROP INDEX IF EXISTS ix_calibraciones_busqueda")
    op.execute("DROP INDEX IF EXISTS ix_usuarios_busqueda")
    op.drop_table("eventos_calendario")
