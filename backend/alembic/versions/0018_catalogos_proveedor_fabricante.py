"""Catálogos de proveedores y fabricantes — Fase 2 de hojas de vida
(docs/24-especificacion-hojas-de-vida-mantenimiento-firmas.md,
docs/25-diseno-tecnico-hojas-de-vida.md sección 2, migración 0018).

`equipos.fabricante`/`proveedor` son hoy texto libre, sin normalizar. Esta
migración crea los catálogos `proveedores`/`fabricantes` (con los campos que
pide el formato físico `LSPC-GMT-GPM-FOR-003.xlsx`, hoja `H.V.`: Nombre,
Dirección, Pais-Ciudad —un solo campo combinado en el formato real, no dos—,
E-Mail, Teléfono, Contacto) y agrega `equipos.proveedor_id`/`fabricante_id`
(FK nullable). **No borra** las columnas de texto existentes.

El backfill agrupa por `(laboratorio_id, lower(trim(nombre)))`, no por
`SELECT DISTINCT` simple: dos valores que solo difieren en mayúsculas o
espacios (p. ej. "Fisher Scientific" vs "FISHER SCIENTIFIC") quedan en una
sola fila del catálogo, usando `MIN(nombre)` como ortografía representativa.
Solo quedan para revisión manual (fuera de esta migración) las variantes que
difieren en algo más que eso (p. ej. "FISHER SCIENTIFIC S.A.").

Aislamiento multi-tenant en las FK nuevas: Postgres evalúa las restricciones
de FK sin pasar por RLS, así que una FK simple permitiría vincular un
proveedor/fabricante de OTRO laboratorio. Se usa FK **compuesta**
`equipos(proveedor_id, laboratorio_id) -> proveedores(id, laboratorio_id)`
(e igual para fabricante), lo que exige un `UNIQUE(id, laboratorio_id)` en
cada catálogo (`id` ya es globalmente único por ser PK; esta restricción
adicional solo habilita que la FK compuesta pueda apuntar a ese par de
columnas). `ON DELETE RESTRICT` explícito: nunca `SET NULL` sin lista de
columnas, porque anularía también `laboratorio_id` de la fila de `equipos`,
no solo `proveedor_id`/`fabricante_id`.

Orden de la migración (creación de tabla -> backfill -> `ENABLE/FORCE ROW
LEVEL SECURITY` al final): las migraciones de este proyecto corren con un rol
superusuario (ver la nota de 0001_esquema_inicial_auth.py), que Postgres
exime de RLS por completo con o sin `FORCE`, así que el orden no cambia el
resultado de las consultas de esta propia migración — se mantiene este orden
igual, por claridad y para no depender de ese detalle de implementación.

`gen_random_uuid()` es una función nativa de Postgres desde la versión 13
(no requiere `CREATE EXTENSION`); el proyecto corre PostgreSQL 16
(docker-compose.yml), así que está disponible sin pasos adicionales.

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0018"
down_revision = "0017"
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


def _crear_tabla_catalogo(nombre_tabla: str) -> None:
    op.create_table(
        nombre_tabla,
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("pais_ciudad", sa.String(150), nullable=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("email", sa.String(150), nullable=True),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("contacto", sa.String(150), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("id", "laboratorio_id", name=f"uq_{nombre_tabla}_id_laboratorio"),
    )
    # Índice único funcional: dedupe por nombre normalizado, no por el texto
    # literal (ver cabecera de este archivo).
    op.execute(
        f"""
        CREATE UNIQUE INDEX uq_{nombre_tabla}_lab_nombre_norm
        ON {nombre_tabla} (laboratorio_id, lower(trim(nombre)))
        """
    )


def _backfill_catalogo(nombre_tabla: str, columna_texto: str) -> None:
    op.execute(
        f"""
        INSERT INTO {nombre_tabla} (id, laboratorio_id, nombre, creado_en, actualizado_en)
        SELECT gen_random_uuid(), laboratorio_id, MIN({columna_texto}), now(), now()
        FROM equipos
        WHERE {columna_texto} IS NOT NULL AND trim({columna_texto}) <> ''
        GROUP BY laboratorio_id, lower(trim({columna_texto}))
        """
    )


def _vincular_columna(columna_id: str, nombre_tabla: str, columna_texto: str) -> None:
    op.execute(
        f"""
        UPDATE equipos AS e
        SET {columna_id} = c.id
        FROM {nombre_tabla} AS c
        WHERE e.laboratorio_id = c.laboratorio_id
          AND e.{columna_texto} IS NOT NULL
          AND lower(trim(e.{columna_texto})) = lower(trim(c.nombre))
          AND e.{columna_id} IS NULL
        """
    )


def upgrade() -> None:
    _crear_tabla_catalogo("proveedores")
    _crear_tabla_catalogo("fabricantes")

    _backfill_catalogo("proveedores", "proveedor")
    _backfill_catalogo("fabricantes", "fabricante")

    op.add_column(
        "equipos", sa.Column("proveedor_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "equipos", sa.Column("fabricante_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True)
    )

    _vincular_columna("proveedor_id", "proveedores", "proveedor")
    _vincular_columna("fabricante_id", "fabricantes", "fabricante")

    op.create_foreign_key(
        "fk_equipos_proveedor_lab",
        "equipos",
        "proveedores",
        ["proveedor_id", "laboratorio_id"],
        ["id", "laboratorio_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_equipos_fabricante_lab",
        "equipos",
        "fabricantes",
        ["fabricante_id", "laboratorio_id"],
        ["id", "laboratorio_id"],
        ondelete="RESTRICT",
    )

    _habilitar_rls("proveedores")
    _habilitar_rls("fabricantes")

    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON proveedores, fabricantes TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_constraint("fk_equipos_fabricante_lab", "equipos", type_="foreignkey")
    op.drop_constraint("fk_equipos_proveedor_lab", "equipos", type_="foreignkey")
    op.drop_column("equipos", "fabricante_id")
    op.drop_column("equipos", "proveedor_id")
    op.drop_table("fabricantes")
    op.drop_table("proveedores")
