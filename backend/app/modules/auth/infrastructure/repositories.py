"""Implementaciones SQLAlchemy de los puertos de docs/13-arquitectura.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session

from app.modules.auth.domain.entities import Laboratorio as LaboratorioDominio
from app.modules.auth.domain.entities import Rol as RolDominio
from app.modules.auth.domain.entities import SesionActiva
from app.modules.auth.domain.entities import Usuario as UsuarioDominio
from app.modules.auth.domain.ports import PaginaUsuarios
from app.modules.auth.infrastructure.models import Laboratorio, Rol, Sesion, Usuario, UsuarioRol


def _laboratorio_a_dominio(fila: Laboratorio) -> LaboratorioDominio:
    return LaboratorioDominio(
        id=fila.id, nombre=fila.nombre, slug=fila.slug, logo_object_key=fila.logo_object_key
    )


def _a_dominio(fila: Usuario) -> UsuarioDominio:
    return UsuarioDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        correo=fila.correo,
        password_hash=fila.password_hash,
        nombre_completo=fila.nombre_completo,
        estado=fila.estado,
        debe_cambiar_password=fila.debe_cambiar_password,
        intentos_fallidos=fila.intentos_fallidos,
        bloqueado_hasta=fila.bloqueado_hasta,
        roles=[rol.nombre for rol in fila.roles],
        foto_object_key=fila.foto_object_key,
    )


class UsuarioRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def buscar_por_correo(self, laboratorio_id: uuid.UUID, correo: str) -> UsuarioDominio | None:
        stmt = select(Usuario).where(
            Usuario.laboratorio_id == laboratorio_id, Usuario.correo == correo.lower()
        )
        fila = self._db.execute(stmt).scalar_one_or_none()
        return _a_dominio(fila) if fila else None

    def obtener_por_id(self, usuario_id: uuid.UUID) -> UsuarioDominio | None:
        fila = self._db.get(Usuario, usuario_id)
        return _a_dominio(fila) if fila else None

    def registrar_intento_fallido(
        self, usuario_id: uuid.UUID, bloqueado_hasta: datetime | None
    ) -> None:
        self._db.execute(
            update(Usuario)
            .where(Usuario.id == usuario_id)
            .values(
                intentos_fallidos=Usuario.intentos_fallidos + 1,
                bloqueado_hasta=bloqueado_hasta,
            )
        )

    def resetear_intentos_fallidos(self, usuario_id: uuid.UUID) -> None:
        self._db.execute(
            update(Usuario)
            .where(Usuario.id == usuario_id)
            .values(intentos_fallidos=0, bloqueado_hasta=None, ultimo_login_en=datetime.utcnow())
        )

    def buscar_texto(self, consulta: str, limite: int) -> list[UsuarioDominio]:
        stmt = (
            select(Usuario)
            .where(
                Usuario.estado == "activo",
                text(
                    "to_tsvector('spanish', coalesce(nombre_completo,'') || ' ' || coalesce(correo,'')) "
                    "@@ plainto_tsquery('spanish', :consulta)"
                ),
            )
            .params(consulta=consulta)
            .limit(limite)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def crear(self, usuario: UsuarioDominio) -> UsuarioDominio:
        fila = Usuario(
            id=usuario.id,
            laboratorio_id=usuario.laboratorio_id,
            correo=usuario.correo.lower(),
            password_hash=usuario.password_hash,
            nombre_completo=usuario.nombre_completo,
            estado=usuario.estado,
            debe_cambiar_password=usuario.debe_cambiar_password,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def listar(self) -> list[UsuarioDominio]:
        stmt = select(Usuario).order_by(Usuario.nombre_completo)
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_paginado(self, pagina: int, tamano_pagina: int) -> PaginaUsuarios:
        stmt = select(Usuario)
        total = self._db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        # `nombre_completo` no es única (dos usuarios pueden compartir
        # nombre) — se desempata por `id` para que el orden entre páginas
        # sea estable.
        stmt = (
            stmt.order_by(Usuario.nombre_completo, Usuario.id)
            .offset((pagina - 1) * tamano_pagina)
            .limit(tamano_pagina)
        )
        filas = self._db.execute(stmt).scalars().all()

        return PaginaUsuarios(
            items=[_a_dominio(f) for f in filas], total=total, pagina=pagina, tamano_pagina=tamano_pagina
        )

    def actualizar(self, usuario: UsuarioDominio) -> UsuarioDominio:
        fila = self._db.get(Usuario, usuario.id)
        assert fila is not None
        fila.nombre_completo = usuario.nombre_completo
        fila.correo = usuario.correo
        fila.estado = usuario.estado
        fila.debe_cambiar_password = usuario.debe_cambiar_password
        fila.foto_object_key = usuario.foto_object_key
        self._db.flush()
        return _a_dominio(fila)

    def actualizar_password(self, usuario_id: uuid.UUID, password_hash: str) -> None:
        fila = self._db.get(Usuario, usuario_id)
        assert fila is not None
        fila.password_hash = password_hash
        fila.debe_cambiar_password = False
        self._db.flush()

    def existe_correo(
        self, laboratorio_id: uuid.UUID, correo: str, excluir_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Usuario.id).where(
            Usuario.laboratorio_id == laboratorio_id, Usuario.correo == correo.lower()
        )
        if excluir_id is not None:
            stmt = stmt.where(Usuario.id != excluir_id)
        return self._db.execute(stmt).scalar_one_or_none() is not None

    def contar_administradores_activos(self, excluir_id: uuid.UUID | None = None) -> int:
        stmt = (
            select(func.count(func.distinct(Usuario.id)))
            .select_from(Usuario)
            .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
            .join(Rol, Rol.id == UsuarioRol.rol_id)
            .where(Usuario.estado == "activo", Rol.nombre == "administrador")
        )
        if excluir_id is not None:
            stmt = stmt.where(Usuario.id != excluir_id)
        return self._db.execute(stmt).scalar_one()

    def asignar_roles(self, usuario_id: uuid.UUID, rol_ids: list[uuid.UUID]) -> None:
        # No se usa la relación `Usuario.roles` (secondary=) para escribir:
        # esa vía de SQLAlchemy solo conoce (usuario_id, rol_id) y no llena
        # `usuarios_roles.laboratorio_id` — la columna denormalizada que la
        # política RLS de esa tabla exige (ver infrastructure/models.py) —
        # así que el INSERT queda rechazado por RLS. Se maneja la tabla de
        # unión directamente para poder fijar `laboratorio_id`.
        fila = self._db.get(Usuario, usuario_id)
        assert fila is not None
        self._db.execute(delete(UsuarioRol).where(UsuarioRol.usuario_id == usuario_id))
        for rol_id in rol_ids:
            self._db.add(
                UsuarioRol(usuario_id=usuario_id, rol_id=rol_id, laboratorio_id=fila.laboratorio_id)
            )
        self._db.flush()
        self._db.expire(fila, ["roles"])


class LaboratorioRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def existe_activo(self, laboratorio_id: uuid.UUID) -> bool:
        fila = self._db.get(Laboratorio, laboratorio_id)
        return fila is not None and fila.estado == "activo"

    def resolver_id_por_slug(self, slug: str) -> uuid.UUID | None:
        stmt = select(Laboratorio.id).where(Laboratorio.slug == slug, Laboratorio.estado == "activo")
        return self._db.execute(stmt).scalar_one_or_none()

    def obtener_por_id(self, laboratorio_id: uuid.UUID) -> LaboratorioDominio | None:
        fila = self._db.get(Laboratorio, laboratorio_id)
        return _laboratorio_a_dominio(fila) if fila else None

    def actualizar(self, laboratorio: LaboratorioDominio) -> LaboratorioDominio:
        fila = self._db.get(Laboratorio, laboratorio.id)
        assert fila is not None
        fila.nombre = laboratorio.nombre
        fila.logo_object_key = laboratorio.logo_object_key
        self._db.flush()
        return _laboratorio_a_dominio(fila)


def _sesion_a_dominio(fila: Sesion) -> SesionActiva:
    return SesionActiva(
        id=fila.id,
        usuario_id=fila.usuario_id,
        laboratorio_id=fila.laboratorio_id,
        refresh_token_hash=fila.refresh_token_hash,
        expira_en=fila.expira_en,
        revocada=fila.revocada,
        revocada_en=fila.revocada_en,
        duracion_dias=fila.duracion_dias,
        ip_origen=fila.ip_origen,
        user_agent=fila.user_agent,
        creado_en=fila.creado_en,
    )


class SesionRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(
        self,
        usuario_id: uuid.UUID,
        laboratorio_id: uuid.UUID,
        refresh_token_hash: str,
        expira_en: datetime,
        duracion_dias: int,
        ip_origen: str | None,
        user_agent: str | None,
    ) -> SesionActiva:
        fila = Sesion(
            usuario_id=usuario_id,
            laboratorio_id=laboratorio_id,
            refresh_token_hash=refresh_token_hash,
            expira_en=expira_en,
            duracion_dias=duracion_dias,
            ip_origen=ip_origen,
            user_agent=user_agent,
        )
        self._db.add(fila)
        self._db.flush()
        return _sesion_a_dominio(fila)

    def buscar_por_hash(self, refresh_token_hash: str) -> SesionActiva | None:
        stmt = select(Sesion).where(Sesion.refresh_token_hash == refresh_token_hash)
        fila = self._db.execute(stmt).scalar_one_or_none()
        return _sesion_a_dominio(fila) if fila else None

    def buscar_por_hash_para_refresh(self, refresh_token_hash: str) -> SesionActiva | None:
        """Variante de `buscar_por_hash` con `SELECT ... FOR UPDATE` — solo
        para `AuthService.refresh`. Bloquea la fila hasta que la transacción
        termine (commit/rollback), para que una segunda petición de refresh
        concurrente con el mismo token vea de forma confiable el resultado ya
        rotado de la primera, en vez de competir sobre una lectura sin
        bloqueo. Revisión de seguridad módulo Auth, hallazgo 1."""
        stmt = select(Sesion).where(Sesion.refresh_token_hash == refresh_token_hash).with_for_update()
        fila = self._db.execute(stmt).scalar_one_or_none()
        return _sesion_a_dominio(fila) if fila else None

    def revocar(self, sesion_id: uuid.UUID) -> None:
        self._db.execute(update(Sesion).where(Sesion.id == sesion_id).values(revocada=True))

    def revocar_por_rotacion(self, sesion_id: uuid.UUID) -> None:
        """Como `revocar`, pero además marca `revocada_en` — usado
        exclusivamente por la rotación normal de refresh en
        `AuthService.refresh`, nunca por `logout` ni por
        `revocar_todas_de_usuario`. Es justamente esa marca de tiempo la que
        habilita la ventana de gracia: una sesión cerrada por logout
        explícito o por detección de compromiso NUNCA debe calificar para la
        ventana de gracia, así que esas dos rutas deliberadamente no tocan
        esta columna (la dejan en su valor previo — NULL o una rotación
        legítima ya vieja)."""
        self._db.execute(
            update(Sesion).where(Sesion.id == sesion_id).values(revocada=True, revocada_en=func.now())
        )

    def revocar_todas_de_usuario(self, usuario_id: uuid.UUID) -> None:
        self._db.execute(
            update(Sesion).where(Sesion.usuario_id == usuario_id).values(revocada=True)
        )

    def listar_activas_de_usuario(self, usuario_id: uuid.UUID) -> list[SesionActiva]:
        stmt = (
            select(Sesion)
            .where(
                Sesion.usuario_id == usuario_id,
                Sesion.revocada.is_(False),
                Sesion.expira_en > datetime.utcnow(),
            )
            .order_by(Sesion.creado_en.desc())
        )
        return [_sesion_a_dominio(f) for f in self._db.execute(stmt).scalars()]


def _rol_a_dominio(fila: Rol) -> RolDominio:
    return RolDominio(id=fila.id, nombre=fila.nombre, es_sistema=fila.es_sistema)


class RolRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def listar(self) -> list[RolDominio]:
        stmt = select(Rol).order_by(Rol.nombre)
        return [_rol_a_dominio(f) for f in self._db.execute(stmt).scalars()]
