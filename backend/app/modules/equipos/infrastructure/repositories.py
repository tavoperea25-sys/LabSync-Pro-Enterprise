"""Implementación SQLAlchemy del repositorio de Equipos."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.modules.calibraciones.infrastructure.models import Calibracion
from app.modules.equipos.domain.entities import Equipo as EquipoDominio
from app.modules.equipos.domain.entities import EquipoAccesorio as EquipoAccesorioDominio
from app.modules.equipos.domain.entities import EquipoFichaTecnica as EquipoFichaTecnicaDominio
from app.modules.equipos.domain.entities import EquipoManual as EquipoManualDominio
from app.modules.equipos.domain.ports import FiltrosEquipo, PaginaEquipos
from app.modules.equipos.infrastructure.models import (
    Area,
    CategoriaEquipo,
    Equipo,
    EquipoAccesorio,
    EquipoFichaTecnica,
    EquipoManual,
    Fabricante,
    Proveedor,
)


def _a_dominio(fila: Equipo) -> EquipoDominio:
    return EquipoDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        codigo_interno=fila.codigo_interno,
        nombre=fila.nombre,
        estado_operativo=fila.estado_operativo,
        categoria_id=fila.categoria_id,
        area_id=fila.area_id,
        responsable_id=fila.responsable_id,
        marca=fila.marca,
        modelo=fila.modelo,
        numero_serie=fila.numero_serie,
        fabricante=fila.fabricante,
        proveedor=fila.proveedor,
        fecha_adquisicion=fila.fecha_adquisicion,
        observaciones=fila.observaciones,
        foto_object_key=fila.foto_url,
        manual_object_key=fila.manual_object_key,
        proveedor_id=fila.proveedor_id,
        fabricante_id=fila.fabricante_id,
        capitulo=fila.capitulo,
        grupo=fila.grupo,
        subgrupo=fila.subgrupo,
        ubicacion=fila.ubicacion,
        numero_inventario=fila.numero_inventario,
        condicion_fisica=fila.condicion_fisica,
        clasificacion_riesgo=fila.clasificacion_riesgo,
        criticidad=fila.criticidad,
        forma_adquisicion=fila.forma_adquisicion,
        garantia=fila.garantia,
        garantia_inicio=fila.garantia_inicio,
        garantia_fin=fila.garantia_fin,
        eliminado_en=fila.eliminado_en,
        creado_en=fila.creado_en,
        actualizado_en=fila.actualizado_en,
    )


class EquipoRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, equipo: EquipoDominio) -> EquipoDominio:
        fila = Equipo(
            id=equipo.id,
            laboratorio_id=equipo.laboratorio_id,
            codigo_interno=equipo.codigo_interno,
            nombre=equipo.nombre,
            estado_operativo=equipo.estado_operativo,
            categoria_id=equipo.categoria_id,
            area_id=equipo.area_id,
            responsable_id=equipo.responsable_id,
            marca=equipo.marca,
            modelo=equipo.modelo,
            numero_serie=equipo.numero_serie,
            fabricante=equipo.fabricante,
            proveedor=equipo.proveedor,
            fecha_adquisicion=equipo.fecha_adquisicion,
            observaciones=equipo.observaciones,
            foto_url=equipo.foto_object_key,
            manual_object_key=equipo.manual_object_key,
            proveedor_id=equipo.proveedor_id,
            fabricante_id=equipo.fabricante_id,
            capitulo=equipo.capitulo,
            grupo=equipo.grupo,
            subgrupo=equipo.subgrupo,
            ubicacion=equipo.ubicacion,
            numero_inventario=equipo.numero_inventario,
            condicion_fisica=equipo.condicion_fisica,
            clasificacion_riesgo=equipo.clasificacion_riesgo,
            criticidad=equipo.criticidad,
            forma_adquisicion=equipo.forma_adquisicion,
            garantia=equipo.garantia,
            garantia_inicio=equipo.garantia_inicio,
            garantia_fin=equipo.garantia_fin,
        )
        self._db.add(fila)
        self._db.flush()
        return _a_dominio(fila)

    def obtener_por_id(self, equipo_id: uuid.UUID) -> EquipoDominio | None:
        fila = self._db.get(Equipo, equipo_id)
        return _a_dominio(fila) if fila else None

    def existe_codigo(self, codigo_interno: str, excluir_id: uuid.UUID | None = None) -> bool:
        stmt = select(Equipo.id).where(Equipo.codigo_interno == codigo_interno)
        if excluir_id:
            stmt = stmt.where(Equipo.id != excluir_id)
        return self._db.execute(stmt).scalar_one_or_none() is not None

    @staticmethod
    def _con_filtros(filtros: FiltrosEquipo):  # type: ignore[no-untyped-def]
        stmt = select(Equipo)

        if not filtros.incluir_eliminados:
            stmt = stmt.where(Equipo.eliminado_en.is_(None))
        if filtros.categoria_id:
            stmt = stmt.where(Equipo.categoria_id == filtros.categoria_id)
        if filtros.area_id:
            stmt = stmt.where(Equipo.area_id == filtros.area_id)
        if filtros.estado_operativo:
            stmt = stmt.where(Equipo.estado_operativo == filtros.estado_operativo)
        if filtros.q:
            vector = func.to_tsvector(
                "spanish",
                func.coalesce(Equipo.codigo_interno, "")
                + " "
                + func.coalesce(Equipo.nombre, "")
                + " "
                + func.coalesce(Equipo.numero_serie, ""),
            )
            stmt = stmt.where(vector.op("@@")(func.plainto_tsquery("spanish", filtros.q)))
        return stmt

    def listar(self, filtros: FiltrosEquipo) -> PaginaEquipos:
        stmt = self._con_filtros(filtros)

        total = self._db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = (
            stmt.order_by(Equipo.creado_en.desc())
            .offset((filtros.pagina - 1) * filtros.tamano_pagina)
            .limit(filtros.tamano_pagina)
        )
        filas = self._db.execute(stmt).scalars().all()

        return PaginaEquipos(
            items=[_a_dominio(f) for f in filas],
            total=total,
            pagina=filtros.pagina,
            tamano_pagina=filtros.tamano_pagina,
        )

    def actualizar(self, equipo: EquipoDominio) -> EquipoDominio:
        self._db.execute(
            update(Equipo)
            .where(Equipo.id == equipo.id)
            .values(
                nombre=equipo.nombre,
                estado_operativo=equipo.estado_operativo,
                categoria_id=equipo.categoria_id,
                area_id=equipo.area_id,
                responsable_id=equipo.responsable_id,
                marca=equipo.marca,
                modelo=equipo.modelo,
                numero_serie=equipo.numero_serie,
                fabricante=equipo.fabricante,
                proveedor=equipo.proveedor,
                fecha_adquisicion=equipo.fecha_adquisicion,
                observaciones=equipo.observaciones,
                foto_url=equipo.foto_object_key,
                manual_object_key=equipo.manual_object_key,
                proveedor_id=equipo.proveedor_id,
                fabricante_id=equipo.fabricante_id,
                capitulo=equipo.capitulo,
                grupo=equipo.grupo,
                subgrupo=equipo.subgrupo,
                ubicacion=equipo.ubicacion,
                numero_inventario=equipo.numero_inventario,
                condicion_fisica=equipo.condicion_fisica,
                clasificacion_riesgo=equipo.clasificacion_riesgo,
                criticidad=equipo.criticidad,
                forma_adquisicion=equipo.forma_adquisicion,
                garantia=equipo.garantia,
                garantia_inicio=equipo.garantia_inicio,
                garantia_fin=equipo.garantia_fin,
                actualizado_en=datetime.utcnow(),
            )
        )
        fila = self._db.get(Equipo, equipo.id)
        assert fila is not None
        return _a_dominio(fila)

    def eliminar(self, equipo_id: uuid.UUID) -> None:
        self._db.execute(update(Equipo).where(Equipo.id == equipo_id).values(eliminado_en=datetime.utcnow()))

    def listar_todos(self, filtros: FiltrosEquipo) -> list[EquipoDominio]:
        stmt = self._con_filtros(filtros).order_by(Equipo.codigo_interno).limit(5000)
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def contar_por_estado(self) -> dict[str, int]:
        stmt = (
            select(Equipo.estado_operativo, func.count())
            .where(Equipo.eliminado_en.is_(None))
            .group_by(Equipo.estado_operativo)
        )
        return {estado: cantidad for estado, cantidad in self._db.execute(stmt).all()}

    def tiene_calibracion_vencida_bloqueante(self, equipo_id: uuid.UUID) -> bool:
        """RN-EQ-03 — True solo si TODO lo siguiente se cumple: el equipo
        tiene categoría, esa categoría tiene el bloqueo activado, y su
        última calibración registrada ya venció (`proxima_fecha` en el
        pasado). Un equipo sin categoría, con categoría sin el bloqueo, o
        que nunca fue calibrado ("gris", no "Vencido") nunca bloquea —
        la regla habla explícitamente de estado "Vencido", no "sin
        información"."""
        equipo = self._db.get(Equipo, equipo_id)
        if equipo is None or equipo.categoria_id is None:
            return False
        categoria = self._db.get(CategoriaEquipo, equipo.categoria_id)
        if categoria is None or not categoria.bloquea_activacion_si_calibracion_vencida:
            return False
        ultima_proxima_fecha = self._db.execute(
            select(Calibracion.proxima_fecha)
            .where(Calibracion.equipo_id == equipo_id)
            .order_by(Calibracion.fecha_calibracion.desc(), Calibracion.creado_en.desc())
            .limit(1)
        ).scalar_one_or_none()
        if ultima_proxima_fecha is None:
            return False
        return ultima_proxima_fecha < date.today()

    def existe_con_categoria(self, categoria_id: uuid.UUID) -> bool:
        stmt = select(Equipo.id).where(Equipo.categoria_id == categoria_id, Equipo.eliminado_en.is_(None))
        return self._db.execute(stmt).first() is not None

    def existe_con_area(self, area_id: uuid.UUID) -> bool:
        stmt = select(Equipo.id).where(Equipo.area_id == area_id, Equipo.eliminado_en.is_(None))
        return self._db.execute(stmt).first() is not None

    def existe_con_proveedor(self, proveedor_id: uuid.UUID) -> bool:
        stmt = select(Equipo.id).where(Equipo.proveedor_id == proveedor_id, Equipo.eliminado_en.is_(None))
        return self._db.execute(stmt).first() is not None

    def existe_con_fabricante(self, fabricante_id: uuid.UUID) -> bool:
        stmt = select(Equipo.id).where(Equipo.fabricante_id == fabricante_id, Equipo.eliminado_en.is_(None))
        return self._db.execute(stmt).first() is not None

    def buscar_texto(self, consulta: str, limite: int) -> list[EquipoDominio]:
        stmt = (
            select(Equipo)
            .where(
                Equipo.eliminado_en.is_(None),
                text(
                    "to_tsvector('spanish', coalesce(codigo_interno,'') || ' ' || "
                    "coalesce(nombre,'') || ' ' || coalesce(numero_serie,'')) "
                    "@@ plainto_tsquery('spanish', :consulta)"
                ),
            )
            .params(consulta=consulta)
            .limit(limite)
        )
        return [_a_dominio(f) for f in self._db.execute(stmt).scalars()]


