"""Endpoints de Equipos. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ErrorDeDominio
from app.core.ip import ip_valida
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.equipos.application.equipo_service import ActorContexto, DatosEquipo, EquipoService
from app.modules.equipos.application.referencia_service import ActorContexto as ActorReferencia
from app.modules.equipos.application.referencia_service import ReferenciaService
from app.modules.equipos.domain.ports import FiltrosEquipo
from app.modules.equipos.infrastructure.exportador import generar_excel
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    CategoriaEquipoRepositorySQLAlchemy,
    EquipoRepositorySQLAlchemy,
)
from app.modules.equipos.presentation.schemas import (
    AreaOut,
    AreaRequest,
    CategoriaEquipoOut,
    CategoriaEquipoRequest,
    EquipoOut,
    EquipoRequest,
    HistorialEntradaOut,
    PaginaEquiposOut,
    UrlFotoOut,
    UrlFotoRequest,
    UrlManualOut,
    UrlManualRequest,
)
from app.modules.qr.application.qr_service import QrService
from app.modules.qr.infrastructure.repositories import (
    IncidenciaQrRepositorySQLAlchemy,
    QrTokenRepositorySQLAlchemy,
)

router = APIRouter(prefix="/api/v1", tags=["equipos"])

_almacenamiento_fotos = AlmacenamientoMinIO(get_settings().minio_bucket_fotos_equipos)
_almacenamiento_manuales = AlmacenamientoMinIO(get_settings().minio_bucket_manuales_equipos)


def _service(db: Session) -> EquipoService:
    return EquipoService(
        EquipoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        _almacenamiento_fotos,
        _almacenamiento_manuales,
    )


def _generar_qr(db: Session, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID) -> None:
    """RF-QR-01 — todo equipo nuevo recibe su QR automáticamente, incluidas
    las copias creadas por RF-EQ-05 (duplicar)."""
    qr_service = QrService(
        QrTokenRepositorySQLAlchemy(db), IncidenciaQrRepositorySQLAlchemy(db), EquipoRepositorySQLAlchemy(db)
    )
    qr_service.generar_para_equipo(laboratorio_id, equipo_id)


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_out(equipo, service: EquipoService) -> EquipoOut:  # type: ignore[no-untyped-def]
    return EquipoOut(
        id=equipo.id,
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
        foto_url=service.url_foto(equipo),
        foto_object_key=equipo.foto_object_key,
        manual_url=service.url_manual(equipo),
        manual_object_key=equipo.manual_object_key,
        creado_en=equipo.creado_en,
        actualizado_en=equipo.actualizado_en,
    )


def _a_datos(datos: EquipoRequest) -> DatosEquipo:
    return DatosEquipo(**datos.model_dump())


@router.get("/equipos", response_model=PaginaEquiposOut)
def listar_equipos(
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
    q: str | None = Query(default=None),
    categoria_id: uuid.UUID | None = Query(default=None),
    area_id: uuid.UUID | None = Query(default=None),
    estado_operativo: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=20, ge=1, le=100),
) -> PaginaEquiposOut:
    service = _service(db)
    resultado = service.listar(
        FiltrosEquipo(
            q=q,
            categoria_id=categoria_id,
            area_id=area_id,
            estado_operativo=estado_operativo,
            pagina=pagina,
            tamano_pagina=tamano_pagina,
        )
    )
    return PaginaEquiposOut(
        items=[_a_out(e, service) for e in resultado.items],
        total=resultado.total,
        pagina=resultado.pagina,
        tamano_pagina=resultado.tamano_pagina,
    )


@router.post("/equipos", response_model=EquipoOut, status_code=201)
def crear_equipo(
    datos: EquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> EquipoOut:
    service = _service(db)
    equipo = service.crear(usuario.laboratorio_id, _a_datos(datos), _actor(request, usuario))
    _generar_qr(db, usuario.laboratorio_id, equipo.id)
    db.commit()
    return _a_out(equipo, service)


@router.post("/equipos/upload-url/foto", response_model=UrlFotoOut)
def solicitar_url_foto(
    datos: UrlFotoRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> UrlFotoOut:
    url, object_key = _service(db).solicitar_url_foto(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlFotoOut(url_subida=url, object_key=object_key)


@router.post("/equipos/upload-url/manual", response_model=UrlManualOut)
def solicitar_url_manual(
    datos: UrlManualRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> UrlManualOut:
    url, object_key = _service(db).solicitar_url_manual(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlManualOut(url_subida=url, object_key=object_key)


@router.get("/equipos/export")
def exportar_equipos(
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
    formato: str = Query(default="xlsx"),
    q: str | None = Query(default=None),
    categoria_id: uuid.UUID | None = Query(default=None),
    area_id: uuid.UUID | None = Query(default=None),
    estado_operativo: str | None = Query(default=None),
) -> StreamingResponse:
    if formato != "xlsx":
        raise ErrorDeDominio(
            "formato_no_soportado",
            "Por ahora solo se puede exportar a Excel (.xlsx); PDF corporativo llega con Reportes.",
            {"formatos_disponibles": ["xlsx"]},
        )

    equipos = EquipoRepositorySQLAlchemy(db).listar_todos(
        FiltrosEquipo(q=q, categoria_id=categoria_id, area_id=area_id, estado_operativo=estado_operativo)
    )
    contenido = generar_excel(equipos)
    return StreamingResponse(
        iter([contenido]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=equipos.xlsx"},
    )


@router.get("/equipos/{equipo_id}", response_model=EquipoOut)
def obtener_equipo(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> EquipoOut:
    service = _service(db)
    return _a_out(service.obtener(equipo_id), service)


@router.patch("/equipos/{equipo_id}", response_model=EquipoOut)
def actualizar_equipo(
    equipo_id: uuid.UUID,
    datos: EquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> EquipoOut:
    service = _service(db)
    equipo = service.actualizar(equipo_id, _a_datos(datos), _actor(request, usuario))
    db.commit()
    return _a_out(equipo, service)


@router.delete("/equipos/{equipo_id}", status_code=204, response_model=None)
def eliminar_equipo(
    equipo_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> None:
    _service(db).eliminar(equipo_id, _actor(request, usuario))
    db.commit()


@router.post("/equipos/{equipo_id}/duplicar", response_model=EquipoOut, status_code=201)
def duplicar_equipo(
    equipo_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.crear")),
) -> EquipoOut:
    service = _service(db)
    equipo = service.duplicar(equipo_id, _actor(request, usuario))
    _generar_qr(db, usuario.laboratorio_id, equipo.id)
    db.commit()
    return _a_out(equipo, service)


@router.get("/equipos/{equipo_id}/historial", response_model=list[HistorialEntradaOut])
def historial_equipo(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[HistorialEntradaOut]:
    entradas = _service(db).historial(equipo_id)
    return [
        HistorialEntradaOut(
            id=e.id,
            usuario_id=e.usuario_id,
            accion=e.accion,
            valor_anterior=e.valor_anterior,
            valor_nuevo=e.valor_nuevo,
            creado_en=e.creado_en,
        )
        for e in entradas
    ]


def _referencia_service(db: Session) -> ReferenciaService:
    return ReferenciaService(
        CategoriaEquipoRepositorySQLAlchemy(db),
        AreaRepositorySQLAlchemy(db),
        EquipoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
    )


def _actor_referencia(request: Request, usuario: UsuarioContexto) -> ActorReferencia:
    return ActorReferencia(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _categoria_a_out(fila) -> CategoriaEquipoOut:  # type: ignore[no-untyped-def]
    return CategoriaEquipoOut(
        id=fila.id,
        nombre=fila.nombre,
        frecuencia_calibracion_default_meses=fila.frecuencia_calibracion_default_meses,
        bloquea_activacion_si_calibracion_vencida=fila.bloquea_activacion_si_calibracion_vencida,
    )


@router.get("/categorias-equipo", response_model=list[CategoriaEquipoOut])
def listar_categorias(
    db: Session = Depends(get_db), _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[CategoriaEquipoOut]:
    return [_categoria_a_out(f) for f in CategoriaEquipoRepositorySQLAlchemy(db).listar()]


@router.post("/categorias-equipo", response_model=CategoriaEquipoOut, status_code=201)
def crear_categoria(
    datos: CategoriaEquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> CategoriaEquipoOut:
    fila = _referencia_service(db).crear_categoria(
        usuario.laboratorio_id,
        _actor_referencia(request, usuario),
        datos.nombre,
        datos.frecuencia_calibracion_default_meses,
        datos.bloquea_activacion_si_calibracion_vencida,
    )
    db.commit()
    return _categoria_a_out(fila)


@router.patch("/categorias-equipo/{categoria_id}", response_model=CategoriaEquipoOut)
def actualizar_categoria(
    categoria_id: uuid.UUID,
    datos: CategoriaEquipoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> CategoriaEquipoOut:
    fila = _referencia_service(db).actualizar_categoria(
        usuario.laboratorio_id,
        _actor_referencia(request, usuario),
        categoria_id,
        datos.nombre,
        datos.frecuencia_calibracion_default_meses,
        datos.bloquea_activacion_si_calibracion_vencida,
    )
    db.commit()
    return _categoria_a_out(fila)


@router.delete("/categorias-equipo/{categoria_id}", status_code=204, response_model=None)
def eliminar_categoria(
    categoria_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> None:
    _referencia_service(db).eliminar_categoria(
        usuario.laboratorio_id, _actor_referencia(request, usuario), categoria_id
    )
    db.commit()


@router.get("/areas", response_model=list[AreaOut])
def listar_areas(
    db: Session = Depends(get_db), _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[AreaOut]:
    filas = AreaRepositorySQLAlchemy(db).listar()
    return [AreaOut(id=f.id, nombre=f.nombre) for f in filas]


@router.post("/areas", response_model=AreaOut, status_code=201)
def crear_area(
    datos: AreaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> AreaOut:
    fila = _referencia_service(db).crear_area(
        usuario.laboratorio_id, _actor_referencia(request, usuario), datos.nombre
    )
    db.commit()
    return AreaOut(id=fila.id, nombre=fila.nombre)


@router.patch("/areas/{area_id}", response_model=AreaOut)
def actualizar_area(
    area_id: uuid.UUID,
    datos: AreaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> AreaOut:
    fila = _referencia_service(db).actualizar_area(
        usuario.laboratorio_id, _actor_referencia(request, usuario), area_id, datos.nombre
    )
    db.commit()
    return AreaOut(id=fila.id, nombre=fila.nombre)


@router.delete("/areas/{area_id}", status_code=204, response_model=None)
def eliminar_area(
    area_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> None:
    _referencia_service(db).eliminar_area(
        usuario.laboratorio_id, _actor_referencia(request, usuario), area_id
    )
    db.commit()
