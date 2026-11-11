"""Accesorios y manuales por tipo de equipo — Fase 2 de hojas de vida
(docs/25-diseno-tecnico-hojas-de-vida.md sección 2, migración 0020).

Crea `equipo_accesorios` (1:N: cantidad, descripción, observaciones — formato
`LSPC-GMT-GPM-FOR-003.xlsx`, hoja `H.V.`, sección "ACCESORIOS"). `descripcion`
es la única columna `NOT NULL`: identifica la fila (sin ella no hay accesorio
que registrar); `cantidad`/`observaciones` quedan opcionales, igual que el
resto de campos técnicos (docs/24-...md sección 3.8).

Crea `equipo_manuales` (1:N, único por `(equipo_id, tipo)`) con los 4 tipos
reales del formato (`Manual de Operaciones/Instalación/Servicio/Partes`,
cada uno un checkbox `SI/NO` en el .xlsx — de ahí `disponible BOOLEAN`) más
`sin_clasificar` para el backfill de abajo. Usa `object_key` directo (no
`documento_id` contra el módulo `documentos`, que no está pensado para
colgar un archivo de un equipo puntual — docs/25-...md sección 1.4): mismo
patrón que ya usa `equipos.manual_object_key` hoy.

**[Ajuste pedido por Gustavo]** `idioma` tiene un dominio cerrado
`('espanol', 'ingles', 'otro')`, nullable.

Backfill **[REVISIÓN 2 del diseño, decidido]**: si `equipos.manual_object_key`
no es nulo, se crea una fila con `tipo='sin_clasificar', disponible=true` —
no se asume "operación" ni ningún otro tipo concreto, porque no hay forma de
saberlo con certeza; el usuario lo reclasifica manualmente si corresponde.
No se borra `equipos.manual_object_key` ni se toca el endpoint existente de
manual (sigue funcionando igual que hoy, en paralelo a esta tabla nueva).

Aislamiento multi-tenant: ambas tablas usan la FK compuesta
`(equipo_id, laboratorio_id) -> equipos(id, laboratorio_id)` creada en 0019,
con `ON DELETE RESTRICT` explícito (mismo criterio que 0018/0019: nunca
`SET NULL` sin lista de columnas).

Orden (tabla -> backfill -> RLS al final): mismo criterio que 0018 — las
migraciones corren como superusuario, que Postgres exime de RLS, así que el
orden no cambia el resultado, pero se mantiene por claridad.

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

_ROL_APP = "labsync_app"

_TIPOS_MANUAL = (
    "manual_operacion",
    "manual_instalacion",
    "manual_servicio",
    "manual_partes",
    "sin_clasificar",
)
_IDIOMAS_MANUAL = ("espanol", "ingles", "otro")


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


def _lista_sql(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def upgrade() -> None:
    op.create_table(
        "equipo_accesorios",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("equipo_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_equipo_accesorios_equipo_lab",
        "equipo_accesorios",
        "equipos",
        ["equipo_id", "laboratorio_id"],
        ["id", "laboratorio_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_equipo_accesorios_equipo", "equipo_accesorios", ["equipo_id"])

    op.create_table(
        "equipo_manuales",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("equipo_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("disponible", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("idioma", sa.String(20), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("equipo_id", "tipo", name="uq_equipo_manuales_equipo_tipo"),
    )
    op.create_foreign_key(
        "fk_equipo_manuales_equipo_lab",
        "equipo_manuales",
        "equipos",
        ["equipo_id", "laboratorio_id"],
        ["id", "laboratorio_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_equipo_manuales_tipo", "equipo_manuales", f"tipo IN ({_lista_sql(_TIPOS_MANUAL)})"
    )
    op.create_check_constraint(
        "ck_equipo_manuales_idioma", "equipo_manuales", f"idioma IN ({_lista_sql(_IDIOMAS_MANUAL)})"
    )

    op.execute(
        """
        INSERT INTO equipo_manuales
            (id, laboratorio_id, equipo_id, tipo, disponible, object_key, creado_en, actualizado_en)
        SELECT gen_random_uuid(), laboratorio_id, id, 'sin_clasificar', true, manual_object_key, now(), now()
        FROM equipos
        WHERE manual_object_key IS NOT NULL
        """
    )

    _habilitar_rls("equipo_accesorios")
    _habilitar_rls("equipo_manuales")

    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON equipo_accesorios TO {_ROL_APP}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON equipo_manuales TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_table("equipo_manuales")
    op.drop_table("equipo_accesorios")
