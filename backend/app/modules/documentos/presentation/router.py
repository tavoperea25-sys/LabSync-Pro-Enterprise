"""Endpoints de Documentos. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db
from app.core.ip import ip_valida
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy
from app.modules.documentos.application.documento_service import (
    ActorContexto,
    CarpetaNoEncontrada,
    DocumentoService,
)
from app.modules.documentos.domain.entities import Documento
from app.modules.documentos.domain.ports import FiltrosDocumento
from app.modules.documentos.infrastructure.repositories import (
    CarpetaRepositorySQLAlchemy,
    DocumentoRepositorySQLAlchemy,
    EtiquetaRepositorySQLAlchemy,
    VersionDocumentoRepositorySQLAlchemy,
)
from app.modules.documentos.presentation.schemas import (
    ArchivoConfirmado,
    CarpetaActualizarRequest,
    CarpetaOut,
    CarpetaRequest,
    DocumentoActualizarRequest,
    DocumentoDetalleOut,
    DocumentoOut,
    DocumentoRequest,
    EtiquetaOut,
    EtiquetaRequest,
    FavoritoOut,
    PaginaDocumentosOut,
    RechazarRequest,
    RechazoOut,
    UrlDescargaOut,
    UrlSubidaOut,
    UrlSubidaRequest,
    VersionOut,
    VistaPreviaOut,
)

router = APIRouter(prefix="/api/v1", tags=["documentos"])

_almacenamiento = AlmacenamientoMinIO(get_settings().minio_bucket_documentos)


def _service(db: Session) -> DocumentoService:
    return DocumentoService(
        DocumentoRepositorySQLAlchemy(db),
        VersionDocumentoRepositorySQLAlchemy(db),
        CarpetaRepositorySQLAlchemy(db),
        EtiquetaRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        _almacenamiento,
        ConfiguracionRepositorySQLAlchemy(db),
    )


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_out(documento: Documento) -> DocumentoOut:
    return DocumentoOut(
        id=documento.id,
        carpeta_id=documento.carpeta_id,
        nombre=documento.nombre,
        categoria=documento.categoria,
        estado=documento.estado,
        estado_efectivo=documento.estado_efectivo(date.today()),
        fecha_emision=documento.fecha_emision,
        fecha_vencimiento=documento.fecha_vencimiento,
        responsable_aprobacion_id=documento.responsable_aprobacion_id,
        version_vigente_id=documento.version_vigente_id,
        creado_en=documento.creado_en,
        actualizado_en=documento.actualizado_en,
    )


def _version_a_out(version) -> VersionOut:  # type: ignore[no-untyped-def]
    return VersionOut(
        id=version.id,
        numero_version=version.numero_version,
        nombre_archivo=version.nombre_archivo,
        tamano_bytes=version.tamano_bytes,
        tipo_mime=version.tipo_mime,
        subido_por_id=version.subido_por_id,
        aprobado_por_id=version.aprobado_por_id,
        aprobado_en=version.aprobado_en,
        creado_en=version.creado_en,
    )


def _etiqueta_a_out(etiqueta) -> EtiquetaOut:  # type: ignore[no-untyped-def]
    return EtiquetaOut(id=etiqueta.id, nombre=etiqueta.nombre)


def _carpeta_a_out(carpeta) -> CarpetaOut:  # type: ignore[no-untyped-def]
    return CarpetaOut(
        id=carpeta.id,
        nombre=carpeta.nombre,
        carpeta_padre_id=carpeta.carpeta_padre_id,
        creado_en=carpeta.creado_en,
    )


# ---------------------------------------------------------------------------
# Documentos
# ---------------------------------------------------------------------------


@router.post("/documentos/upload-url", response_model=UrlSubidaOut)
def solicitar_url_subida(
    datos: UrlSubidaRequest,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> UrlSubidaOut:
    url, object_key = _service(db).solicitar_url_subida(
        usuario.laboratorio_id, datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlSubidaOut(url_subida=url, object_key=object_key)


@router.post("/documentos", response_model=DocumentoOut, status_code=201)
def crear_documento(
    datos: DocumentoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> DocumentoOut:
    documento = _service(db).crear_documento(
        usuario.laboratorio_id,
        _actor(request, usuario),
        nombre=datos.nombre,
        carpeta_id=datos.carpeta_id,
        categoria=datos.categoria,
        fecha_emision=datos.fecha_emision,
        fecha_vencimiento=datos.fecha_vencimiento,
        object_key=datos.archivo.object_key,
        nombre_archivo=datos.archivo.nombre_archivo,
        tamano_bytes=datos.archivo.tamano_bytes,
        tipo_mime=datos.archivo.tipo_mime,
    )
    db.commit()
    return _a_out(documento)


@router.get("/documentos/recientes", response_model=list[DocumentoOut])
def listar_recientes(
    db: Session = Depends(get_db), usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer"))
) -> list[DocumentoOut]:
    return [_a_out(d) for d in _service(db).listar_recientes(usuario.laboratorio_id)]


@router.get("/documentos/papelera", response_model=list[DocumentoOut])
def listar_papelera(
    db: Session = Depends(get_db), usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer"))
) -> list[DocumentoOut]:
    return [_a_out(d) for d in _service(db).listar_papelera(usuario.laboratorio_id)]


@router.get("/documentos", response_model=PaginaDocumentosOut)
def listar_documentos(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
    carpeta_id: uuid.UUID | None = Query(default=None),
    categoria: str | None = Query(default=None),
    etiqueta_id: uuid.UUID | None = Query(default=None),
    q: str | None = Query(default=None),
    favoritos: bool = Query(default=False),
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=20, ge=1, le=100),
) -> PaginaDocumentosOut:
    resultado = _service(db).listar(
        usuario.laboratorio_id,
        FiltrosDocumento(
            carpeta_id=carpeta_id,
            categoria=categoria,
            etiqueta_id=etiqueta_id,
            q=q,
            solo_favoritos_de=usuario.id if favoritos else None,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
        ),
    )
    return PaginaDocumentosOut(
        items=[_a_out(d) for d in resultado.items],
        total=resultado.total,
        pagina=resultado.pagina,
        tamano_pagina=resultado.tamano_pagina,
    )


@router.get("/documentos/{documento_id}", response_model=DocumentoDetalleOut)
def obtener_documento(
    documento_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
) -> DocumentoDetalleOut:
    servicio = _service(db)
    documento = servicio.obtener(documento_id)
    versiones = servicio.versiones(documento_id)
    etiquetas = servicio.etiquetas_de(documento_id)
    es_favorito = DocumentoRepositorySQLAlchemy(db).es_favorito(documento_id, usuario.id)
    rechazo = servicio.ultimo_rechazo(documento_id)
    return DocumentoDetalleOut(
        **_a_out(documento).model_dump(),
        versiones=[_version_a_out(v) for v in versiones],
        etiquetas=[_etiqueta_a_out(e) for e in etiquetas],
        es_favorito=es_favorito,
        ultimo_rechazo=RechazoOut(
            comentario=rechazo.valor_nuevo.get("comentario", "") if rechazo.valor_nuevo else "",
            usuario_id=rechazo.usuario_id,
            creado_en=rechazo.creado_en,
        )
        if rechazo
        else None,
    )


@router.patch("/documentos/{documento_id}", response_model=DocumentoOut)
def actualizar_documento(
    documento_id: uuid.UUID,
    datos: DocumentoActualizarRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> DocumentoOut:
    servicio = _service(db)
    documento = None
    if datos.nombre is not None:
        documento = servicio.renombrar(documento_id, datos.nombre, _actor(request, usuario))
    if datos.mover_a_carpeta:
        documento = servicio.mover(documento_id, datos.carpeta_id, _actor(request, usuario))
    if datos.actualizar_metadatos:
        documento = servicio.actualizar_metadatos(
            documento_id,
            _actor(request, usuario),
            categoria=datos.categoria,
            fecha_emision=datos.fecha_emision,
            fecha_vencimiento=datos.fecha_vencimiento,
        )
    if documento is None:
        documento = servicio.obtener(documento_id)
    db.commit()
    return _a_out(documento)


@router.post("/documentos/{documento_id}/aprobar", response_model=DocumentoOut)
def aprobar_documento(
    documento_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.aprobar")),
) -> DocumentoOut:
    documento = _service(db).aprobar(documento_id, _actor(request, usuario))
    db.commit()
    return _a_out(documento)


@router.post("/documentos/{documento_id}/rechazar", response_model=DocumentoOut)
def rechazar_documento(
    documento_id: uuid.UUID,
    datos: RechazarRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.aprobar")),
) -> DocumentoOut:
    documento = _service(db).rechazar(documento_id, _actor(request, usuario), datos.comentario)
    db.commit()
    return _a_out(documento)


@router.post("/documentos/{documento_id}/versiones", response_model=VersionOut, status_code=201)
def subir_nueva_version(
    documento_id: uuid.UUID,
    datos: ArchivoConfirmado,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> VersionOut:
    version = _service(db).subir_nueva_version(
        documento_id,
        _actor(request, usuario),
        object_key=datos.object_key,
        nombre_archivo=datos.nombre_archivo,
        tamano_bytes=datos.tamano_bytes,
        tipo_mime=datos.tipo_mime,
    )
    db.commit()
    return _version_a_out(version)


@router.get(
    "/documentos/{documento_id}/versiones/{numero_version}/download-url", response_model=UrlDescargaOut
)
def obtener_url_descarga(
    documento_id: uuid.UUID,
    numero_version: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
) -> UrlDescargaOut:
    return UrlDescargaOut(url=_service(db).url_descarga(documento_id, numero_version))


@router.get("/documentos/{documento_id}/vista-previa", response_model=VistaPreviaOut)
def obtener_vista_previa(
    documento_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
) -> VistaPreviaOut:
    url, version = _service(db).url_vista_previa(documento_id)
    return VistaPreviaOut(
        url=url,
        nombre_archivo=version.nombre_archivo,
        tipo_mime=version.tipo_mime,
        tamano_bytes=version.tamano_bytes,
    )


@router.post("/documentos/{documento_id}/copiar", response_model=DocumentoOut, status_code=201)
def copiar_documento(
    documento_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> DocumentoOut:
    copia = _service(db).copiar(documento_id, _actor(request, usuario))
    db.commit()
    return _a_out(copia)


@router.delete("/documentos/{documento_id}", status_code=204, response_model=None)
def enviar_a_papelera(
    documento_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> None:
    _service(db).enviar_a_papelera(documento_id, _actor(request, usuario))
    db.commit()


@router.post("/documentos/{documento_id}/restaurar", status_code=204, response_model=None)
def restaurar_documento(
    documento_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> None:
    _service(db).restaurar(documento_id, _actor(request, usuario))
    db.commit()


@router.post("/documentos/{documento_id}/favorito", response_model=FavoritoOut)
def alternar_favorito(
    documento_id: uuid.UUID,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
) -> FavoritoOut:
    es_favorito = _service(db).alternar_favorito(documento_id, usuario.id)
    db.commit()
    return FavoritoOut(es_favorito=es_favorito)


@router.get("/documentos/{documento_id}/etiquetas", response_model=list[EtiquetaOut])
def listar_etiquetas_documento(
    documento_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
) -> list[EtiquetaOut]:
    return [_etiqueta_a_out(e) for e in _service(db).etiquetas_de(documento_id)]


@router.post("/documentos/{documento_id}/etiquetas", response_model=EtiquetaOut, status_code=201)
def asignar_etiqueta(
    documento_id: uuid.UUID,
    datos: EtiquetaRequest,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> EtiquetaOut:
    etiqueta = _service(db).asignar_etiqueta(documento_id, usuario.laboratorio_id, datos.nombre)
    db.commit()
    return _etiqueta_a_out(etiqueta)


@router.delete("/documentos/{documento_id}/etiquetas/{etiqueta_id}", status_code=204, response_model=None)
def quitar_etiqueta(
    documento_id: uuid.UUID,
    etiqueta_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> None:
    _service(db).quitar_etiqueta(documento_id, etiqueta_id)
    db.commit()


@router.get("/etiquetas", response_model=list[EtiquetaOut])
def listar_etiquetas(
    db: Session = Depends(get_db), usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer"))
) -> list[EtiquetaOut]:
    return [_etiqueta_a_out(e) for e in _service(db).listar_etiquetas(usuario.laboratorio_id)]


# ---------------------------------------------------------------------------
# Carpetas
# ---------------------------------------------------------------------------


@router.get("/carpetas", response_model=list[CarpetaOut])
def listar_carpetas(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
    carpeta_padre_id: uuid.UUID | None = Query(default=None),
) -> list[CarpetaOut]:
    return [_carpeta_a_out(c) for c in _service(db).listar_carpetas(usuario.laboratorio_id, carpeta_padre_id)]


@router.get("/carpetas/{carpeta_id}", response_model=CarpetaOut)
def obtener_carpeta(
    carpeta_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("documentos.leer")),
) -> CarpetaOut:
    carpeta = CarpetaRepositorySQLAlchemy(db).obtener_por_id(carpeta_id)
    if carpeta is None:
        raise CarpetaNoEncontrada()
    return _carpeta_a_out(carpeta)


@router.post("/carpetas", response_model=CarpetaOut, status_code=201)
def crear_carpeta(
    datos: CarpetaRequest,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> CarpetaOut:
    carpeta = _service(db).crear_carpeta(usuario.laboratorio_id, datos.nombre, datos.carpeta_padre_id)
    db.commit()
    return _carpeta_a_out(carpeta)


@router.patch("/carpetas/{carpeta_id}", response_model=CarpetaOut)
def renombrar_carpeta(
    carpeta_id: uuid.UUID,
    datos: CarpetaActualizarRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> CarpetaOut:
    carpeta = _service(db).renombrar_carpeta(carpeta_id, datos.nombre)
    db.commit()
    return _carpeta_a_out(carpeta)


@router.delete("/carpetas/{carpeta_id}", status_code=204, response_model=None)
def eliminar_carpeta(
    carpeta_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("documentos.crear")),
) -> None:
    _service(db).eliminar_carpeta(carpeta_id)
    db.commit()