class CategoriaEquipoRepositorySQLAlchemy:
    """Datos de referencia para el formulario de Equipos. El CRUD completo
    es RF-CFG-05 (Sprint 12) — antes solo se listaban."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def listar(self) -> list[CategoriaEquipo]:
        return list(self._db.execute(select(CategoriaEquipo).order_by(CategoriaEquipo.nombre)).scalars())

    def obtener_por_id(self, categoria_id: uuid.UUID) -> CategoriaEquipo | None:
        return self._db.get(CategoriaEquipo, categoria_id)

    def crear(
        self,
        laboratorio_id: uuid.UUID,
        nombre: str,
        frecuencia_calibracion_default_meses: int | None,
        bloquea_activacion_si_calibracion_vencida: bool = False,
    ) -> CategoriaEquipo:
        fila = CategoriaEquipo(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            nombre=nombre,
            frecuencia_calibracion_default_meses=frecuencia_calibracion_default_meses,
            bloquea_activacion_si_calibracion_vencida=bloquea_activacion_si_calibracion_vencida,
        )
        self._db.add(fila)
        self._db.flush()
        return fila

    def actualizar(
        self,
        categoria_id: uuid.UUID,
        nombre: str,
        frecuencia_calibracion_default_meses: int | None,
        bloquea_activacion_si_calibracion_vencida: bool = False,
    ) -> CategoriaEquipo:
        fila = self._db.get(CategoriaEquipo, categoria_id)
        assert fila is not None
        fila.nombre = nombre
        fila.frecuencia_calibracion_default_meses = frecuencia_calibracion_default_meses
        fila.bloquea_activacion_si_calibracion_vencida = bloquea_activacion_si_calibracion_vencida
        self._db.flush()
        return fila

    def eliminar(self, categoria_id: uuid.UUID) -> None:
        fila = self._db.get(CategoriaEquipo, categoria_id)
        if fila is not None:
            self._db.delete(fila)
            self._db.flush()

    def existe_nombre(
        self, laboratorio_id: uuid.UUID, nombre: str, excluir_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(CategoriaEquipo.id).where(
            CategoriaEquipo.laboratorio_id == laboratorio_id, CategoriaEquipo.nombre == nombre
        )
        if excluir_id is not None:
            stmt = stmt.where(CategoriaEquipo.id != excluir_id)
        return self._db.execute(stmt).first() is not None


class AreaRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def listar(self) -> list[Area]:
        return list(self._db.execute(select(Area).order_by(Area.nombre)).scalars())

    def obtener_por_id(self, area_id: uuid.UUID) -> Area | None:
        return self._db.get(Area, area_id)

    def crear(self, laboratorio_id: uuid.UUID, nombre: str) -> Area:
        fila = Area(id=uuid.uuid4(), laboratorio_id=laboratorio_id, nombre=nombre)
        self._db.add(fila)
        self._db.flush()
        return fila

    def actualizar(self, area_id: uuid.UUID, nombre: str) -> Area:
        fila = self._db.get(Area, area_id)
        assert fila is not None
        fila.nombre = nombre
        self._db.flush()
        return fila

    def eliminar(self, area_id: uuid.UUID) -> None:
        fila = self._db.get(Area, area_id)
        if fila is not None:
            self._db.delete(fila)
            self._db.flush()

    def existe_nombre(
        self, laboratorio_id: uuid.UUID, nombre: str, excluir_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Area.id).where(Area.laboratorio_id == laboratorio_id, Area.nombre == nombre)
        if excluir_id is not None:
            stmt = stmt.where(Area.id != excluir_id)
        return self._db.execute(stmt).first() is not None


def _normalizado(valor):  # type: ignore[no-untyped-def]
    """`lower(trim(...))`, tanto para una columna como para un literal de
    Python — mismo criterio de normalización que el índice único funcional
    de la migración 0018 (ver su cabecera): dos nombres que solo difieren en
    mayúsculas o espacios se consideran el mismo proveedor/fabricante."""
    return func.lower(func.trim(valor))


class ProveedorRepositorySQLAlchemy:
    """Catálogo de proveedores — Fase 2 de hojas de vida. Mismo patrón que
    `CategoriaEquipoRepositorySQLAlchemy`/`AreaRepositorySQLAlchemy`."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def listar(self) -> list[Proveedor]:
        return list(self._db.execute(select(Proveedor).order_by(Proveedor.nombre)).scalars())

    def obtener_por_id(self, proveedor_id: uuid.UUID) -> Proveedor | None:
        return self._db.get(Proveedor, proveedor_id)

    def crear(
        self,
        laboratorio_id: uuid.UUID,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Proveedor:
        fila = Proveedor(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            nombre=nombre,
            pais_ciudad=pais_ciudad,
            direccion=direccion,
            email=email,
            telefono=telefono,
            contacto=contacto,
        )
        self._db.add(fila)
        self._db.flush()
        return fila

    def actualizar(
        self,
        proveedor_id: uuid.UUID,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Proveedor:
        fila = self._db.get(Proveedor, proveedor_id)
        assert fila is not None
        fila.nombre = nombre
        fila.pais_ciudad = pais_ciudad
        fila.direccion = direccion
        fila.email = email
        fila.telefono = telefono
        fila.contacto = contacto
        self._db.flush()
        return fila

    def eliminar(self, proveedor_id: uuid.UUID) -> None:
        fila = self._db.get(Proveedor, proveedor_id)
        if fila is not None:
            self._db.delete(fila)
            self._db.flush()

    def existe_nombre(
        self, laboratorio_id: uuid.UUID, nombre: str, excluir_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Proveedor.id).where(
            Proveedor.laboratorio_id == laboratorio_id, _normalizado(Proveedor.nombre) == _normalizado(nombre)
        )
        if excluir_id is not None:
            stmt = stmt.where(Proveedor.id != excluir_id)
        return self._db.execute(stmt).first() is not None


class FabricanteRepositorySQLAlchemy:
    """Catálogo de fabricantes — mismo diseño que `ProveedorRepositorySQLAlchemy`."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def listar(self) -> list[Fabricante]:
        return list(self._db.execute(select(Fabricante).order_by(Fabricante.nombre)).scalars())

    def obtener_por_id(self, fabricante_id: uuid.UUID) -> Fabricante | None:
        return self._db.get(Fabricante, fabricante_id)

    def crear(
        self,
        laboratorio_id: uuid.UUID,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Fabricante:
        fila = Fabricante(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            nombre=nombre,
            pais_ciudad=pais_ciudad,
            direccion=direccion,
            email=email,
            telefono=telefono,
            contacto=contacto,
        )
        self._db.add(fila)
        self._db.flush()
        return fila

    def actualizar(
        self,
        fabricante_id: uuid.UUID,
        nombre: str,
        pais_ciudad: str | None,
        direccion: str | None,
        email: str | None,
        telefono: str | None,
        contacto: str | None,
    ) -> Fabricante:
        fila = self._db.get(Fabricante, fabricante_id)
        assert fila is not None
        fila.nombre = nombre
        fila.pais_ciudad = pais_ciudad
        fila.direccion = direccion
        fila.email = email
        fila.telefono = telefono
        fila.contacto = contacto
        self._db.flush()
        return fila

    def eliminar(self, fabricante_id: uuid.UUID) -> None:
        fila = self._db.get(Fabricante, fabricante_id)
        if fila is not None:
            self._db.delete(fila)
            self._db.flush()

    def existe_nombre(
        self, laboratorio_id: uuid.UUID, nombre: str, excluir_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Fabricante.id).where(
            Fabricante.laboratorio_id == laboratorio_id,
            _normalizado(Fabricante.nombre) == _normalizado(nombre),
        )
        if excluir_id is not None:
            stmt = stmt.where(Fabricante.id != excluir_id)
        return self._db.execute(stmt).first() is not None


def _ficha_tecnica_a_dominio(fila: EquipoFichaTecnica) -> EquipoFichaTecnicaDominio:
    return EquipoFichaTecnicaDominio(
        equipo_id=fila.equipo_id,
        voltaje=fila.voltaje,
        corriente=fila.corriente,
        frecuencia=fila.frecuencia,
        corriente_ma=fila.corriente_ma,
        variable_medicion=fila.variable_medicion,
        rango_medicion=fila.rango_medicion,
        rpm=fila.rpm,
        temperatura_trabajo=fila.temperatura_trabajo,
        humedad_trabajo=fila.humedad_trabajo,
        peso=fila.peso,
        dimensiones=fila.dimensiones,
        color=fila.color,
        numero_puertas=fila.numero_puertas,
        clase_sistema=fila.clase_sistema,
        alimentacion=fila.alimentacion,
        uso=fila.uso,
        uso_especifico=fila.uso_especifico,
        condiciones_ambientales=fila.condiciones_ambientales,
        datos_adicionales=fila.datos_adicionales,
        creado_en=fila.creado_en,
        actualizado_en=fila.actualizado_en,
    )


def _accesorio_a_dominio(fila: EquipoAccesorio) -> EquipoAccesorioDominio:
    return EquipoAccesorioDominio(
        id=fila.id,
        equipo_id=fila.equipo_id,
        cantidad=fila.cantidad,
        descripcion=fila.descripcion,
        observaciones=fila.observaciones,
        creado_en=fila.creado_en,
    )


def _manual_a_dominio(fila: EquipoManual) -> EquipoManualDominio:
    return EquipoManualDominio(
        id=fila.id,
        equipo_id=fila.equipo_id,
        tipo=fila.tipo,
        disponible=fila.disponible,
        idioma=fila.idioma,
        object_key=fila.object_key,
        creado_en=fila.creado_en,
        actualizado_en=fila.actualizado_en,
    )


class FichaTecnicaRepositorySQLAlchemy:
    """Ficha técnica extendida (1:1), accesorios (1:N) y manuales (1:N,
    único por tipo) de un equipo — Fase 2 de hojas de vida. Las tres tablas
    viven juntas en un solo repositorio porque conceptualmente son una sola
    cosa ("la ficha técnica extendida"), mismo criterio de agrupación que
    `ReferenciaService` ya aplica a categorías+áreas en la capa de
    aplicación."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ---- Ficha técnica (1:1) -------------------------------------------------

    def obtener_ficha_tecnica(self, equipo_id: uuid.UUID) -> EquipoFichaTecnicaDominio | None:
        fila = self._db.get(EquipoFichaTecnica, equipo_id)
        return _ficha_tecnica_a_dominio(fila) if fila else None

    def guardar_ficha_tecnica(
        self, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID, datos: dict
    ) -> EquipoFichaTecnicaDominio:
        fila = self._db.get(EquipoFichaTecnica, equipo_id)
        if fila is None:
            fila = EquipoFichaTecnica(equipo_id=equipo_id, laboratorio_id=laboratorio_id, **datos)
            self._db.add(fila)
        else:
            for campo, valor in datos.items():
                setattr(fila, campo, valor)
            fila.actualizado_en = datetime.utcnow()
        self._db.flush()
        return _ficha_tecnica_a_dominio(fila)

    # ---- Accesorios (1:N) -----------------------------------------------------

    def listar_accesorios(self, equipo_id: uuid.UUID) -> list[EquipoAccesorioDominio]:
        stmt = (
            select(EquipoAccesorio)
            .where(EquipoAccesorio.equipo_id == equipo_id)
            .order_by(EquipoAccesorio.creado_en)
        )
        return [_accesorio_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def obtener_accesorio(self, accesorio_id: uuid.UUID) -> EquipoAccesorioDominio | None:
        fila = self._db.get(EquipoAccesorio, accesorio_id)
        return _accesorio_a_dominio(fila) if fila else None

    def crear_accesorio(
        self,
        laboratorio_id: uuid.UUID,
        equipo_id: uuid.UUID,
        cantidad: int | None,
        descripcion: str,
        observaciones: str | None,
    ) -> EquipoAccesorioDominio:
        fila = EquipoAccesorio(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            equipo_id=equipo_id,
            cantidad=cantidad,
            descripcion=descripcion,
            observaciones=observaciones,
        )
        self._db.add(fila)
        self._db.flush()
        return _accesorio_a_dominio(fila)

    def actualizar_accesorio(
        self, accesorio_id: uuid.UUID, cantidad: int | None, descripcion: str, observaciones: str | None
    ) -> EquipoAccesorioDominio:
        fila = self._db.get(EquipoAccesorio, accesorio_id)
        assert fila is not None
        fila.cantidad = cantidad
        fila.descripcion = descripcion
        fila.observaciones = observaciones
        self._db.flush()
        return _accesorio_a_dominio(fila)

    def eliminar_accesorio(self, accesorio_id: uuid.UUID) -> None:
        fila = self._db.get(EquipoAccesorio, accesorio_id)
        if fila is not None:
            self._db.delete(fila)
            self._db.flush()

    # ---- Manuales (1:N, único por tipo) ----------------------------------------

    def listar_manuales(self, equipo_id: uuid.UUID) -> list[EquipoManualDominio]:
        stmt = select(EquipoManual).where(EquipoManual.equipo_id == equipo_id).order_by(EquipoManual.tipo)
        return [_manual_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def obtener_manual(self, equipo_id: uuid.UUID, tipo: str) -> EquipoManualDominio | None:
        stmt = select(EquipoManual).where(EquipoManual.equipo_id == equipo_id, EquipoManual.tipo == tipo)
        fila = self._db.execute(stmt).scalar_one_or_none()
        return _manual_a_dominio(fila) if fila else None

    def guardar_manual(
        self,
        laboratorio_id: uuid.UUID,
        equipo_id: uuid.UUID,
        tipo: str,
        disponible: bool,
        idioma: str | None,
        object_key: str | None,
    ) -> EquipoManualDominio:
        stmt = select(EquipoManual).where(EquipoManual.equipo_id == equipo_id, EquipoManual.tipo == tipo)
        fila = self._db.execute(stmt).scalar_one_or_none()
        if fila is None:
            fila = EquipoManual(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                equipo_id=equipo_id,
                tipo=tipo,
                disponible=disponible,
                idioma=idioma,
                object_key=object_key,
            )
            self._db.add(fila)
        else:
            fila.disponible = disponible
            fila.idioma = idioma
            fila.object_key = object_key
            fila.actualizado_en = datetime.utcnow()
        self._db.flush()
        return _manual_a_dominio(fila)
