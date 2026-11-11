"""CRUD de categorías de equipo y áreas — RF-CFG-05 (Sprint 12).

Vive en el módulo Equipos (no en Configuración) porque son las tablas de
referencia de ESE módulo (`categorias_equipo`, `areas`) — Configuración solo
las expone bajo el permiso `configuracion.gestionar`, que es la parte
correcta a centralizar (quién puede tocarlas), no dónde vive el modelo."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.errors import ConflictoDeNegocio, ErrorDeDominio, RecursoNoEncontrado
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.equipos.domain.ports import EquipoRepository
from app.modules.equipos.infrastructure.models import Area, CategoriaEquipo, Fabricante, Proveedor
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    CategoriaEquipoRepositorySQLAlchemy,
    FabricanteRepositorySQLAlchemy,
    ProveedorRepositorySQLAlchemy,
)

_MODULO = "configuracion"


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class CategoriaNoEncontrada(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("categoria_no_encontrada", "La categoría no existe.")


class AreaNoEncontrada(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("area_no_encontrada", "El área no existe.")


class ProveedorNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("proveedor_no_encontrado", "El proveedor no existe.")


class FabricanteNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("fabricante_no_encontrado", "El fabricante no existe.")


class NombreYaExiste(ConflictoDeNegocio):
    def __init__(self, codigo: str, etiqueta: str) -> None:
        super().__init__(f"{codigo}_nombre_duplicado", f"Ya existe un(a) {etiqueta} con ese nombre.")


class EnUso(ConflictoDeNegocio):
    def __init__(self, codigo: str, etiqueta: str) -> None:
        # `codigo` es siempre ASCII (para que el código de error sea estable
        # y fácil de comparar en clientes) — `etiqueta` sí lleva tilde, es
        # solo para el mensaje legible.
        super().__init__(
            f"{codigo}_en_uso", f"No se puede eliminar: hay equipos que usan este(a) {etiqueta}."
        )


class FrecuenciaInvalida(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "frecuencia_invalida", "La frecuencia de calibración por defecto debe ser un entero positivo."
        )


class ReferenciaService:
    def __init__(
        self,
        categorias: CategoriaEquipoRepositorySQLAlchemy,
        areas: AreaRepositorySQLAlchemy,
        equipos: EquipoRepository,
        auditoria: AuditoriaRepository,
        proveedores: ProveedorRepositorySQLAlchemy,
        fabricantes: FabricanteRepositorySQLAlchemy,
    ) -> None:
        self._categorias = categorias
        self._areas = areas
        self._equipos = equipos
        self._auditoria = auditoria
        self._proveedores = proveedores
        self._fabricantes = fabricantes

    # ---- Categorías ---------------------------------------------------------

    def crear_categoria(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        nombre: str,
        frecuencia_calibracion_default_meses: int | None,
        bloquea_activacion_si_calibracion_vencida: bool = False,
    ) -> CategoriaEquipo:
        if frecuencia_calibracion_default_meses is not None and frecuencia_calibracion_default_meses <= 0:
            raise FrecuenciaInvalida()
        if self._categorias.existe_nombre(laboratorio_id, nombre):
            raise NombreYaExiste("categoria", "categoría")
        fila = self._categorias.crear(
            laboratorio_id,
            nombre,
            frecuencia_calibracion_default_meses,
            bloquea_activacion_si_calibracion_vencida,
        )
        self._auditar(laboratorio_id, actor, "crear_categoria", fila.id, {"nombre": nombre})
        return fila

    def actualizar_categoria(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        categoria_id: uuid.UUID,
        nombre: str,
        frecuencia_calibracion_default_meses: int | None,
        bloquea_activacion_si_calibracion_vencida: bool = False,
    ) -> CategoriaEquipo:
        if frecuencia_calibracion_default_meses is not None and frecuencia_calibracion_default_meses <= 0:
            raise FrecuenciaInvalida()
        if self._categorias.obtener_por_id(categoria_id) is None:
            raise CategoriaNoEncontrada()
        if self._categorias.existe_nombre(laboratorio_id, nombre, excluir_id=categoria_id):
            raise NombreYaExiste("categoria", "categoría")
        fila = self._categorias.actualizar(
            categoria_id,
            nombre,
            frecuencia_calibracion_default_meses,
            bloquea_activacion_si_calibracion_vencida,
        )
        self._auditar(laboratorio_id, actor, "actualizar_categoria", categoria_id, {"nombre": nombre})
        return fila

    def eliminar_categoria(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, categoria_id: uuid.UUID
    ) -> None:
        if self._categorias.obtener_por_id(categoria_id) is None:
            raise CategoriaNoEncontrada()
        if self._equipos.existe_con_categoria(categoria_id):
            raise EnUso("categoria", "categoría")
        self._categorias.eliminar(categoria_id)
        self._auditar(laboratorio_id, actor, "eliminar_categoria", categoria_id, None)

    # ---- Áreas ----------------------------------------------------------------

    def crear_area(self, laboratorio_id: uuid.UUID, actor: ActorContexto, nombre: str) -> Area:
        if self._areas.existe_nombre(laboratorio_id, nombre):
            raise NombreYaExiste("area", "área")
        fila = self._areas.crear(laboratorio_id, nombre)
        self._auditar(laboratorio_id, actor, "crear_area", fila.id, {"nombre": nombre})
        return fila

    def actualizar_area(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, area_id: uuid.UUID, nombre: str
    ) -> Area:
        if self._areas.obtener_por_id(area_id) is None:
            raise AreaNoEncontrada()
        if self._areas.existe_nombre(laboratorio_id, nombre, excluir_id=area_id):
            raise NombreYaExiste("area", "área")
        fila = self._areas.actualizar(area_id, nombre)
        self._auditar(laboratorio_id, actor, "actualizar_area", area_id, {"nombre": nombre})
        return fila

    def eliminar_area(self, laboratorio_id: uuid.UUID, actor: ActorContexto, area_id: uuid.UUID) -> None:
        if self._areas.obtener_por_id(area_id) is None:
            raise AreaNoEncontrada()
        if self._equipos.existe_con_area(area_id):
            raise EnUso("area", "área")
        self._areas.eliminar(area_id)
        self._auditar(laboratorio_id, actor, "eliminar_area", area_id, None)

    # ---- Proveedores (Fase 2 de hojas de vida) ---------------------------------

    def crear_proveedor(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Proveedor:
        if self._proveedores.existe_nombre(laboratorio_id, nombre):
            raise NombreYaExiste("proveedor", "proveedor")
        fila = self._proveedores.crear(
            laboratorio_id, nombre, pais_ciudad, direccion, email, telefono, contacto
        )
        self._auditar(laboratorio_id, actor, "crear_proveedor", fila.id, {"nombre": nombre})
        return fila

    def actualizar_proveedor(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        proveedor_id: uuid.UUID,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Proveedor:
        if self._proveedores.obtener_por_id(proveedor_id) is None:
            raise ProveedorNoEncontrado()
        if self._proveedores.existe_nombre(laboratorio_id, nombre, excluir_id=proveedor_id):
            raise NombreYaExiste("proveedor", "proveedor")
        fila = self._proveedores.actualizar(
            proveedor_id, nombre, pais_ciudad, direccion, email, telefono, contacto
        )
        self._auditar(laboratorio_id, actor, "actualizar_proveedor", proveedor_id, {"nombre": nombre})
        return fila

    def eliminar_proveedor(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, proveedor_id: uuid.UUID
    ) -> None:
        if self._proveedores.obtener_por_id(proveedor_id) is None:
            raise ProveedorNoEncontrado()
        if self._equipos.existe_con_proveedor(proveedor_id):
            raise EnUso("proveedor", "proveedor")
        self._proveedores.eliminar(proveedor_id)
        self._auditar(laboratorio_id, actor, "eliminar_proveedor", proveedor_id, None)

    # ---- Fabricantes (Fase 2 de hojas de vida) ---------------------------------

    def crear_fabricante(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Fabricante:
        if self._fabricantes.existe_nombre(laboratorio_id, nombre):
            raise NombreYaExiste("fabricante", "fabricante")
        fila = self._fabricantes.crear(
            laboratorio_id, nombre, pais_ciudad, direccion, email, telefono, contacto
        )
        self._auditar(laboratorio_id, actor, "crear_fabricante", fila.id, {"nombre": nombre})
        return fila

    def actualizar_fabricante(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        fabricante_id: uuid.UUID,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Fabricante:
        if self._fabricantes.obtener_por_id(fabricante_id) is None:
            raise FabricanteNoEncontrado()
        if self._fabricantes.existe_nombre(laboratorio_id, nombre, excluir_id=fabricante_id):
            raise NombreYaExiste("fabricante", "fabricante")
        fila = self._fabricantes.actualizar(
            fabricante_id, nombre, pais_ciudad, direccion, email, telefono, contacto
        )
        self._auditar(laboratorio_id, actor, "actualizar_fabricante", fabricante_id, {"nombre": nombre})
        return fila

    def eliminar_fabricante(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, fabricante_id: uuid.UUID
    ) -> None:
        if self._fabricantes.obtener_por_id(fabricante_id) is None:
            raise FabricanteNoEncontrado()
        if self._equipos.existe_con_fabricante(fabricante_id):
            raise EnUso("fabricante", "fabricante")
        self._fabricantes.eliminar(fabricante_id)
        self._auditar(laboratorio_id, actor, "eliminar_fabricante", fabricante_id, None)

    def _auditar(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        accion: str,
        entidad_id: uuid.UUID | None,
        valor_nuevo: dict | None,
    ) -> None:
        self._auditoria.registrar(
            laboratorio_id=laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion=accion,
            entidad_tipo="referencia_equipo",
            entidad_id=entidad_id,
            valor_anterior=None,
            valor_nuevo=valor_nuevo,
        )
