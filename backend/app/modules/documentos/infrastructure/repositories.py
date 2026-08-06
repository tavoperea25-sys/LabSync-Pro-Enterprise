"""Implementación SQLAlchemy de los repositorios de Documentos."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, case, delete, func, select, text, update
from sqlalchemy.orm import Session

from app.modules.documentos.domain.entities import Carpeta as CarpetaDominio
from app.modules.documentos.domain.entities import Documento as DocumentoDominio
from app.modules.documentos.domain.entities import Etiqueta as EtiquetaDominio
from app.modules.documentos.domain.entities import VersionDocumento as VersionDominio
from app.modules.documentos.domain.ports import FiltrosDocumento, PaginaDocumentos
from app.modules.documentos.infrastructure.models import (
    Carpeta,
    Documento,
    DocumentoEtiqueta,
    DocumentoFavorito,
    Etiqueta,
    VersionDocumento,
)


def _carpeta_a_dominio(fila: Carpeta) -> CarpetaDominio:
    return CarpetaDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        nombre=fila.nombre,
        carpeta_padre_id=fila.carpeta_padre_id,
        creado_en=fila.creado_en,
    )


def _etiqueta_a_dominio(fila: Etiqueta) -> EtiquetaDominio:
    return EtiquetaDominio(id=fila.id, laboratorio_id=fila.laboratorio_id, nombre=fila.nombre)


def _version_a_dominio(fila: VersionDocumento) -> VersionDominio:
    return VersionDominio(
        id=fila.id,
        documento_id=fila.documento_id,
        numero_version=fila.numero_version,
        object_key=fila.object_key,
        nombre_archivo=fila.nombre_archivo,
        tamano_bytes=fila.tamano_bytes,
        tipo_mime=fila.tipo_mime,
        subido_por_id=fila.subido_por_id,
        aprobado_por_id=fila.aprobado_por_id,
        aprobado_en=fila.aprobado_en,
        creado_en=fila.creado_en,
    )


def _documento_a_dominio(fila: Documento) -> DocumentoDominio:
    return DocumentoDominio(
        id=fila.id,
        laboratorio_id=fila.laboratorio_id,
        carpeta_id=fila.carpeta_id,
        nombre=fila.nombre,
        categoria=fila.categoria,
        estado=fila.estado,
        fecha_emision=fila.fecha_emision,
        fecha_vencimiento=fila.fecha_vencimiento,
        responsable_aprobacion_id=fila.responsable_aprobacion_id,
        version_vigente_id=fila.version_vigente_id,
        eliminado_en=fila.eliminado_en,
        creado_en=fila.creado_en,
        actualizado_en=fila.actualizado_en,
    )


class CarpetaRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, carpeta: CarpetaDominio) -> CarpetaDominio:
        fila = Carpeta(
            id=carpeta.id,
            laboratorio_id=carpeta.laboratorio_id,
            nombre=carpeta.nombre,
            carpeta_padre_id=carpeta.carpeta_padre_id,
        )
        self._db.add(fila)
        self._db.flush()
        return _carpeta_a_dominio(fila)

    def obtener_por_id(self, carpeta_id: uuid.UUID) -> CarpetaDominio | None:
        fila = self._db.get(Carpeta, carpeta_id)
        return _carpeta_a_dominio(fila) if fila else None

    def listar(self, laboratorio_id: uuid.UUID, carpeta_padre_id: uuid.UUID | None) -> list[CarpetaDominio]:
        stmt = select(Carpeta).where(Carpeta.carpeta_padre_id == carpeta_padre_id).order_by(Carpeta.nombre)
        return [_carpeta_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def existe_nombre(
        self,
        laboratorio_id: uuid.UUID,
        carpeta_padre_id: uuid.UUID | None,
        nombre: str,
        excluir_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = select(Carpeta.id).where(
            Carpeta.carpeta_padre_id == carpeta_padre_id, Carpeta.nombre == nombre
        )
        if excluir_id:
            stmt = stmt.where(Carpeta.id != excluir_id)
        return self._db.execute(stmt).scalar_one_or_none() is not None

    def tiene_contenido(self, carpeta_id: uuid.UUID) -> bool:
        tiene_subcarpetas = (
            self._db.execute(select(Carpeta.id).where(Carpeta.carpeta_padre_id == carpeta_id).limit(1))
            .scalar_one_or_none()
            is not None
        )
        if tiene_subcarpetas:
            return True
        # Incluye documentos en papelera a propósito: siguen teniendo una FK
        # `carpeta_id` válida hacia esta carpeta (para poder restaurarse en
        # el mismo lugar), así que un DELETE físico de la carpeta fallaría
        # igual por integridad referencial aunque el documento esté oculto
        # en los listados normales.
        tiene_documentos = (
            self._db.execute(select(Documento.id).where(Documento.carpeta_id == carpeta_id).limit(1))
            .scalar_one_or_none()
            is not None
        )
        return tiene_documentos

    def actualizar(self, carpeta: CarpetaDominio) -> CarpetaDominio:
        self._db.execute(
            update(Carpeta)
            .where(Carpeta.id == carpeta.id)
            .values(nombre=carpeta.nombre, carpeta_padre_id=carpeta.carpeta_padre_id)
        )
        fila = self._db.get(Carpeta, carpeta.id)
        assert fila is not None
        return _carpeta_a_dominio(fila)

    def eliminar(self, carpeta_id: uuid.UUID) -> None:
        self._db.execute(delete(Carpeta).where(Carpeta.id == carpeta_id))


class EtiquetaRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def listar(self, laboratorio_id: uuid.UUID) -> list[EtiquetaDominio]:
        stmt = select(Etiqueta).order_by(Etiqueta.nombre)
        return [_etiqueta_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def obtener_o_crear(self, laboratorio_id: uuid.UUID, nombre: str) -> EtiquetaDominio:
        fila = self._db.execute(select(Etiqueta).where(Etiqueta.nombre == nombre)).scalar_one_or_none()
        if fila is None:
            fila = Etiqueta(id=uuid.uuid4(), laboratorio_id=laboratorio_id, nombre=nombre)
            self._db.add(fila)
            self._db.flush()
        return _etiqueta_a_dominio(fila)

    def asignar(self, documento_id: uuid.UUID, etiqueta_id: uuid.UUID) -> None:
        ya_existe = self._db.execute(
            select(DocumentoEtiqueta).where(
                DocumentoEtiqueta.documento_id == documento_id, DocumentoEtiqueta.etiqueta_id == etiqueta_id
            )
        ).scalar_one_or_none()
        if ya_existe is not None:
            return
        documento = self._db.get(Documento, documento_id)
        assert documento is not None
        self._db.add(
            DocumentoEtiqueta(
                laboratorio_id=documento.laboratorio_id, documento_id=documento_id, etiqueta_id=etiqueta_id
            )
        )

    def quitar(self, documento_id: uuid.UUID, etiqueta_id: uuid.UUID) -> None:
        self._db.execute(
            delete(DocumentoEtiqueta).where(
                DocumentoEtiqueta.documento_id == documento_id, DocumentoEtiqueta.etiqueta_id == etiqueta_id
            )
        )

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[EtiquetaDominio]:
        stmt = (
            select(Etiqueta)
            .join(DocumentoEtiqueta, DocumentoEtiqueta.etiqueta_id == Etiqueta.id)
            .where(DocumentoEtiqueta.documento_id == documento_id)
            .order_by(Etiqueta.nombre)
        )
        return [_etiqueta_a_dominio(f) for f in self._db.execute(stmt).scalars()]


class VersionDocumentoRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, version: VersionDominio) -> VersionDominio:
        documento = self._db.get(Documento, version.documento_id)
        assert documento is not None
        fila = VersionDocumento(
            id=version.id,
            laboratorio_id=documento.laboratorio_id,
            documento_id=version.documento_id,
            numero_version=version.numero_version,
            object_key=version.object_key,
            nombre_archivo=version.nombre_archivo,
            tamano_bytes=version.tamano_bytes,
            tipo_mime=version.tipo_mime,
            subido_por_id=version.subido_por_id,
        )
        self._db.add(fila)
        self._db.flush()
        return _version_a_dominio(fila)

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[VersionDominio]:
        stmt = (
            select(VersionDocumento)
            .where(VersionDocumento.documento_id == documento_id)
            .order_by(VersionDocumento.numero_version.desc())
        )
        return [_version_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def obtener(self, documento_id: uuid.UUID, numero_version: int) -> VersionDominio | None:
        fila = self._db.execute(
            select(VersionDocumento).where(
                VersionDocumento.documento_id == documento_id,
                VersionDocumento.numero_version == numero_version,
            )
        ).scalar_one_or_none()
        return _version_a_dominio(fila) if fila else None

    def siguiente_numero_version(self, documento_id: uuid.UUID) -> int:
        maximo = self._db.execute(
            select(func.max(VersionDocumento.numero_version)).where(
                VersionDocumento.documento_id == documento_id
            )
        ).scalar_one()
        return (maximo or 0) + 1

    def obtener_por_id(self, version_id: uuid.UUID) -> VersionDominio | None:
        fila = self._db.get(VersionDocumento, version_id)
        return _version_a_dominio(fila) if fila else None

    def marcar_aprobada(self, version_id: uuid.UUID, usuario_id: uuid.UUID | None) -> VersionDominio:
        self._db.execute(
            update(VersionDocumento)
            .where(VersionDocumento.id == version_id)
            .values(aprobado_por_id=usuario_id, aprobado_en=datetime.utcnow())
        )
        fila = self._db.get(VersionDocumento, version_id)
        assert fila is not None
        return _version_a_dominio(fila)


class DocumentoRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def crear(self, documento: DocumentoDominio) -> DocumentoDominio:
        fila = Documento(
            id=documento.id,
            laboratorio_id=documento.laboratorio_id,
            carpeta_id=documento.carpeta_id,
            nombre=documento.nombre,
            categoria=documento.categoria,
            estado=documento.estado,
            fecha_emision=documento.fecha_emision,
            fecha_vencimiento=documento.fecha_vencimiento,
            responsable_aprobacion_id=documento.responsable_aprobacion_id,
        )
        self._db.add(fila)
        self._db.flush()
        return _documento_a_dominio(fila)

    def obtener_por_id(self, documento_id: uuid.UUID) -> DocumentoDominio | None:
        fila = self._db.get(Documento, documento_id)
        return _documento_a_dominio(fila) if fila else None

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosDocumento) -> PaginaDocumentos:
        stmt = select(Documento)
        if not filtros.incluir_eliminados:
            stmt = stmt.where(Documento.eliminado_en.is_(None))
        if filtros.carpeta_id is not None:
            stmt = stmt.where(Documento.carpeta_id == filtros.carpeta_id)
        elif not filtros.q and filtros.etiqueta_id is None and filtros.solo_favoritos_de is None:
            # Sin carpeta ni criterio de búsqueda/etiqueta/favoritos, se
            # navega la raíz por defecto en vez de listar todo el árbol.
            stmt = stmt.where(Documento.carpeta_id.is_(None))
        if filtros.categoria:
            stmt = stmt.where(Documento.categoria == filtros.categoria)
        if filtros.etiqueta_id is not None:
            stmt = stmt.join(DocumentoEtiqueta, DocumentoEtiqueta.documento_id == Documento.id).where(
                DocumentoEtiqueta.etiqueta_id == filtros.etiqueta_id
            )
        if filtros.solo_favoritos_de is not None:
            stmt = stmt.join(DocumentoFavorito, DocumentoFavorito.documento_id == Documento.id).where(
                DocumentoFavorito.usuario_id == filtros.solo_favoritos_de
            )
        if filtros.q:
            vector = func.to_tsvector(
                "spanish", func.coalesce(Documento.nombre, "") + " " + func.coalesce(Documento.categoria, "")
            )
            stmt = stmt.where(vector.op("@@")(func.plainto_tsquery("spanish", filtros.q)))

        total = self._db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()

        stmt = (
            stmt.order_by(Documento.nombre)
            .offset((filtros.pagina - 1) * filtros.tamano_pagina)
            .limit(filtros.tamano_pagina)
        )
        filas = self._db.execute(stmt).scalars().all()

        return PaginaDocumentos(
            items=[_documento_a_dominio(f) for f in filas],
            total=total,
            pagina=filtros.pagina,
            tamano_pagina=filtros.tamano_pagina,
        )

    def listar_todos(self, laboratorio_id: uuid.UUID) -> list[DocumentoDominio]:
        stmt = (
            select(Documento)
            .where(Documento.eliminado_en.is_(None))
            .order_by(Documento.nombre)
            .limit(5000)
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_recientes(self, laboratorio_id: uuid.UUID, limite: int) -> list[DocumentoDominio]:
        stmt = (
            select(Documento)
            .where(Documento.eliminado_en.is_(None))
            .order_by(Documento.actualizado_en.desc())
            .limit(limite)
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_vigencia_critica(self, laboratorio_id: uuid.UUID, dias_umbral: int) -> list[DocumentoDominio]:
        limite = datetime.utcnow().date() + timedelta(days=dias_umbral)
        stmt = select(Documento).where(
            Documento.eliminado_en.is_(None),
            Documento.fecha_vencimiento.is_not(None),
            Documento.fecha_vencimiento <= limite,
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def contar_por_estado_efectivo(self, hoy: date) -> dict[str, int]:
        # Traducción 1:1 de `Documento.estado_efectivo()` (RN-DOC-01): el
        # vencimiento manda sobre el estado manual, sin excepción.
        estado_efectivo = case(
            (and_(Documento.fecha_vencimiento.is_not(None), Documento.fecha_vencimiento < hoy), "vencido"),
            else_=Documento.estado,
        )
        stmt = (
            select(estado_efectivo, func.count())
            .where(Documento.eliminado_en.is_(None))
            .group_by(estado_efectivo)
        )
        return dict(self._db.execute(stmt).tuples().all())

    def listar_por_vencimiento_rango(
        self, laboratorio_id: uuid.UUID, desde: date, hasta: date
    ) -> list[DocumentoDominio]:
        stmt = select(Documento).where(
            Documento.eliminado_en.is_(None),
            Documento.fecha_vencimiento.is_not(None),
            Documento.fecha_vencimiento >= desde,
            Documento.fecha_vencimiento <= hasta,
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_papelera(self, laboratorio_id: uuid.UUID) -> list[DocumentoDominio]:
        stmt = (
            select(Documento)
            .where(Documento.eliminado_en.is_not(None))
            .order_by(Documento.eliminado_en.desc())
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def listar_vigentes(self, laboratorio_id: uuid.UUID) -> list[DocumentoDominio]:
        stmt = (
            select(Documento)
            .where(Documento.eliminado_en.is_(None), Documento.estado == "vigente")
            .order_by(Documento.nombre)
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def buscar_texto(self, consulta: str, limite: int) -> list[DocumentoDominio]:
        stmt = (
            select(Documento)
            .where(Documento.eliminado_en.is_(None))
            .where(
                text(
                    "to_tsvector('spanish', coalesce(nombre,'') || ' ' || coalesce(categoria,'')) "
                    "@@ plainto_tsquery('spanish', :consulta)"
                )
            )
            .params(consulta=consulta)
            .limit(limite)
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def actualizar(self, documento: DocumentoDominio) -> DocumentoDominio:
        self._db.execute(
            update(Documento)
            .where(Documento.id == documento.id)
            .values(
                carpeta_id=documento.carpeta_id,
                nombre=documento.nombre,
                categoria=documento.categoria,
                estado=documento.estado,
                fecha_emision=documento.fecha_emision,
                fecha_vencimiento=documento.fecha_vencimiento,
                responsable_aprobacion_id=documento.responsable_aprobacion_id,
                version_vigente_id=documento.version_vigente_id,
                actualizado_en=datetime.utcnow(),
            )
        )
        fila = self._db.get(Documento, documento.id)
        assert fila is not None
        return _documento_a_dominio(fila)

    def eliminar(self, documento_id: uuid.UUID) -> None:
        self._db.execute(
            update(Documento).where(Documento.id == documento_id).values(eliminado_en=datetime.utcnow())
        )

    def restaurar(self, documento_id: uuid.UUID) -> None:
        self._db.execute(update(Documento).where(Documento.id == documento_id).values(eliminado_en=None))

    def listar_papelera_expirada(
        self, laboratorio_id: uuid.UUID, dias_retencion: int
    ) -> list[DocumentoDominio]:
        limite = datetime.now(UTC) - timedelta(days=dias_retencion)
        stmt = select(Documento).where(
            Documento.eliminado_en.is_not(None), Documento.eliminado_en < limite
        )
        return [_documento_a_dominio(f) for f in self._db.execute(stmt).scalars()]

    def purgar(self, documento_id: uuid.UUID) -> list[str]:
        # Orden de borrado obligatorio por las FK sin ON DELETE CASCADE:
        # `documentos.version_vigente_id` apunta a `documentos_versiones`, así
        # que se limpia esa referencia antes de poder borrar las versiones;
        # etiquetas/favoritos son tablas puente que también referencian al
        # documento y deben irse antes que la fila principal.
        object_keys = list(
            self._db.execute(
                select(VersionDocumento.object_key).where(VersionDocumento.documento_id == documento_id)
            ).scalars()
        )
        self._db.execute(
            update(Documento).where(Documento.id == documento_id).values(version_vigente_id=None)
        )
        self._db.execute(delete(VersionDocumento).where(VersionDocumento.documento_id == documento_id))
        self._db.execute(delete(DocumentoEtiqueta).where(DocumentoEtiqueta.documento_id == documento_id))
        self._db.execute(delete(DocumentoFavorito).where(DocumentoFavorito.documento_id == documento_id))
        self._db.execute(delete(Documento).where(Documento.id == documento_id))
        return object_keys

    def es_favorito(self, documento_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        return (
            self._db.execute(
                select(DocumentoFavorito).where(
                    DocumentoFavorito.documento_id == documento_id, DocumentoFavorito.usuario_id == usuario_id
                )
            ).scalar_one_or_none()
            is not None
        )

    def alternar_favorito(self, documento_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        if self.es_favorito(documento_id, usuario_id):
            self._db.execute(
                delete(DocumentoFavorito).where(
                    DocumentoFavorito.documento_id == documento_id, DocumentoFavorito.usuario_id == usuario_id
                )
            )
            return False
        documento = self._db.get(Documento, documento_id)
        assert documento is not None
        self._db.add(
            DocumentoFavorito(
                laboratorio_id=documento.laboratorio_id, documento_id=documento_id, usuario_id=usuario_id
            )
        )
        return True
