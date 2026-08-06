"""Esquema inicial: laboratorios, usuarios, roles, permisos, sesiones — con RLS.

Corresponde a docs/14-base-de-datos.md (tablas de identidad/tenant) y aplica
el patrón de Row Level Security de la sección 3 de ese documento: ENABLE +
FORCE ROW LEVEL SECURITY (FORCE hace que la política también aplique al
propietario de la tabla) y políticas con USING + WITH CHECK (para que el
aislamiento aplique tanto a lecturas como a escrituras).

IMPORTANTE — rol de aplicación no-superusuario: esta migración también crea
el rol `labsync_app` y le otorga privilegios DML explícitos. Postgres ignora
Row Level Security POR COMPLETO para roles superusuario, sin excepción —ni
siquiera FORCE ROW LEVEL SECURITY los afecta. La migración se ejecuta con un
rol con privilegios elevados (ver `database_url_migraciones` en
app/core/config.py), pero la aplicación en tiempo de ejecución SIEMPRE debe
conectarse como `labsync_app`. Esto se descubrió precisamente gracias a
tests/test_tenant_isolation.py fallando contra una conexión de superusuario
— ver ese archivo para el detalle.

Revision ID: 0001
Revises:
Create Date: 2026-07-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


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


_ROL_APP = "labsync_app"
# Contraseña de desarrollo — en producción se gestiona fuera del repositorio
# (secret manager), nunca hardcodeada en una migración versionada.
_ROL_APP_PASSWORD_DEV = "labsync_app"


def _crear_rol_app_si_no_existe() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{_ROL_APP}') THEN
            CREATE ROLE {_ROL_APP} LOGIN PASSWORD '{_ROL_APP_PASSWORD_DEV}'
              NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
          END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    _crear_rol_app_si_no_existe()

    op.create_table(
        "laboratorios",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="activo"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=True,
        ),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("es_sistema", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "permisos",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clave", sa.String(100), nullable=False, unique=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
    )

    op.create_table(
        "roles_permisos",
        sa.Column(
            "rol_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), primary_key=True
        ),
        sa.Column(
            "permiso_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("permisos.id"),
            primary_key=True,
        ),
    )

    op.create_table(
        "usuarios",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column("correo", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("nombre_completo", sa.String(200), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="pendiente_activacion"),
        sa.Column("debe_cambiar_password", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("mfa_habilitado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("intentos_fallidos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_login_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("laboratorio_id", "correo", name="uq_usuarios_lab_correo"),
    )

    op.create_table(
        "usuarios_roles",
        sa.Column(
            "usuario_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            primary_key=True,
        ),
        sa.Column(
            "rol_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), primary_key=True
        ),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
    )

    op.create_table(
        "sesiones",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "laboratorio_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("laboratorios.id"),
            nullable=False,
        ),
        sa.Column(
            "usuario_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ip_origen", sa.dialects.postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_index("ix_usuarios_laboratorio", "usuarios", ["laboratorio_id"])
    op.create_index("ix_sesiones_usuario", "sesiones", ["usuario_id"])
    op.create_index("ix_sesiones_laboratorio", "sesiones", ["laboratorio_id"])

    # --- Row Level Security ---------------------------------------------
    # `laboratorios` es la raíz del tenant, no lleva RLS por columna
    # laboratorio_id (es la propia identidad del tenant). `permisos` y
    # `roles_permisos` son catálogo global no sensible — sin RLS.
    _habilitar_rls("usuarios")
    _habilitar_rls("usuarios_roles")
    _habilitar_rls("sesiones")

    # `roles` admite filas de sistema (laboratorio_id NULL, visibles para
    # todos los tenants) además de roles propios de un laboratorio.
    op.execute("ALTER TABLE roles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE roles FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_roles ON roles
          USING (
            laboratorio_id IS NULL
            OR laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
          )
          WITH CHECK (
            laboratorio_id IS NULL
            OR laboratorio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
          )
        """
    )

    # --- Privilegios del rol de aplicación --------------------------------
    # `labsync_app` necesita DML (no DDL) sobre las tablas de negocio. RLS
    # ya restringe QUÉ filas ve/modifica dentro de eso — estos GRANT solo
    # habilitan la operación a nivel de tabla, la fila la decide la política.
    op.execute(f"GRANT CONNECT ON DATABASE {op.get_bind().engine.url.database} TO {_ROL_APP}")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {_ROL_APP}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {_ROL_APP}")


def downgrade() -> None:
    op.drop_table("sesiones")
    op.drop_table("usuarios_roles")
    op.drop_table("usuarios")
    op.drop_table("roles_permisos")
    op.drop_table("permisos")
    op.drop_table("roles")
    op.drop_table("laboratorios")
