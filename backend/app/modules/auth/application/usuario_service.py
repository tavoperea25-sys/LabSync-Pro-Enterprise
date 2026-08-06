"""Casos de uso de administración de usuarios — RF-USR-01 a 07 (Sprint 10).

Vive en el módulo Auth (no un módulo `usuarios` aparte) porque opera sobre
las mismas tablas (usuarios, roles, sesiones) que Auth ya posee desde el
Sprint 1 — separar la administración del flujo de login habría significado
dos módulos compitiendo por el mismo esquema sin ganar nada a cambio.

No hay flujo de invitación por correo (HU-ADMIN-02): esta versión crea el
usuario con una contraseña que el Administrador define directamente y fuerza
su cambio en el primer login (`debe_cambiar_password=True`, RF-USR-04) — no
existe infraestructura de envío de correo en el proyecto todavía."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace

from app.core.errors import ConflictoDeNegocio, ErrorDeDominio, RecursoNoEncontrado
from app.core.password_policy import validar_password
from app.core.security import hash_password, verificar_password
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.auth.domain.entities import SesionActiva, Usuario
from app.modules.auth.domain.ports import PaginaUsuarios, RolRepository, SesionRepository, UsuarioRepository
from app.modules.configuracion.domain.ports import ConfiguracionRepository
from app.modules.documentos.domain.ports import AlmacenamientoPort

_MODULO = "usuarios"

# RF-CFG-01 — "foto" de perfil. Mismos formatos/límite que el resto de
# imágenes de referencia del proyecto (logo institucional, Sprint 12).
FORMATOS_PERMITIDOS_FOTO_USUARIO: dict[str, tuple[str, ...]] = {
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "png": ("image/png",),
    "webp": ("image/webp",),
}
TAMANO_MAXIMO_FOTO_USUARIO_BYTES = 2 * 1024 * 1024


class FormatoFotoNoSoportado(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "formato_foto_no_soportado",
            "La fotografía debe ser JPG, PNG o WEBP.",
            {
                "formatos_permitidos": sorted(
                    {e for exts in FORMATOS_PERMITIDOS_FOTO_USUARIO.values() for e in exts}
                )
            },
        )


class FotoDemasiadoGrande(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "foto_demasiado_grande",
            f"La fotografía no puede superar {TAMANO_MAXIMO_FOTO_USUARIO_BYTES // (1024 * 1024)}MB.",
        )


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class UsuarioNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("usuario_no_encontrado", "El usuario no existe.")


class SesionNoEncontrada(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("sesion_no_encontrada", "La sesión no existe o ya no está activa.")


class CorreoYaRegistrado(ConflictoDeNegocio):
    def __init__(self) -> None:
        super().__init__(
            "correo_ya_registrado", "Ya existe un usuario con este correo en el laboratorio."
        )


class UltimoAdministrador(ConflictoDeNegocio):
    def __init__(self) -> None:
        super().__init__(
            "ultimo_administrador",
            "No se puede quitar el rol de Administrador ni desactivar al único "
            "Administrador activo del laboratorio (RN-USR-02).",
        )


class SinRoles(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__("roles_requeridos", "Debe asignar al menos un rol.")


class RolInvalido(ErrorDeDominio):
    def __init__(self, rol_id: uuid.UUID) -> None:
        super().__init__("rol_invalido", f"El rol '{rol_id}' no existe.")


class PasswordActualIncorrecta(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__("password_actual_incorrecta", "La contraseña actual no es correcta.")


@dataclass
class DatosUsuario:
    nombre_completo: str
    correo: str
    password: str


@dataclass
class DatosActualizarUsuario:
    nombre_completo: str


class UsuarioService:
    def __init__(
        self,
        usuarios: UsuarioRepository,
        roles: RolRepository,
        sesiones: SesionRepository,
        auditoria: AuditoriaRepository,
        configuraciones: ConfiguracionRepository | None = None,
        almacenamiento: AlmacenamientoPort | None = None,
    ) -> None:
        self._usuarios = usuarios
        self._roles = roles
        self._sesiones = sesiones
        self._auditoria = auditoria
        self._configuraciones = configuraciones
        self._almacenamiento = almacenamiento

    def solicitar_url_foto(self, nombre_archivo: str, tipo_mime: str, tamano_bytes: int) -> tuple[str, str]:
        assert self._almacenamiento is not None
        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        mimes_validos = FORMATOS_PERMITIDOS_FOTO_USUARIO.get(extension)
        if mimes_validos is None or tipo_mime not in mimes_validos:
            raise FormatoFotoNoSoportado()
        if tamano_bytes > TAMANO_MAXIMO_FOTO_USUARIO_BYTES:
            raise FotoDemasiadoGrande()
        object_key = f"{uuid.uuid4()}.{extension}"
        url = self._almacenamiento.url_subida(object_key, tipo_mime)
        return url, object_key

    def url_foto(self, usuario: Usuario) -> str | None:
        if usuario.foto_object_key is None or self._almacenamiento is None:
            return None
        return self._almacenamiento.url_vista_previa(usuario.foto_object_key)

    def _politica_password(self, laboratorio_id: uuid.UUID) -> dict | None:
        if self._configuraciones is None:
            return None
        config = self._configuraciones.obtener(laboratorio_id)
        return config.politica_password if config else None

    # ---- CRUD (RF-USR-01) ------------------------------------------------

    def crear(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        datos: DatosUsuario,
        rol_ids: list[uuid.UUID],
    ) -> Usuario:
        if self._usuarios.existe_correo(laboratorio_id, datos.correo):
            raise CorreoYaRegistrado()
        validar_password(datos.password, self._politica_password(laboratorio_id))
        self._validar_roles(rol_ids)

        creado = self._usuarios.crear(
            Usuario(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                correo=datos.correo,
                password_hash=hash_password(datos.password),
                nombre_completo=datos.nombre_completo,
                estado="activo",
                debe_cambiar_password=True,
                intentos_fallidos=0,
                bloqueado_hasta=None,
            )
        )
        self._usuarios.asignar_roles(creado.id, rol_ids)
        usuario = self.obtener(creado.id)
        self._auditar(usuario, actor, "crear", {"roles": usuario.roles})
        return usuario

    def actualizar(
        self, usuario_id: uuid.UUID, actor: ActorContexto, datos: DatosActualizarUsuario
    ) -> Usuario:
        usuario = self.obtener(usuario_id)
        actualizado = self._usuarios.actualizar(replace(usuario, nombre_completo=datos.nombre_completo))
        self._auditar(actualizado, actor, "actualizar", None)
        return actualizado

    def desactivar(self, usuario_id: uuid.UUID, actor: ActorContexto) -> Usuario:
        """RN-USR-01/02 — revoca todas las sesiones activas al desactivar;
        bloquea si sería el último Administrador activo."""
        usuario = self.obtener(usuario_id)
        self._bloquear_si_es_ultimo_administrador(usuario)
        actualizado = self._usuarios.actualizar(replace(usuario, estado="inactivo"))
        self._sesiones.revocar_todas_de_usuario(usuario_id)
        self._auditar(actualizado, actor, "desactivar", None)
        return actualizado

    def activar(self, usuario_id: uuid.UUID, actor: ActorContexto) -> Usuario:
        usuario = self.obtener(usuario_id)
        actualizado = self._usuarios.actualizar(replace(usuario, estado="activo"))
        self._auditar(actualizado, actor, "activar", None)
        return actualizado

    def listar(self) -> list[Usuario]:
        return self._usuarios.listar()

    def listar_paginado(self, pagina: int, tamano_pagina: int) -> PaginaUsuarios:
        return self._usuarios.listar_paginado(pagina, tamano_pagina)

    # ---- Autoservicio (RF-CFG-01) ------------------------------------------

    def actualizar_perfil_propio(
        self,
        usuario_id: uuid.UUID,
        actor: ActorContexto,
        nombre_completo: str,
        correo: str,
        foto_object_key: str | None = None,
    ) -> Usuario:
        usuario = self.obtener(usuario_id)
        if correo != usuario.correo and self._usuarios.existe_correo(
            usuario.laboratorio_id, correo, excluir_id=usuario_id
        ):
            raise CorreoYaRegistrado()
        actualizado = self._usuarios.actualizar(
            replace(usuario, nombre_completo=nombre_completo, correo=correo, foto_object_key=foto_object_key)
        )
        self._auditar(actualizado, actor, "actualizar_perfil_propio", None)
        return actualizado

    def cambiar_password_propio(
        self,
        usuario_id: uuid.UUID,
        actor: ActorContexto,
        password_actual: str,
        password_nueva: str,
    ) -> None:
        usuario = self.obtener(usuario_id)
        if not verificar_password(password_actual, usuario.password_hash):
            raise PasswordActualIncorrecta()
        validar_password(password_nueva, self._politica_password(usuario.laboratorio_id))
        self._usuarios.actualizar_password(usuario_id, hash_password(password_nueva))
        # Mismo criterio que RN-USR-01 (desactivación): un cambio de
        # contraseña invalida toda sesión existente, incluida la que hizo el
        # cambio — el frontend redirige a login con un mensaje explicativo.
        self._sesiones.revocar_todas_de_usuario(usuario_id)
        self._auditar(usuario, actor, "cambiar_password_propio", None)

    def obtener(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self._usuarios.obtener_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontrado()
        return usuario

    # ---- Roles (RF-USR-02/03) ---------------------------------------------

    def asignar_roles(
        self, usuario_id: uuid.UUID, actor: ActorContexto, rol_ids: list[uuid.UUID]
    ) -> Usuario:
        usuario = self.obtener(usuario_id)
        self._validar_roles(rol_ids)
        nombres_por_id = {r.id: r.nombre for r in self._roles.listar()}
        nombres_nuevos = {nombres_por_id[rid] for rid in rol_ids}
        if "administrador" in usuario.roles and "administrador" not in nombres_nuevos:
            self._bloquear_si_es_ultimo_administrador(usuario)

        self._usuarios.asignar_roles(usuario_id, rol_ids)
        actualizado = self.obtener(usuario_id)
        self._auditar(actualizado, actor, "asignar_roles", {"roles": actualizado.roles})
        return actualizado

    def _validar_roles(self, rol_ids: list[uuid.UUID]) -> None:
        if not rol_ids:
            raise SinRoles()
        disponibles = {r.id for r in self._roles.listar()}
        for rol_id in rol_ids:
            if rol_id not in disponibles:
                raise RolInvalido(rol_id)

    def _bloquear_si_es_ultimo_administrador(self, usuario: Usuario) -> None:
        if "administrador" not in usuario.roles:
            return
        if self._usuarios.contar_administradores_activos(excluir_id=usuario.id) == 0:
            raise UltimoAdministrador()

    # ---- Sesiones (RF-USR-06) ---------------------------------------------

    def listar_sesiones(self, usuario_id: uuid.UUID) -> list[SesionActiva]:
        self.obtener(usuario_id)
        return self._sesiones.listar_activas_de_usuario(usuario_id)

    def cerrar_sesion(self, usuario_id: uuid.UUID, sesion_id: uuid.UUID, actor: ActorContexto) -> None:
        usuario = self.obtener(usuario_id)
        sesiones = self._sesiones.listar_activas_de_usuario(usuario_id)
        if not any(s.id == sesion_id for s in sesiones):
            raise SesionNoEncontrada()
        self._sesiones.revocar(sesion_id)
        self._auditar(usuario, actor, "cerrar_sesion", {"sesion_id": str(sesion_id)})

    # ---- Auditoría (RF-USR-07) ---------------------------------------------

    def _auditar(self, usuario: Usuario, actor: ActorContexto, accion: str, extra: dict | None) -> None:
        self._auditoria.registrar(
            laboratorio_id=usuario.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion=accion,
            entidad_tipo="usuario",
            entidad_id=usuario.id,
            valor_anterior=None,
            valor_nuevo={"correo": usuario.correo, "estado": usuario.estado, **(extra or {})},
        )
