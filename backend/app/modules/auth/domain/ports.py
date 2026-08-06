"""Puertos (interfaces) que la infraestructura implementa.

El dominio y la capa de aplicación programan contra estas interfaces, nunca
contra SQLAlchemy directamente — esto es lo que permite testear reglas de
negocio sin base de datos real y extraer el módulo a un servicio
independiente en el futuro sin reescribirlo (docs/13-arquitectura.md).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.modules.auth.domain.entities import Laboratorio, Rol, SesionActiva, Usuario


@dataclass
class PaginaUsuarios:
    """Fase 2/M3 — mismo patrón que PaginaEquipos (equipos/domain/ports.py)."""

    items: list[Usuario] = field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamano_pagina: int = 20


class UsuarioRepository(Protocol):
    def buscar_por_correo(self, laboratorio_id: uuid.UUID, correo: str) -> Usuario | None: ...

    def obtener_por_id(self, usuario_id: uuid.UUID) -> Usuario | None: ...

    def buscar_texto(self, consulta: str, limite: int) -> list[Usuario]:
        """RF-SEARCH-02 — vía el índice GIN `ix_usuarios_busqueda` (0008)."""
        ...

    def registrar_intento_fallido(self, usuario_id: uuid.UUID, bloqueado_hasta: datetime | None) -> None: ...

    def resetear_intentos_fallidos(self, usuario_id: uuid.UUID) -> None: ...

    def crear(self, usuario: Usuario) -> Usuario:
        """RF-USR-01."""
        ...

    def listar(self) -> list[Usuario]:
        """Sin paginar — usado solo por la exportación de datos del
        laboratorio (RF-CFG, configuracion/application/exportacion_service.py),
        que necesita el tenant completo, no una página."""
        ...

    def listar_paginado(self, pagina: int, tamano_pagina: int) -> PaginaUsuarios:
        """RF-USR — pantalla de administración de usuarios. Fase 2/M3:
        reemplaza el listado sin límite que tenía el endpoint antes."""
        ...

    def actualizar(self, usuario: Usuario) -> Usuario:
        """Nombre, estado y `debe_cambiar_password` — nunca la contraseña
        (eso pasa por un flujo dedicado, no por una edición genérica)."""
        ...

    def existe_correo(
        self, laboratorio_id: uuid.UUID, correo: str, excluir_id: uuid.UUID | None = None
    ) -> bool:
        """RN-USR-03."""
        ...

    def contar_administradores_activos(self, excluir_id: uuid.UUID | None = None) -> int:
        """RN-USR-02 — para bloquear la desactivación del último Administrador."""
        ...

    def asignar_roles(self, usuario_id: uuid.UUID, rol_ids: list[uuid.UUID]) -> None:
        """RF-USR-02 — reemplaza el conjunto completo de roles del usuario."""
        ...

    def actualizar_password(self, usuario_id: uuid.UUID, password_hash: str) -> None:
        """RF-CFG-01 — flujo dedicado de cambio de contraseña, nunca vía
        `actualizar()` genérico (ver su docstring)."""
        ...


class RolRepository(Protocol):
    def listar(self) -> list[Rol]: ...


class LaboratorioRepository(Protocol):
    def existe_activo(self, laboratorio_id: uuid.UUID) -> bool: ...

    def resolver_id_por_slug(self, slug: str) -> uuid.UUID | None: ...

    def obtener_por_id(self, laboratorio_id: uuid.UUID) -> Laboratorio | None:
        """RF-CFG-04."""
        ...

    def actualizar(self, laboratorio: Laboratorio) -> Laboratorio:
        """RF-CFG-04 — nombre y logo institucional."""
        ...


class SesionRepository(Protocol):
    def crear(
        self,
        usuario_id: uuid.UUID,
        laboratorio_id: uuid.UUID,
        refresh_token_hash: str,
        expira_en: datetime,
        ip_origen: str | None,
        user_agent: str | None,
    ) -> SesionActiva: ...

    def buscar_por_hash(self, refresh_token_hash: str) -> SesionActiva | None: ...

    def revocar(self, sesion_id: uuid.UUID) -> None: ...

    def revocar_todas_de_usuario(self, usuario_id: uuid.UUID) -> None: ...

    def listar_activas_de_usuario(self, usuario_id: uuid.UUID) -> list[SesionActiva]:
        """RF-USR-06."""
        ...
