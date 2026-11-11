"""Ficha técnica extendida de equipos — Fase 2 de hojas de vida
(docs/25-diseno-tecnico-hojas-de-vida.md sección 2, migración 0019).

Agrega a `equipos` los campos de clasificación/adquisición que pide el
formato físico `LSPC-GMT-GPM-FOR-003.xlsx` (hoja `H.V.`): `capitulo`,
`grupo`, `subgrupo`, `ubicacion`, `numero_inventario` (texto libre, el
formato no los restringe a una lista cerrada), `condicion_fisica`
(bueno/regular/malo — distinto de `estado_operativo`, ver
docs/24-...md sección 3.4), `clasificacion_riesgo` (I/IIA/IIB/III),
`criticidad` (baja/media/alta), `forma_adquisicion`
(compra/donación/comodato) y `garantia`/`garantia_inicio`/`garantia_fin`.

`garantia` es booleano, no texto ni fecha: la celda real del formato es un
checkbox `"Garantia: SI ☐  NO ☐"` (verificado en el .xlsx). Todos los campos
son opcionales — RF-EQ ya establecido: "ningún campo técnico obligatorio,
todos admiten vacío" (docs/24-...md sección 3.8).

Crea `equipo_ficha_tecnica` (1:1, PK = `equipo_id`) con los datos técnicos
variables (voltaje, corriente, RPM, dimensiones, etc. — todos `TEXT`
nullable: el formato acepta "N/A" en varios de estos campos, así que un tipo
`NUMERIC` rechazaría respuestas válidas del formato real) y
`datos_adicionales JSONB` para lo específico de cada categoría.

Aislamiento multi-tenant: agrega `UNIQUE(id, laboratorio_id)` en `equipos`
(requerido para que una FK compuesta pueda apuntar a ese par de columnas —
mismo patrón que 0018) y usa esa FK compuesta desde `equipo_ficha_tecnica`,
con `ON DELETE RESTRICT` explícito (nunca `SET NULL` sin lista de columnas,
porque anularía también `laboratorio_id`).

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None

_ROL_APP = "labsync_app"

_CONDICIONES_FISICAS = ("bueno", "regular", "malo")
_CLASIFICACIONES_RIESGO = ("I", "IIA", "IIB", "III")
_CRITICIDADES = ("baja", "media", "alta")
_FORMAS_ADQUISICION = ("compra", "donacion", "comodato")


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
    # Habilita FK compuestas hacia `equipos` desde las tablas hijas nuevas
    # de esta Fase (equipo_ficha_tecnica aquí; equipo_accesorios/
    # equipo_manuales en 0020 reutilizan esta misma restricción).
    op.create_unique_constraint("uq_equipos_id_laboratorio", "equipos", ["id", "laboratorio_id"])

    op.add_column("equipos", sa.Column("capitulo", sa.String(100), nullable=True))
    op.add_column("equipos", sa.Column("grupo", sa.String(100), nullable=True))
    op.add_column("equipos", sa.Column("subgrupo", sa.String(100), nullable=True))
    op.add_column("equipos", sa.Column("ubicacion", sa.String(200), nullable=True))
    op.add_column("equipos", sa.Column("numero_inventario", sa.String(100), nullable=True))
    op.add_column("equipos", sa.Column("condicion_fisica", sa.String(20), nullable=True))
    op.add_column("equipos", sa.Column("clasificacion_riesgo", sa.String(10), nullable=True))
    op.add_column("equipos", sa.Column("criticidad", sa.String(20), nullable=True))
    op.add_column("equipos", sa.Column("forma_adquisicion", sa.String(20), nullable=True))
    op.add_column("equipos", sa.Column("garantia", sa.Boolean(), nullable=True))
    op.add_column("equipos", sa.Column("garantia_inicio", sa.Date(), nullable=True))
    op.add_column("equipos", sa.Column("garantia_fin", sa.Date(), nullable=True))

    op.create_check_constraint(
        "ck_equipos_condicion_fisica", "equipos", f"condicion_fisica IN ({_lista_sql(_CONDICIONES_FISICAS)})"
    )
    op.create_check_constraint(
        "ck_equipos_clasificacion_riesgo",
        "equipos",
        f"clasificacion_riesgo IN ({_lista_sql(_CLASIFICACIONES_RIESGO)})",
    )
    op.create_check_constraint(
        "ck_equipos_criticidad", "equipos", f"criticidad IN ({_lista_sql(_CRITICIDADES)})"
    )
    op.create_check_constraint(
        "ck_equipos_forma_adquisicion",
        "equipos",
        f"forma_adquisicion IN ({_lista_sql(_FORMAS_ADQUISICION)})",
    )
    op.create_check_constraint(
        "ck_equipos_garantia_fechas",
        "equipos",
        "garantia_fin IS NULL OR garantia_inicio IS NULL OR garantia_fin >= garantia_inicio",
    )

    op.create_table(
        "equipo_ficha_tecnica",
        sa.Column(
            "equipo_id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True
        ),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("voltaje", sa.Text(), nullable=True),
        sa.Column("corriente", sa.Text(), nullable=True),
        sa.Column("frecuencia", sa.Text(), nullable=True),
        sa.Column("corriente_ma", sa.Text(), nullable=True),
        sa.Column("variable_medicion", sa.Text(), nullable=True),
        sa.Column("rango_medicion", sa.Text(), nullable=True),
        sa.Column("rpm", sa.Text(), nullable=True),
        sa.Column("temperatura_trabajo", sa.Text(), nullable=True),
        sa.Column("humedad_trabajo", sa.Text(), nullable=True),
        sa.Column("peso", sa.Text(), nullable=True),
        sa.Column("dimensiones", sa.Text(), nullable=True),
        sa.Column("color", sa.Text(), nullable=True),
        sa.Column("numero_puertas", sa.Text(), nullable=True),
        sa.Column("clase_sistema", sa.Text(), nullable=True),
        sa.Column("alimentacion", sa.Text(), nullable=True),
        sa.Column("uso", sa.Text(), nullable=True),
        sa.Column("uso_especifico", sa.Text(), nullable=True),
        sa.Column("condiciones_ambientales", sa.Text(), nullable=True),
        sa.Column(
            "datos_adicionales",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_foreign_key(
        "fk_equipo_ficha_tecnica_equipo_lab",
        "equipo_ficha_tecnica",
        "equipos",
        ["equipo_id", "laboratorio_id"],
        ["id", "laboratorio_id"],
        ondelete="RESTRICT",
    )

    _habilitar_rls("equipo_ficha_tecnica")

    op.execute(f"GRANT SELECT, INSERT, UPDATE ON equipo_ficha_tecnica TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_table("equipo_ficha_tecnica")

    op.drop_constraint("ck_equipos_garantia_fechas", "equipos", type_="check")
    op.drop_constraint("ck_equipos_forma_adquisicion", "equipos", type_="check")
    op.drop_constraint("ck_equipos_criticidad", "equipos", type_="check")
    op.drop_constraint("ck_equipos_clasificacion_riesgo", "equipos", type_="check")
    op.drop_constraint("ck_equipos_condicion_fisica", "equipos", type_="check")

    op.drop_column("equipos", "garantia_fin")
    op.drop_column("equipos", "garantia_inicio")
    op.drop_column("equipos", "garantia")
    op.drop_column("equipos", "forma_adquisicion")
    op.drop_column("equipos", "criticidad")
    op.drop_column("equipos", "clasificacion_riesgo")
    op.drop_column("equipos", "condicion_fisica")
    op.drop_column("equipos", "numero_inventario")
    op.drop_column("equipos", "ubicacion")
    op.drop_column("equipos", "subgrupo")
    op.drop_column("equipos", "grupo")
    op.drop_column("equipos", "capitulo")

    op.drop_constraint("uq_equipos_id_laboratorio", "equipos", type_="unique")
